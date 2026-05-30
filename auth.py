# auth.py — Proteempreenda
# Autenticação adaptada para PostgreSQL (Supabase)

from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
import time
from functools import wraps

from flask import Blueprint, jsonify, request, g
from werkzeug.security import check_password_hash, generate_password_hash
import os

from conexao import get_connection

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

TOKEN_TTL_HORAS = 24
RESET_TOKEN_TTL_MINUTOS = 30
_RATE_BUCKETS = {}
_PASSWORD_RESET_TOKENS = {}
DEBUG_ENABLED = str(os.getenv('FLASK_DEBUG', 'false')).strip().lower() in {'1', 'true', 'yes', 'on'}


def _normalize_email(email: str) -> str:
    return (email or '').strip().lower()


def _email_valido(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""))


def _rate_limit(max_calls: int, window_seconds: int):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
            rota = request.path
            key = f"{ip}:{rota}"
            now = time.time()
            bucket = _RATE_BUCKETS.get(key, [])
            bucket = [t for t in bucket if now - t < window_seconds]
            if len(bucket) >= max_calls:
                return jsonify({'error': 'Muitas tentativas. Tente novamente em instantes.'}), 429
            bucket.append(now)
            _RATE_BUCKETS[key] = bucket
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _gerar_token() -> str:
    return secrets.token_urlsafe(48)


def _limpar_tokens_reset_expirados() -> None:
    agora = datetime.now(timezone.utc).replace(tzinfo=None)
    expirados = [
        token_hash
        for token_hash, data in _PASSWORD_RESET_TOKENS.items()
        if data.get('expira_em') is None or data.get('expira_em') <= agora
    ]
    for token_hash in expirados:
        _PASSWORD_RESET_TOKENS.pop(token_hash, None)


def _buscar_usuario_por_email(email: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome, email, senha_hash, ativo, tipo
            FROM usuarios
            WHERE email = %s
            """,
            (email,),
        )
        return cur.fetchone()
    finally:
        conn.close()


def _buscar_usuario_por_id(user_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome, email, ativo, criado_em, tipo
            FROM usuarios
            WHERE id = %s
            """,
            (user_id,),
        )
        return cur.fetchone()
    finally:
        conn.close()


