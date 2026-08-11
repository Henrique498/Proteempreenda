# subscription.py — Proteempreenda
# Assinaturas adaptadas para PostgreSQL (Supabase)

from datetime import datetime, timedelta, timezone
import unicodedata
import os

from flask import Blueprint, jsonify, request, g

from auth import require_auth
from conexao import get_connection

subscription_bp = Blueprint('subscription', __name__, url_prefix='/api/subscription')

PLANOS_VALIDOS = {'gratuito', 'basico', 'premium', 'premiumplus'}
PERIODOS_VALIDOS = {'mensal', 'anual'}
DEBUG_ENABLED = str(os.getenv('FLASK_DEBUG', 'false')).strip().lower() in {'1', 'true', 'yes', 'on'}


def _normalize_text(v: str) -> str:
    if not v:
        return ''
    base = unicodedata.normalize('NFKD', v)
    sem_acentos = ''.join(c for c in base if not unicodedata.combining(c))
    return sem_acentos.strip().lower()


def _slug_from_plan_name(nome: str) -> str:
    n = _normalize_text(nome)
    if 'gratuito' in n:
        return 'gratuito'
    if 'plus' in n or 'premiumplus' in n:
        return 'premiumplus'
    if 'premium' in n:
        return 'premium'
    if 'basico' in n or n == 'pro':
        return 'basico'
    return ''


def _resolver_plano(cur, plano_slug: str):
    cur.execute("SELECT id, nome FROM planos WHERE ativo = TRUE")
    rows = cur.fetchall()

    alvo = _normalize_text(plano_slug)

    aliases = {
        'basico':   {'basico', 'plano basico', 'pro', 'plano pro'},
        'premium':  {'premium', 'plano premium'},
        'escola':   {'escola', 'plano escola'},
        'gratuito': {'gratuito', 'free', 'trial'},
    }

    for row in rows:
        row_id   = row[0]
        row_nome = row[1]
        nome_norm = _normalize_text(row_nome)

        if nome_norm == alvo:
            return row_id, row_nome
        if alvo in aliases and nome_norm in aliases[alvo]:
            return row_id, row_nome
        if alvo == 'basico' and ('basico' in nome_norm or nome_norm == 'pro'):
            return row_id, row_nome
        if alvo in ('premium', 'escola', 'gratuito') and alvo in nome_norm:
            return row_id, row_nome

    return None, None


def _to_iso(dt):
    if dt is None:
        return None
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    return str(dt)


def _sql_datetime(dt):
    if hasattr(dt, 'strftime'):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return str(dt)


