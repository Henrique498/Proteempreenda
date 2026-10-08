# pairing.py — GuardianNet
# Fluxo de pareamento responsável -> criança via código curto de 6 dígitos

import secrets
import string
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, g

from auth import require_auth, _emitir_token, _rate_limit
from conexao import get_connection

pairing_bp = Blueprint('pairing', __name__, url_prefix='/api/pairing')

CODIGO_TTL_MINUTOS = 10
CRIANCA_TOKEN_TTL_HORAS = 24 * 30   # monitoramento não pode parar a cada 24h


def _gerar_codigo() -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def _agora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pairing_bp.post('/generate')
@require_auth
def gerar_codigo():
    """Responsável gera um código para a criança parear o app."""
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT tipo FROM usuarios WHERE id = %s", (g.user_id,))
        row = cur.fetchone()
        if not row or (row[0] or '').lower() not in ('usuario', 'admin'):
            return jsonify({'error': 'Apenas responsáveis podem gerar código de pareamento.'}), 403

        agora = _agora()

        # Invalida códigos antigos não usados desse responsável
        cur.execute(
            """
            UPDATE codigos_pareamento
            SET usado = TRUE
            WHERE responsavel_id = %s AND usado = FALSE
            """,
            (g.user_id,),
        )

        # Garante que nenhum outro código ATIVO tenha o mesmo número
        codigo = None
        for _ in range(10):
            candidato = _gerar_codigo()
            cur.execute(
                """
                SELECT 1 FROM codigos_pareamento
                WHERE codigo = %s AND usado = FALSE AND expira_em > %s
                """,
                (candidato, agora),
            )
            if not cur.fetchone():
                codigo = candidato
                break
        if codigo is None:
            return jsonify({'error': 'Não foi possível gerar o código agora. Tente de novo.'}), 503

        expira_em = agora + timedelta(minutes=CODIGO_TTL_MINUTOS)
        cur.execute(
            """
            INSERT INTO codigos_pareamento (responsavel_id, codigo, expira_em, usado)
            VALUES (%s, %s, %s, FALSE)
            """,
            (g.user_id, codigo, expira_em),
        )
        conn.commit()

        return jsonify({
            'ok': True,
            'codigo': codigo,
            'expiraEmMinutos': CODIGO_TTL_MINUTOS,
            'expiraEm': expira_em.isoformat(),
        }), 201
    finally:
        conn.close()


@pairing_bp.post('/redeem')
@_rate_limit(max_calls=10, window_seconds=60)
def resgatar_codigo():
    """Criança usa o código para entrar vinculada à conta do responsável."""
    data = request.get_json(silent=True) or {}
    codigo = (data.get('codigo') or '').strip()
    nome = (data.get('nome') or '').strip()

    if len(codigo) != 6 or not codigo.isdigit():
        return jsonify({'error': 'Código inválido. Use os 6 dígitos enviados pelo responsável.'}), 400
    if len(nome) < 2:
        return jsonify({'error': 'Informe um nome para continuar.'}), 400

    conn = get_connection()
    try:
        cur = conn.cursor()

        # Resgate atômico: quem queimar o código primeiro ganha, o outro recebe 404.
        cur.execute(
            """
            UPDATE codigos_pareamento
            SET usado = TRUE
            WHERE id = (
                SELECT id FROM codigos_pareamento
                WHERE codigo = %s AND usado = FALSE AND expira_em > %s
                ORDER BY id DESC LIMIT 1
                FOR UPDATE
            )
            RETURNING responsavel_id
            """,
            (codigo, _agora()),
        )
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return jsonify({'error': 'Código inválido ou expirado. Peça um novo código ao responsável.'}), 404

        responsavel_id = row[0]

        cur.execute("SELECT nome FROM usuarios WHERE id = %s", (responsavel_id,))
        resp_row = cur.fetchone()
        nome_responsavel = resp_row[0] if resp_row else 'Responsável'

        # Conta da criança: tipo 'crianca', sem senha. Só entra via novo código.
        cur.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, telefone, tipo, responsavel_id, ativo)
            VALUES (%s, NULL, NULL, NULL, 'crianca', %s, TRUE)
            RETURNING id
            """,
            (nome, responsavel_id),
        )
        crianca_id = cur.fetchone()[0]
        conn.commit()

        token = _emitir_token(crianca_id, ttl_horas=CRIANCA_TOKEN_TTL_HORAS)

        return jsonify({
            'ok': True,
            'token': token,
            'nome': nome,
            'tipo': 'crianca',
            'responsavelNome': nome_responsavel,
        }), 201
    finally:
        conn.close()