def _emitir_token(user_id: int) -> str:
    token = _gerar_token()
    expira_em = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=TOKEN_TTL_HORAS)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auth_tokens (user_id, token_hash, expira_em, revogado)
            VALUES (%s, %s, %s, FALSE)
            """,
            (user_id, _token_hash(token), expira_em),
        )
        conn.commit()
    finally:
        conn.close()

    return token


def _usuario_tem_assinatura_ativa(user_id: int):
    try:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT a.id, p.nome AS plano_nome, a.periodo, a.status, a.data_fim
                FROM assinaturas a
                INNER JOIN planos p ON p.id = a.plano_id
                WHERE a.usuario_id = %s
                  AND a.status = 'ativa'
                ORDER BY a.id DESC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return False, None
            return True, {
                'plano':   (row[1] or '').lower(),
                'periodo': (row[2] or '').lower(),
                'status':  (row[3] or '').lower(),
            }
        finally:
            conn.close()
    except Exception:
        return False, None


def _extrair_bearer_token() -> str:
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return ''
    return auth_header.split(' ', 1)[1].strip()


def _autenticar_requisicao():
    token = _extrair_bearer_token()
    if not token:
        return None

    token_hash = _token_hash(token)
    agora = datetime.now(timezone.utc).replace(tzinfo=None)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT t.user_id, u.ativo
            FROM auth_tokens t
            INNER JOIN usuarios u ON u.id = t.user_id
            WHERE t.token_hash = %s
              AND t.revogado = FALSE
              AND t.expira_em > %s
            ORDER BY t.id DESC
            LIMIT 1
            """,
            (token_hash, agora),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            'user_id': int(row[0]),
            'ativo': bool(row[1]),
        }
    finally:
        conn.close()


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_data = _autenticar_requisicao()
        if not auth_data:
            return jsonify({'error': 'Não autenticado.'}), 401

        if not auth_data.get('ativo', False):
            try:
                conn = get_connection()
                try:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        UPDATE auth_tokens
                        SET revogado = TRUE,
                            revogado_em = NOW()
                        WHERE user_id = %s
                          AND revogado = FALSE
                        """,
                        (auth_data['user_id'],),
                    )
                    conn.commit()
                finally:
                    conn.close()
            except Exception:
                pass
            return jsonify({'error': 'Usuário desativado. Contate o administrador.'}), 403

        g.user_id = auth_data['user_id']
        return fn(*args, **kwargs)
    return wrapper


@auth_bp.post('/register')
@_rate_limit(max_calls=20, window_seconds=60)
def register():
    try:
        data     = request.get_json(silent=True) or {}
        nome     = (data.get("nome")     or "").strip()
        email    = _normalize_email(data.get("email"))
        senha    = (data.get("senha")    or "").strip()
        telefone = (data.get("telefone") or "").strip()

        if len(nome) < 3 or not _email_valido(email) or len(senha) < 6 or not telefone:
            return jsonify({"error": "Dados inválidos."}), 400

        digitos = "".join(c for c in telefone if c.isdigit())
        if len(digitos) < 8 or len(digitos) > 15:
            return jsonify({"error": "Telefone inválido. Use formato internacional com código do país."}), 400

        senha_hash = generate_password_hash(senha)

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO usuarios (nome, email, senha_hash, telefone, tipo)
                VALUES (%s, %s, %s, %s, 'usuario')
                RETURNING id
                """,
                (nome, email, senha_hash, telefone),
            )
            user_id = cur.fetchone()[0]
            conn.commit()
        except Exception as e:
            conn.rollback()
            msg = str(e)
            if 'uq_usuarios_email' in msg.lower() or 'unique' in msg.lower():
                return jsonify({'error': 'E-mail já cadastrado.'}), 409
            raise
        finally:
            conn.close()

        token = _emitir_token(user_id)

        return jsonify({
            'ok':              True,
            'token':           token,
            'ttlHoras':        TOKEN_TTL_HORAS,
            'nome':            nome,
            'tipo':            'usuario',
            'hasSubscription': False,
            'redirectTo':      'planos.html',
        }), 201

    except Exception as e:
        return jsonify({'error': 'Falha ao criar conta.', 'detail': str(e) if DEBUG_ENABLED else ''}), 500


@auth_bp.post('/login')
@_rate_limit(max_calls=30, window_seconds=60)
def login():
    try:
        data  = request.get_json(silent=True) or {}
        email = _normalize_email(data.get('email'))
        senha = (data.get('senha') or '').strip()

        user = _buscar_usuario_por_email(email)
        if not user:
            return jsonify({'error': 'Credenciais inválidas.'}), 401

        user_id, _nome, _email, senha_hash, ativo, tipo = user
        if not ativo:
            return jsonify({'error': 'Usuário inativo.'}), 403

        if not check_password_hash(senha_hash, senha):
            return jsonify({'error': 'Credenciais inválidas.'}), 401

        token = _emitir_token(user_id)
        tem_assinatura, assinatura_info = _usuario_tem_assinatura_ativa(user_id)

        payload = {
            'ok':              True,
            'token':           token,
            'ttlHoras':        TOKEN_TTL_HORAS,
            'nome':            _nome,
            'tipo':            (tipo or 'usuario').lower(),
            'hasSubscription': tem_assinatura,
        }
        if payload['tipo'] == 'admin':
            payload['hasSubscription'] = True
            payload['redirectTo'] = 'admin.html'
            return jsonify(payload), 200

        if tem_assinatura and assinatura_info:
            payload['plano']   = assinatura_info.get('plano')
            payload['periodo'] = assinatura_info.get('periodo')
            payload['redirectTo'] = 'dashboard.html'
        else:
            payload['redirectTo'] = 'planos.html'

        return jsonify(payload), 200

    except Exception as e:
        return jsonify({'error': 'Falha ao fazer login.', 'detail': str(e) if DEBUG_ENABLED else ''}), 500


