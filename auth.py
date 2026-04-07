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
_RATE_BUCKETS = {}
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


def _buscar_usuario_por_email(email: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT Id, Nome, Email, SenhaHash, Ativo
            FROM dbo.Usuarios
            WHERE Email = ?
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
            SELECT Id, Nome, Email, Ativo, CriadoEm
            FROM dbo.Usuarios
            WHERE Id = ?
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
            INSERT INTO dbo.AuthTokens (UserId, TokenHash, ExpiraEm, Revogado)
            VALUES (?, ?, ?, 0)
            """,
            (user_id, _token_hash(token), expira_em),
        )
        conn.commit()
    finally:
        conn.close()

    return token


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
            SELECT TOP 1 UserId
            FROM dbo.AuthTokens
            WHERE TokenHash = ?
              AND Revogado = 0
              AND ExpiraEm > ?
            ORDER BY Id DESC
            """,
            (token_hash, agora),
        )
        row = cur.fetchone()
        if not row:
            return None
        return row[0]
    finally:
        conn.close()


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = _autenticar_requisicao()
        if not user_id:
            return jsonify({'error': 'Não autenticado.'}), 401
        g.user_id = user_id
        return fn(*args, **kwargs)
    return wrapper


@auth_bp.post('/register')
@_rate_limit(max_calls=20, window_seconds=60)
def register():
    data = request.get_json(silent=True) or {}
    nome = (data.get('nome') or '').strip()
    email = _normalize_email(data.get('email'))
    senha = (data.get('senha') or '').strip()

    if len(nome) < 3 or not _email_valido(email) or len(senha) < 6:
        return jsonify({'error': 'Dados inválidos.'}), 400

    if _buscar_usuario_por_email(email):
        return jsonify({'error': 'E-mail já cadastrado.'}), 409

    senha_hash = generate_password_hash(senha)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.Usuarios (Nome, Email, SenhaHash)
            OUTPUT INSERTED.Id
            VALUES (?, ?, ?)
            """,
            (nome, email, senha_hash),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    token = _emitir_token(user_id)
    return jsonify({'ok': True, 'token': token, 'ttlHoras': TOKEN_TTL_HORAS}), 201


@auth_bp.post('/login')
@_rate_limit(max_calls=30, window_seconds=60)
def login():
    data = request.get_json(silent=True) or {}
    email = _normalize_email(data.get('email'))
    senha = (data.get('senha') or '').strip()

    user = _buscar_usuario_por_email(email)
    if not user:
        return jsonify({'error': 'Credenciais inválidas.'}), 401

    user_id, _nome, _email, senha_hash, ativo = user
    if not ativo:
        return jsonify({'error': 'Usuário inativo.'}), 403

    if not check_password_hash(senha_hash, senha):
        return jsonify({'error': 'Credenciais inválidas.'}), 401

    token = _emitir_token(user_id)
    return jsonify({'ok': True, 'token': token, 'ttlHoras': TOKEN_TTL_HORAS}), 200


@auth_bp.get('/me')
@require_auth
def me():
    try:
        user = _buscar_usuario_por_id(g.user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado.'}), 404

        user_id = int(user[0]) if user[0] is not None else None
        nome = str(user[1]) if user[1] is not None else ''
        email = str(user[2]) if user[2] is not None else ''
        ativo = bool(user[3]) if user[3] is not None else False
        criado_em = user[4]

        return jsonify(
            {
                'id': user_id,
                'nome': nome,
                'email': email,
                'ativo': ativo,
                'criadoEm': criado_em.isoformat() if hasattr(criado_em, 'isoformat') else None,
            }
        ), 200
    except Exception as e:
        payload = {'error': 'Falha ao carregar perfil.'}
        if DEBUG_ENABLED:
            payload['detail'] = str(e)
        return jsonify(payload), 500


@auth_bp.post('/logout')
@require_auth
def logout():
    token = _extrair_bearer_token()
    token_hash = _token_hash(token)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE dbo.AuthTokens
            SET Revogado = 1,
                RevogadoEm = SYSUTCDATETIME()
            WHERE TokenHash = ?
              AND Revogado = 0
            """,
            (token_hash,),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({'ok': True}), 200


