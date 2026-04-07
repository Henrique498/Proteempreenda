from datetime import datetime, timedelta, timezone
import unicodedata
import os

from flask import Blueprint, jsonify, request, g

from auth import require_auth
from conexao import get_connection


subscription_bp = Blueprint('subscription', __name__, url_prefix='/api/subscription')

PLANOS_VALIDOS = {'gratuito', 'basico', 'premium', 'escola'}
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
    if 'escola' in n:
        return 'escola'
    if 'premium' in n:
        return 'premium'
    if 'basico' in n or n == 'pro':
        return 'basico'
    return n or 'premium'


def _resolver_plano(cur, plano_slug: str):
    cur.execute("SELECT Id, Nome FROM dbo.Planos WHERE Ativo = 1")
    rows = cur.fetchall()

    alvo = _normalize_text(plano_slug)
    for row in rows:
        row_id = row[0]
        row_nome = row[1]
        nome_norm = _normalize_text(row_nome)
        if alvo == 'basico' and nome_norm in ('basico', 'pro'):
            return row_id, row_nome
        if alvo == nome_norm:
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
            SELECT TOP 1
                a.Id,
                a.UsuarioId,
                p.Nome AS PlanoNome,
                a.Periodo,
                a.Status,
                a.DataInicio,
                a.DataFim,
                a.CriadoEm
            FROM dbo.Assinaturas a
            INNER JOIN dbo.Planos p ON p.Id = a.PlanoId
            WHERE a.UsuarioId = ?
            ORDER BY a.Id DESC
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


def _criar_assinatura_paga(user_id: int, plano: str, periodo: str, metodo: str, valor) -> tuple[bool, object]:
    agora = _sql_datetime(datetime.now(timezone.utc).replace(tzinfo=None))

    conn = get_connection()
    try:
        cur = conn.cursor()
        plano_id, _nome = _resolver_plano(cur, plano)
        if not plano_id:
            return False, _erro_json('Plano não encontrado no banco.', status=404)

        cur.execute(
            """
            UPDATE dbo.Assinaturas
            SET Status = 'cancelada',
                DataFim = ?
            WHERE UsuarioId = ?
              AND Status = 'ativa'
            """,
                        (agora, user_id),
        )

        cur.execute(
            """
            INSERT INTO dbo.Assinaturas (UsuarioId, PlanoId, Periodo, DataInicio, Status)
            OUTPUT INSERTED.Id
            VALUES (?, ?, ?, ?, 'ativa')
            """,
            (user_id, plano_id, periodo, agora),
        )
        row = cur.fetchone()
        subscription_id = row[0] if row else None
        if not subscription_id:
            return False, _erro_json('Não foi possível criar a assinatura.', status=500)

        try:
            valor_num = float(valor) if valor is not None else 0.0
        except (TypeError, ValueError):
            valor_num = 0.0

        cur.execute(
            """
            INSERT INTO dbo.Pagamentos (AssinaturaId, Valor, Metodo, Status, DataPagamento)
            VALUES (?, ?, ?, 'aprovado', SYSUTCDATETIME())
            """,
            (subscription_id, valor_num, metodo),
        )

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

        row_id = row[0]
        usuario_id = row[1]
        plano_nome = row[2]
        periodo = row[3]
        status = (row[4] or '').lower()
        data_inicio = _parse_datetime(row[5])
        data_fim = _parse_datetime(row[6])

        plano_slug = _slug_from_plan_name(plano_nome)

        if plano_slug == 'gratuito' and data_fim:
            hoje = datetime.now(timezone.utc).replace(tzinfo=None)
            if hoje > data_fim:
                status = 'expirada'

        return jsonify(
            {
                'assinatura': {
                    'id': row_id,
                    'userId': usuario_id,
                    'plano': plano_slug,
                    'periodo': periodo,
                    'status': status,
                    'trialEndsAt': _to_iso(data_fim) if plano_slug == 'gratuito' else None,
                    'startedAt': _to_iso(data_inicio),
                    'nextBillingAt': None,
                    'canceledAt': None,
                }
            }
        ), 200
    except Exception as e:
        return _erro_json('Falha ao carregar assinatura.', str(e), 500)


@subscription_bp.post('/start')
@require_auth
def iniciar_assinatura():
    data = request.get_json(silent=True) or {}
    plano = (data.get('plano') or '').strip().lower()
    periodo = (data.get('periodo') or '').strip().lower()
    metodo = (data.get('metodo') or 'cartao').strip().lower()
    valor = data.get('valor')

    if plano not in PLANOS_VALIDOS - {'gratuito'} or periodo not in PERIODOS_VALIDOS:
        return jsonify({'error': 'Plano ou período inválido.'}), 400

    if metodo not in {'pix', 'cartao', 'boleto'}:
        metodo = 'cartao'

    try:
        ok, result = _criar_assinatura_paga(g.user_id, plano, periodo, metodo, valor)
        if not ok:
            return result
        subscription_id = result
        return jsonify({'ok': True, 'subscriptionId': subscription_id}), 201
    except Exception as e:
        return _erro_json('Falha ao criar assinatura.', str(e), 500)


@subscription_bp.post('/start-trial')
@require_auth
def iniciar_trial():
    try:
        trial_days = 30
        hoje_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        trial_ends_dt = hoje_dt + timedelta(days=trial_days)
        hoje = _sql_datetime(hoje_dt)
        trial_ends = _sql_datetime(trial_ends_dt)

        conn = get_connection()
        try:
            cur = conn.cursor()
            plano_id, _nome = _resolver_plano(cur, 'gratuito')
            if not plano_id:
                return _erro_json('Plano gratuito não encontrado no banco.', status=404)

            cur.execute(
                """
                UPDATE dbo.Assinaturas
                SET Status = 'cancelada',
                    DataFim = ?
                WHERE UsuarioId = ?
                  AND Status = 'ativa'
                """,
                (hoje, g.user_id),
            )

            cur.execute(
                """
                INSERT INTO dbo.Assinaturas (UsuarioId, PlanoId, Periodo, DataInicio, DataFim, Status)
                OUTPUT INSERTED.Id
                VALUES (?, ?, 'mensal', ?, ?, 'ativa')
                """,
                (g.user_id, plano_id, hoje, trial_ends),
            )
            row = cur.fetchone()
            subscription_id = row[0] if row else None
            if not subscription_id:
                return _erro_json('Não foi possível criar trial.', status=500)
            conn.commit()
        finally:
            conn.close()

        return jsonify({'ok': True, 'subscriptionId': subscription_id, 'trialEndsAt': trial_ends.replace(' ', 'T')}), 201
    except Exception as e:
        return _erro_json('Falha ao iniciar trial.', str(e), 500)


@subscription_bp.post('/change-plan')
@require_auth
def trocar_plano():
    data = request.get_json(silent=True) or {}
    plano = (data.get('plano') or '').strip().lower()
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
                SELECT TOP 1 Id
                FROM dbo.Assinaturas
                WHERE UsuarioId = ?
                ORDER BY Id DESC
                """,
                (g.user_id,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Assinatura não encontrada.'}), 404

            subscription_id = row[0]
            cur.execute(
                """
                UPDATE dbo.Assinaturas
                SET Status = 'cancelada',
                    DataFim = ?
                WHERE Id = ?
                """,
                (hoje, subscription_id),
            )
            conn.commit()
        finally:
            conn.close()

        return jsonify({'ok': True}), 200
    except Exception as e:
        return _erro_json('Falha ao cancelar assinatura.', str(e), 500)