@auth_bp.post('/forgot-password')
@_rate_limit(max_calls=10, window_seconds=60)
def forgot_password():
    try:
        data  = request.get_json(silent=True) or {}
        email = _normalize_email(data.get('email'))

        _limpar_tokens_reset_expirados()

        token_claro = None
        if _email_valido(email):
            user = _buscar_usuario_por_email(email)
            if user and bool(user[4]):
                user_id     = int(user[0])
                token_claro = secrets.token_urlsafe(24)
                token_hash  = _token_hash(token_claro)
                expira_em   = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=RESET_TOKEN_TTL_MINUTOS)
                _PASSWORD_RESET_TOKENS[token_hash] = {'user_id': user_id, 'expira_em': expira_em}

        payload = {
            'ok':      True,
            'message': 'Se o e-mail existir, um token de recuperação foi gerado.'
        }
        if DEBUG_ENABLED and token_claro:
            payload['resetToken'] = token_claro
            payload['ttlMinutos'] = RESET_TOKEN_TTL_MINUTOS

        return jsonify(payload), 200

    except Exception as e:
        return jsonify({'error': 'Falha ao iniciar recuperação de senha.', 'detail': str(e) if DEBUG_ENABLED else ''}), 500


@auth_bp.post('/reset-password')
@_rate_limit(max_calls=15, window_seconds=60)
def reset_password():
    try:
        data  = request.get_json(silent=True) or {}
        token = (data.get('token') or '').strip()
        senha = (data.get('senha') or '').strip()

        if len(token) < 10 or len(senha) < 6:
            return jsonify({'error': 'Token ou senha inválidos.'}), 400

        _limpar_tokens_reset_expirados()
        token_hash = _token_hash(token)
        token_data = _PASSWORD_RESET_TOKENS.get(token_hash)
        if not token_data:
            return jsonify({'error': 'Token inválido ou expirado.'}), 400

        user_id    = int(token_data['user_id'])
        senha_hash = generate_password_hash(senha)

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE usuarios
                SET senha_hash = %s,
                    atualizado_em = NOW()
                WHERE id = %s
                  AND ativo = TRUE
                """,
                (senha_hash, user_id),
            )
            if cur.rowcount == 0:
                return jsonify({'error': 'Usuário não encontrado ou inativo.'}), 404

            cur.execute(
                """
                UPDATE auth_tokens
                SET revogado = TRUE,
                    revogado_em = NOW()
                WHERE user_id = %s
                  AND revogado = FALSE
                """,
                (user_id,),
            )
            conn.commit()
        finally:
            conn.close()

        _PASSWORD_RESET_TOKENS.pop(token_hash, None)
        return jsonify({'ok': True, 'message': 'Senha redefinida com sucesso.'}), 200

    except Exception as e:
        return jsonify({'error': 'Falha ao redefinir senha.', 'detail': str(e) if DEBUG_ENABLED else ''}), 500


@auth_bp.get('/me')
@require_auth
def me():
    try:
        user = _buscar_usuario_por_id(g.user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado.'}), 404

        user_id   = int(user[0]) if user[0] is not None else None
        nome      = str(user[1]) if user[1] is not None else ''
        email     = str(user[2]) if user[2] is not None else ''
        ativo     = bool(user[3]) if user[3] is not None else False
        criado_em = user[4]
        tipo      = str(user[5]).lower() if user[5] is not None else 'usuario'

        return jsonify({
            'id':       user_id,
            'nome':     nome,
            'email':    email,
            'ativo':    ativo,
            'tipo':     tipo,
            'criadoEm': criado_em.isoformat() if hasattr(criado_em, 'isoformat') else None,
        }), 200

    except Exception as e:
        payload = {'error': 'Falha ao carregar perfil.'}
        if DEBUG_ENABLED:
            payload['detail'] = str(e)
        return jsonify(payload), 500


@auth_bp.post('/logout')
@require_auth
def logout():
    token      = _extrair_bearer_token()
    token_hash = _token_hash(token)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE auth_tokens
            SET revogado = TRUE,
                revogado_em = NOW()
            WHERE token_hash = %s
              AND revogado = FALSE
            """,
            (token_hash,),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({'ok': True}), 200