def _add_period(dt: datetime, periodo: str) -> datetime:
    if periodo == 'anual':
        try:
            return dt.replace(year=dt.year + 1)
        except ValueError:
            return dt.replace(month=2, day=28, year=dt.year + 1)
    try:
        month = dt.month + 1
        year = dt.year
        if month > 12:
            month = 1
            year += 1
        day = min(dt.day, [31,
                           29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                           31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return dt.replace(year=year, month=month, day=day)
    except ValueError:
        return dt + timedelta(days=30)


def _parse_datetime(v):
    if v is None:
        return None
    if hasattr(v, 'year') and hasattr(v, 'month'):
        return v
    text = str(v).replace('T', ' ').replace('Z', '')
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def _buscar_assinatura_atual(user_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.id, a.usuario_id, p.nome AS plano_nome,
                   a.periodo, a.status, a.data_inicio, a.data_fim, a.criado_em
            FROM assinaturas a
            INNER JOIN planos p ON p.id = a.plano_id
            WHERE a.usuario_id = %s
            ORDER BY a.id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone()
    finally:
        conn.close()


def _erro_json(msg: str, detail: str = None, status: int = 500):
    payload = {'error': msg}
    if detail and DEBUG_ENABLED:
        payload['detail'] = detail
    return jsonify(payload), status


def _registrar_pagamento_best_effort(cur, assinatura_id: int, valor_num: float, metodo: str) -> bool:
    tentativas = [
        (
            """
            INSERT INTO pagamentos (assinatura_id, valor, metodo, status, data_pagamento)
            VALUES (%s, %s, %s, 'aprovado', NOW())
            """,
            (assinatura_id, valor_num, metodo),
        ),
        (
            """
            INSERT INTO pagamentos (assinatura_id, valor, metodo, status)
            VALUES (%s, %s, %s, 'aprovado')
            """,
            (assinatura_id, valor_num, metodo),
        ),
    ]
    for sql, params in tentativas:
        try:
            cur.execute(sql, params)
            return True
        except Exception:
            continue
    return False


def _inserir_assinatura_e_obter_id(cur, user_id: int, plano_id: int, periodo: str,
                                    data_inicio: str, data_fim: str, status: str = 'ativa'):
    cur.execute(
        """
        INSERT INTO assinaturas (usuario_id, plano_id, periodo, data_inicio, data_fim, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (user_id, plano_id, periodo, data_inicio, data_fim, status),
    )
    row = cur.fetchone()
    return row[0] if row else None


def _criar_assinatura_paga(user_id: int, plano: str, periodo: str, metodo: str, valor) -> tuple:
    agora    = _sql_datetime(datetime.now(timezone.utc).replace(tzinfo=None))
    agora_dt = _parse_datetime(agora) or datetime.now(timezone.utc).replace(tzinfo=None)
    data_fim = _sql_datetime(_add_period(agora_dt, periodo))

    conn = get_connection()
    try:
        cur = conn.cursor()
        plano_id, _nome = _resolver_plano(cur, plano)
        if not plano_id:
            return False, _erro_json('Plano não encontrado no banco.', status=404)

        cur.execute(
            """
            UPDATE assinaturas
            SET status = 'cancelada', data_fim = %s
            WHERE usuario_id = %s AND status = 'ativa'
            """,
            (agora, user_id),
        )

        subscription_id = _inserir_assinatura_e_obter_id(
            cur, user_id=user_id, plano_id=plano_id,
            periodo=periodo, data_inicio=agora, data_fim=data_fim, status='ativa',
        )
        if not subscription_id:
            return False, _erro_json('Não foi possível criar a assinatura.', status=500)

        conn.commit()

        try:
            valor_num = float(valor) if valor is not None else 0.0
        except (TypeError, ValueError):
            valor_num = 0.0

        if _registrar_pagamento_best_effort(cur, subscription_id, valor_num, metodo):
            conn.commit()
    finally:
        conn.close()

    return True, subscription_id


@subscription_bp.get('/current')
@require_auth
def assinatura_atual():
    try:
        row = _buscar_assinatura_atual(g.user_id)
        if not row:
            return jsonify({'assinatura': None}), 200

        row_id      = row[0]
        usuario_id  = row[1]
        plano_nome  = row[2]
        periodo     = row[3]
        status      = (row[4] or '').lower()
        data_inicio = _parse_datetime(row[5])
        data_fim    = _parse_datetime(row[6])
        plano_slug  = _slug_from_plan_name(plano_nome)
        agora       = datetime.now(timezone.utc).replace(tzinfo=None)

        if data_fim and status == 'ativa' and agora > data_fim:
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE assinaturas SET status = 'expirada' WHERE id = %s",
                    (row_id,),
                )
                conn.commit()
            finally:
                conn.close()
            status = 'expirada'

        if plano_slug == 'gratuito' and data_fim and agora > data_fim:
            status = 'expirada'

        return jsonify({'assinatura': {
            'id':           row_id,
            'userId':       usuario_id,
            'plano':        plano_slug,
            'periodo':      periodo,
            'status':       status,
            'trialEndsAt':  _to_iso(data_fim) if plano_slug == 'gratuito' else None,
            'startedAt':    _to_iso(data_inicio),
            'nextBillingAt': _to_iso(data_fim) if plano_slug != 'gratuito' else None,
            'dataFim':      _to_iso(data_fim),
            'canceledAt':   None,
        }}), 200
    except Exception as e:
        return _erro_json('Falha ao carregar assinatura.', str(e), 500)


@subscription_bp.post('/start')
@require_auth
def iniciar_assinatura():
    data    = request.get_json(silent=True) or {}
    plano   = (data.get('plano')   or '').strip().lower()
    periodo = (data.get('periodo') or '').strip().lower()
    metodo  = (data.get('metodo')  or 'cartao').strip().lower()
    valor   = data.get('valor')

    if plano not in PLANOS_VALIDOS - {'gratuito'} or periodo not in PERIODOS_VALIDOS:
        return jsonify({'error': 'Plano ou período inválido.'}), 400
    if metodo not in {'pix', 'cartao', 'boleto'}:
        metodo = 'cartao'

    try:
        ok, result = _criar_assinatura_paga(g.user_id, plano, periodo, metodo, valor)
        if not ok:
            return result
        return jsonify({'ok': True, 'subscriptionId': result}), 201
    except Exception as e:
        return _erro_json('Falha ao criar assinatura.', str(e), 500)


@subscription_bp.post('/start-trial')
@require_auth
def iniciar_trial():
    try:
        hoje_dt      = datetime.now(timezone.utc).replace(tzinfo=None)
        trial_ends_dt = hoje_dt + timedelta(days=30)
        hoje         = _sql_datetime(hoje_dt)
        trial_ends   = _sql_datetime(trial_ends_dt)

        conn = get_connection()
        try:
            cur = conn.cursor()
            plano_id, _nome = _resolver_plano(cur, 'gratuito')
            if not plano_id:
                return _erro_json('Plano gratuito não encontrado no banco.', status=404)

            cur.execute(
                """
                UPDATE assinaturas
                SET status = 'cancelada', data_fim = %s
                WHERE usuario_id = %s AND status = 'ativa'
                """,
                (hoje, g.user_id),
            )

            subscription_id = _inserir_assinatura_e_obter_id(
                cur, user_id=g.user_id, plano_id=plano_id,
                periodo='mensal', data_inicio=hoje, data_fim=trial_ends, status='ativa',
            )
            if not subscription_id:
                return _erro_json('Não foi possível criar trial.', status=500)
            conn.commit()
        finally:
            conn.close()

        return jsonify({
            'ok': True,
            'subscriptionId': subscription_id,
            'trialEndsAt': trial_ends.replace(' ', 'T'),
        }), 201
    except Exception as e:
        return _erro_json('Falha ao iniciar trial.', str(e), 500)


@subscription_bp.post('/change-plan')
@require_auth
def trocar_plano():
    data    = request.get_json(silent=True) or {}
    plano   = (data.get('plano')   or '').strip().lower()
    periodo = (data.get('periodo') or '').strip().lower()

    if plano not in PLANOS_VALIDOS or periodo not in PERIODOS_VALIDOS:
        return jsonify({'error': 'Plano ou período inválido.'}), 400

    try:
        ok, result = _criar_assinatura_paga(g.user_id, plano, periodo, 'cartao', 0)
        if not ok:
            return result
        return jsonify({'ok': True, 'subscriptionId': result}), 200
    except Exception as e:
        return _erro_json('Falha ao trocar plano.', str(e), 500)


@subscription_bp.post('/cancel')
@require_auth
def cancelar_assinatura():
    try:
        hoje = _sql_datetime(datetime.now(timezone.utc).replace(tzinfo=None))

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id FROM assinaturas
                WHERE usuario_id = %s
                ORDER BY id DESC LIMIT 1
                """,
                (g.user_id,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Assinatura não encontrada.'}), 404

            cur.execute(
                "UPDATE assinaturas SET status = 'cancelada', data_fim = %s WHERE id = %s",
                (hoje, row[0]),
            )
            conn.commit()
        finally:
            conn.close()

        return jsonify({'ok': True}), 200
    except Exception as e:
        return _erro_json('Falha ao cancelar assinatura.', str(e), 500)

PLANOS_PAGOS = {'basico', 'premium', 'premiumplus'}


def usuario_tem_plano_pago_ativo(user_id: int) -> bool:
    """True se o usuário tem um plano PAGO (não-gratuito) com status ativo/trialing e não vencido."""
    row = _buscar_assinatura_atual(user_id)
    if not row:
        return False

    plano_nome = row[2]
    status     = (row[4] or '').lower()
    data_fim   = _parse_datetime(row[6])
    plano_slug = _slug_from_plan_name(plano_nome)

    if plano_slug not in PLANOS_PAGOS:
        return False
    if status not in {'ativa', 'trialing'}:
        return False
    if data_fim and datetime.now(timezone.utc).replace(tzinfo=None) > data_fim:
        return False
    return True