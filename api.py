# api.py — Proteempreenda
# Flask API adaptada para PostgreSQL (Supabase)

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from conexao import executar
from auth import auth_bp, require_auth
from subscription import subscription_bp
from pairing import pairing_bp
import os
import secrets
from ia.ia_service import ia_bp
import requests

def _enviar_email_api(assunto: str, corpo: str):
    resend_api_key = os.getenv('RESEND_API_KEY')
    
    response = requests.post(
        'https://api.resend.com/emails',
        headers={
            'Authorization': f'Bearer {resend_api_key}',
            'Content-Type': 'application/json'
        },
        json={
            'from': 'onboarding@resend.dev', # ou seu domínio verificado
            'to': 'guardiannet33@gmail.com',
            'subject': assunto,
            'text': corpo
        }
    )
    if response.status_code not in [200, 201]:
        raise Exception(f"Erro ao enviar via Resend: {response.text}")



load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


DEBUG_ENABLED = _as_bool(os.getenv('FLASK_DEBUG', 'false'))
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5500,http://127.0.0.1:5500,null'
    ).split(',') if o.strip()
]

CORS(
    app,
    resources={r"/api/*": {"origins": CORS_ALLOWED_ORIGINS}},
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization', 'X-Admin-Key']
)
app.register_blueprint(auth_bp)
app.register_blueprint(subscription_bp)
app.register_blueprint(pairing_bp)
app.register_blueprint(ia_bp)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'ok': True}), 200

@app.errorhandler(Exception)
def handle_unexpected_error(e):
    payload = {'error': 'Erro interno da API.'}
    if DEBUG_ENABLED:
        payload['detail'] = str(e)
    return jsonify(payload), 500


def _api_error(message: str, e: Exception = None, status: int = 500):
    payload = {'error': message}
    if DEBUG_ENABLED and e is not None:
        payload['detail'] = str(e)
    return jsonify(payload), status


@app.after_request
def apply_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/api/feedback', methods=['POST'])
def receber_feedback():
    data = request.get_json(silent=True) or {}
    rating = data.get('rating')
    topic = (data.get('topic') or 'Geral').strip()
    message = (data.get('message') or '').strip()

    if not rating or not message:
        return jsonify({'error': 'Avaliação e mensagem são obrigatórias.'}), 400

    estrelas = '★' * int(rating) + '☆' * (5 - int(rating))
    corpo = (
        f"Novo Feedback Recebido no GuardianNet:\n\n"
        f"Avaliação: {estrelas} ({rating} de 5)\n"
        f"Tópico: {topic}\n\n"
        f"Mensagem:\n{message}"
    )

    try:
        _enviar_email_api(f"Feedback GuardianNet - {topic}", corpo)
        return jsonify({'ok': True, 'mensagem': 'Feedback enviado com sucesso!'}), 200
    except Exception as e:
        return _api_error('Falha ao enviar e-mail de feedback.', e)


ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', '').strip()


def _is_admin_request() -> bool:
    if not ADMIN_API_KEY:
        return False
    return request.headers.get('X-Admin-Key', '') == ADMIN_API_KEY


def _validar_plano_payload(data):
    nome         = (data.get('nome')        or '').strip().lower()
    descricao    = (data.get('descricao')   or '').strip()
    valor_mensal = data.get('valorMensal')
    valor_anual  = data.get('valorAnual')
    ativo        = data.get('ativo', True)

    if len(nome) < 3 or not descricao:
        return None, 'Nome e descrição são obrigatórios.'

    try:
        valor_mensal = float(valor_mensal)
        valor_anual  = float(valor_anual)
    except (TypeError, ValueError):
        return None, 'Valores mensal/anual inválidos.'

    if valor_mensal < 0 or valor_anual < 0:
        return None, 'Valores não podem ser negativos.'

    return {
        'nome':         nome,
        'descricao':    descricao,
        'valor_mensal': valor_mensal,
        'valor_anual':  valor_anual,
        'ativo':        True if bool(ativo) else False,
    }, None


