# pairing.py — GuardianNet
# Fluxo de pareamento responsável -> criança via código curto de 6 dígitos

import random
import string
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, g

from auth import require_auth, _emitir_token, _rate_limit
from conexao import get_connection

pairing_bp = Blueprint('pairing', __name__, url_prefix='/api/pairing')

CODIGO_TTL_MINUTOS = 10


def _gerar_codigo() -> str:
    return ''.join(random.choices(string.digits, k=6))


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

        # Invalida códigos antigos não usados desse responsável
        cur.execute(
            """
            UPDATE codigos_pareamento
            SET usado = TRUE
            WHERE responsavel_id = %s AND usado = FALSE
            """,
            (g.user_id,),
        )

        codigo = _gerar_codigo()
        expira_em = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=CODIGO_TTL_MINUTOS)

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
        agora = datetime.now(timezone.utc).replace(tzinfo=None)

        cur.execute(
            """
            SELECT id, responsavel_id
            FROM codigos_pareamento
            WHERE codigo = %s AND usado = FALSE AND expira_em > %s
            ORDER BY id DESC LIMIT 1
            """,
            (codigo, agora),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'Código inválido ou expirado. Peça um novo código ao responsável.'}), 404

        pareamento_id, responsavel_id = row

        cur.execute("SELECT nome FROM usuarios WHERE id = %s", (responsavel_id,))
        resp_row = cur.fetchone()
        nome_responsavel = resp_row[0] if resp_row else 'Responsável'

        # Cria a conta da criança vinculada ao responsável.
        # Sem senha própria — o único jeito de entrar é via novo código do responsável.
        cur.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, telefone, tipo, responsavel_id, ativo)
            VALUES (%s, NULL, NULL, NULL, 'crianca', %s, TRUE)
            RETURNING id
            """,
            (nome, responsavel_id),
        )
        crianca_id = cur.fetchone()[0]

        cur.execute("UPDATE codigos_pareamento SET usado = TRUE WHERE id = %s", (pareamento_id,))
        conn.commit()

        token = _emitir_token(crianca_id)

        return jsonify({
            'ok': True,
            'token': token,
            'nome': nome,
            'tipo': 'crianca',
            'responsavelNome': nome_responsavel,
        }), 201
    finally:
        conn.close()