# ── POST /api/checkout ────────────────────────────────────────
@app.route('/api/checkout', methods=['POST'])
def checkout():
    data    = request.get_json(silent=True) or {}
    nome    = (data.get('nome')    or '').strip()
    plano   = (data.get('plano')   or '').strip()
    periodo = (data.get('periodo') or '').strip()
    metodo  = (data.get('metodo')  or '').strip()
    valor   = data.get('valor')

    if not nome or not plano or not periodo or not metodo or valor is None:
        return jsonify({"error": "Dados inválidos. Preencha todos os campos."}), 400

    try:
        executar(
            """
            INSERT INTO checkout_log (nome, plano, periodo, metodo, valor)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (nome, plano, periodo, metodo, float(valor))
        )
        return jsonify({"ok": True, "mensagem": "Assinatura registrada com sucesso!"}), 200
    except Exception as e:
        return _api_error('Falha ao registrar checkout.', e)


# ── GET /api/usuarios ─────────────────────────────────────────
@app.route('/api/usuarios', methods=['GET'])
@require_auth
def listar_usuarios():
    try:
        resultado = executar(
            "SELECT id, nome, email, ativo, criado_em FROM usuarios ORDER BY criado_em DESC",
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao listar usuários.', e)


# ── GET /api/planos ───────────────────────────────────────────
@app.route('/api/planos', methods=['GET'])
def listar_planos():
    try:
        resultado = executar(
            "SELECT id, nome, descricao, valor_mensal, valor_anual FROM planos WHERE ativo = TRUE",
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao listar planos.', e)


@app.route('/api/planos', methods=['POST'])
def criar_plano():
    if not _is_admin_request():
        return jsonify({'error': 'Acesso negado.'}), 403

    payload, erro = _validar_plano_payload(request.get_json(silent=True) or {})
    if erro:
        return jsonify({'error': erro}), 400

    try:
        executar(
            """
            INSERT INTO planos (nome, descricao, valor_mensal, valor_anual, ativo)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (payload['nome'], payload['descricao'],
             payload['valor_mensal'], payload['valor_anual'], payload['ativo'])
        )
        return jsonify({'ok': True}), 201
    except Exception as e:
        return _api_error('Falha ao criar plano.', e)


@app.route('/api/planos/<int:plano_id>', methods=['PUT'])
def atualizar_plano(plano_id: int):
    if not _is_admin_request():
        return jsonify({'error': 'Acesso negado.'}), 403

    payload, erro = _validar_plano_payload(request.get_json(silent=True) or {})
    if erro:
        return jsonify({'error': erro}), 400

    try:
        executar(
            """
            UPDATE planos
            SET nome = %s, descricao = %s,
                valor_mensal = %s, valor_anual = %s, ativo = %s
            WHERE id = %s
            """,
            (payload['nome'], payload['descricao'],
             payload['valor_mensal'], payload['valor_anual'],
             payload['ativo'], plano_id)
        )
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _api_error('Falha ao atualizar plano.', e)


@app.route('/api/planos/<int:plano_id>', methods=['DELETE'])
def remover_plano(plano_id: int):
    if not _is_admin_request():
        return jsonify({'error': 'Acesso negado.'}), 403

    try:
        executar("DELETE FROM planos WHERE id = %s", (plano_id,))
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _api_error('Falha ao remover plano.', e)


# ── GET /api/dashboard ────────────────────────────────────────
@app.route('/api/dashboard', methods=['GET'])
@require_auth
def dashboard():
    try:
        resumo = executar("SELECT * FROM vw_resumo_financeiro", fetch=True)
        assinaturas = executar(
            """
            SELECT
                COUNT(*)                                              AS total,
                SUM(CASE WHEN status = 'ativa'     THEN 1 ELSE 0 END) AS ativas,
                SUM(CASE WHEN status = 'cancelada' THEN 1 ELSE 0 END) AS canceladas
            FROM assinaturas
            """,
            fetch=True
        )
        return jsonify({
            "resumoFinanceiro": resumo,
            "assinaturas":      assinaturas[0] if assinaturas else {}
        }), 200
    except Exception as e:
        return _api_error('Falha ao carregar dashboard.', e)


# ── GET /api/historico ────────────────────────────────────────
@app.route('/api/historico', methods=['GET'])
@require_auth
def historico():
    try:
        resultado = executar(
            "SELECT * FROM checkout_log ORDER BY criado_em DESC",
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao carregar histórico.', e)


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=DEBUG_ENABLED
    )