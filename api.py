# api.py — Proteempreenda
# Flask API com SQL Server — usa conexao.py como módulo central

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from dotenv import load_dotenv
from conexao import executar
from auth import auth_bp, require_auth
from subscription import subscription_bp
from werkzeug.security import generate_password_hash
import os
import secrets

# 1. Carrega o .env PRIMEIRO
load_dotenv()

# 2. Cria o app DEPOIS
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


DEBUG_ENABLED = _as_bool(os.getenv('FLASK_DEBUG', 'false'))
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500,null').split(',') if o.strip()
]

CORS(
    app,
    resources={r"/api/*": {"origins": CORS_ALLOWED_ORIGINS}},
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization', 'X-Admin-Key']
)
app.register_blueprint(auth_bp)
app.register_blueprint(subscription_bp)


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    payload = {'error': 'Erro interno da API.'}
    payload['detail'] = str(e)
    return jsonify(payload), 500


def _api_error(message: str, e: Exception | None = None, status: int = 500):
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


ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', '').strip()


def _is_admin_request() -> bool:
    if not ADMIN_API_KEY:
        return False
    return request.headers.get('X-Admin-Key', '') == ADMIN_API_KEY


def _is_admin_user(user_id: int) -> bool:
    try:
        row = executar(
            "SELECT TOP 1 Tipo, Ativo FROM dbo.Usuarios WHERE Id = ?",
            (user_id,),
            fetch=True
        )
        if not row:
            return False
        tipo = str(row[0].get('Tipo') or '').strip().lower()
        ativo = bool(row[0].get('Ativo'))
        return ativo and tipo == 'admin'
    except Exception:
        return False


def _validar_plano_payload(data):
    nome = (data.get('nome') or '').strip().lower()
    descricao = (data.get('descricao') or '').strip()
    valor_mensal = data.get('valorMensal')
    valor_anual = data.get('valorAnual')
    ativo = data.get('ativo', True)

    if len(nome) < 3 or not descricao:
        return None, 'Nome e descrição são obrigatórios.'

    try:
        valor_mensal = float(valor_mensal)
        valor_anual = float(valor_anual)
    except (TypeError, ValueError):
        return None, 'Valores mensal/anual inválidos.'

    if valor_mensal < 0 or valor_anual < 0:
        return None, 'Valores não podem ser negativos.'

    return {
        'nome': nome,
        'descricao': descricao,
        'valor_mensal': valor_mensal,
        'valor_anual': valor_anual,
        'ativo': 1 if bool(ativo) else 0,
    }, None


# ============================================================
#  ROTA: POST /api/checkout
#  Endpoint legado (compatibilidade)
#  O fluxo oficial de cobrança/assinatura é /api/subscription/start
# ============================================================
@app.route('/api/checkout', methods=['POST'])
def checkout():
    return jsonify({
        "ok": True,
        "mensagem": "Checkout legado ignorado. Use /api/subscription/start para gravar assinatura e pagamento."
    }), 200


# ============================================================
#  ROTA: GET /api/usuarios
# ============================================================
@app.route('/api/usuarios', methods=['GET'])
@require_auth
def listar_usuarios():
    try:
        resultado = executar(
            "SELECT Id, Nome, Email, Telefone, Tipo, Ativo, CriadoEm, AtualizadoEm FROM dbo.Usuarios ORDER BY CriadoEm DESC",
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao listar usuários.', e)


@app.route('/api/admin/usuarios', methods=['GET'])
@require_auth
def admin_listar_usuarios():
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    try:
        resultado = executar(
            "SELECT Id, Nome, Email, Telefone, Tipo, Ativo, CriadoEm, AtualizadoEm FROM dbo.Usuarios ORDER BY CriadoEm DESC",
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao listar usuários (admin).', e)


@app.route('/api/admin/usuarios', methods=['POST'])
@require_auth
def admin_criar_usuario():
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    data = request.get_json(silent=True) or {}
    nome = (data.get('nome') or '').strip()
    email = (data.get('email') or '').strip().lower()
    senha = (data.get('senha') or '').strip()
    telefone = (data.get('telefone') or '').strip() or None
    tipo = (data.get('tipo') or 'usuario').strip().lower()

    if len(nome) < 3 or '@' not in email or len(senha) < 6:
        return jsonify({'error': 'Dados inválidos.'}), 400
    if tipo not in ('usuario', 'admin'):
        return jsonify({'error': 'Tipo inválido. Use usuario ou admin.'}), 400

    try:
        senha_hash = generate_password_hash(senha)
        executar(
            """
            INSERT INTO dbo.Usuarios (Nome, Email, SenhaHash, Telefone, Tipo, Ativo)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (nome, email, senha_hash, telefone, tipo)
        )
        return jsonify({'ok': True}), 201
    except Exception as e:
        msg = str(e)
        if '2601' in msg or '2627' in msg or 'UQ_Usuarios_Email' in msg:
            return jsonify({'error': 'E-mail já cadastrado.'}), 409
        return _api_error('Falha ao criar usuário (admin).', e)


@app.route('/api/admin/usuarios/<int:user_id>', methods=['PUT'])
@require_auth
def admin_atualizar_usuario(user_id: int):
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    data = request.get_json(silent=True) or {}
    nome = data.get('nome')
    telefone = data.get('telefone')
    ativo = data.get('ativo')
    tipo = data.get('tipo')

    try:
        atual = executar(
            "SELECT TOP 1 Nome, Telefone, Tipo, Ativo FROM dbo.Usuarios WHERE Id = ?",
            (user_id,),
            fetch=True
        )
        if not atual:
            return jsonify({'error': 'Usuário não encontrado.'}), 404

        atual = atual[0]
        nome_final = (nome.strip() if isinstance(nome, str) and nome.strip() else atual.get('Nome') or '')
        telefone_final = telefone.strip() if isinstance(telefone, str) else atual.get('Telefone')
        if telefone_final == '':
            telefone_final = None
        tipo_final = (tipo.strip().lower() if isinstance(tipo, str) and tipo.strip() else str(atual.get('Tipo') or 'usuario').lower())
        if tipo_final not in ('usuario', 'admin'):
            return jsonify({'error': 'Tipo inválido. Use usuario ou admin.'}), 400
        ativo_final = 1 if bool(ativo) else 0 if ativo is not None else (1 if bool(atual.get('Ativo')) else 0)

        executar(
            """
            UPDATE dbo.Usuarios
            SET Nome = ?,
                Telefone = ?,
                Tipo = ?,
                Ativo = ?,
                AtualizadoEm = SYSUTCDATETIME()
            WHERE Id = ?
            """,
            (nome_final, telefone_final, tipo_final, ativo_final, user_id)
        )
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _api_error('Falha ao atualizar usuário (admin).', e)


@app.route('/api/admin/usuarios/<int:user_id>', methods=['DELETE'])
@require_auth
def admin_desativar_usuario(user_id: int):
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    try:
        executar(
            """
            UPDATE dbo.Usuarios
            SET Ativo = 0,
                AtualizadoEm = SYSUTCDATETIME()
            WHERE Id = ?
            """,
            (user_id,)
        )
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _api_error('Falha ao desativar usuário (admin).', e)


# ============================================================
#  ROTA: GET /api/planos
# ============================================================
@app.route('/api/planos', methods=['GET'])
def listar_planos():
    try:
        resultado = executar(
            "SELECT Id, Nome, Descricao, ValorMensal, ValorAnual FROM dbo.Planos WHERE Ativo = 1",
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao listar planos.', e)


@app.route('/api/admin/planos', methods=['GET'])
@require_auth
def admin_listar_planos():
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    try:
        resultado = executar(
            "SELECT Id, Nome, Descricao, ValorMensal, ValorAnual, Ativo, CriadoEm FROM dbo.Planos ORDER BY Id",
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao listar planos (admin).', e)


@app.route('/api/planos', methods=['POST'])
@require_auth
def criar_plano():
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    payload, erro = _validar_plano_payload(request.get_json(silent=True) or {})
    if erro:
        return jsonify({'error': erro}), 400

    try:
        executar(
            """
            INSERT INTO dbo.Planos (Nome, Descricao, ValorMensal, ValorAnual, Ativo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload['nome'],
                payload['descricao'],
                payload['valor_mensal'],
                payload['valor_anual'],
                payload['ativo'],
            )
        )
        return jsonify({'ok': True}), 201
    except Exception as e:
        return _api_error('Falha ao criar plano.', e)


@app.route('/api/admin/planos', methods=['POST'])
@require_auth
def admin_criar_plano():
    return criar_plano()


@app.route('/api/planos/<int:plano_id>', methods=['PUT'])
@require_auth
def atualizar_plano(plano_id: int):
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    payload, erro = _validar_plano_payload(request.get_json(silent=True) or {})
    if erro:
        return jsonify({'error': erro}), 400

    try:
        executar(
            """
            UPDATE dbo.Planos
               SET Nome = ?,
                   Descricao = ?,
                   ValorMensal = ?,
                   ValorAnual = ?,
                   Ativo = ?
             WHERE Id = ?
            """,
            (
                payload['nome'],
                payload['descricao'],
                payload['valor_mensal'],
                payload['valor_anual'],
                payload['ativo'],
                plano_id,
            )
        )
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _api_error('Falha ao atualizar plano.', e)


@app.route('/api/admin/planos/<int:plano_id>', methods=['PUT'])
@require_auth
def admin_atualizar_plano(plano_id: int):
    return atualizar_plano(plano_id)


@app.route('/api/planos/<int:plano_id>', methods=['DELETE'])
@require_auth
def remover_plano(plano_id: int):
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    try:
        executar("UPDATE dbo.Planos SET Ativo = 0 WHERE Id = ?", (plano_id,))
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _api_error('Falha ao remover plano.', e)


@app.route('/api/admin/planos/<int:plano_id>', methods=['DELETE'])
@require_auth
def admin_remover_plano(plano_id: int):
    return remover_plano(plano_id)


@app.route('/api/admin/assinaturas', methods=['GET'])
@require_auth
def admin_listar_assinaturas():
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    try:
        resultado = executar(
            """
            SELECT
                a.Id,
                a.UsuarioId,
                u.Nome AS UsuarioNome,
                u.Email AS UsuarioEmail,
                p.Id AS PlanoId,
                p.Nome AS PlanoNome,
                a.Periodo,
                a.Status,
                a.DataInicio,
                a.DataFim,
                a.CriadoEm
            FROM dbo.Assinaturas a
            INNER JOIN dbo.Usuarios u ON u.Id = a.UsuarioId
            INNER JOIN dbo.Planos p ON p.Id = a.PlanoId
            ORDER BY a.Id DESC
            """,
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao listar assinaturas (admin).', e)


@app.route('/api/admin/assinaturas/<int:assinatura_id>', methods=['PUT'])
@require_auth
def admin_atualizar_assinatura(assinatura_id: int):
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    data = request.get_json(silent=True) or {}
    status = (data.get('status') or '').strip().lower()
    periodo = (data.get('periodo') or '').strip().lower()
    data_fim = data.get('dataFim')

    if status and status not in ('ativa', 'cancelada', 'expirada', 'trialing'):
        return jsonify({'error': 'Status inválido.'}), 400
    if periodo and periodo not in ('mensal', 'anual'):
        return jsonify({'error': 'Período inválido.'}), 400

    try:
        atual = executar(
            """
            SELECT TOP 1 Status, Periodo, DataFim
            FROM dbo.Assinaturas
            WHERE Id = ?
            """,
            (assinatura_id,),
            fetch=True
        )
        if not atual:
            return jsonify({'error': 'Assinatura não encontrada.'}), 404

        atual_row = atual[0]
        status_final = status or str(atual_row.get('Status') or 'ativa').lower()
        periodo_final = periodo or str(atual_row.get('Periodo') or 'mensal').lower()
        data_fim_final = data_fim if data_fim not in ('', None) else atual_row.get('DataFim')

        executar(
            """
            UPDATE dbo.Assinaturas
            SET Status = ?,
                Periodo = ?,
                DataFim = ?
            WHERE Id = ?
            """,
            (status_final, periodo_final, data_fim_final, assinatura_id)
        )
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _api_error('Falha ao atualizar assinatura (admin).', e)


@app.route('/api/admin/assinaturas/<int:assinatura_id>', methods=['DELETE'])
@require_auth
def admin_cancelar_assinatura(assinatura_id: int):
    if not _is_admin_user(g.user_id):
        return jsonify({'error': 'Acesso negado.'}), 403

    try:
        atual = executar(
            """
            SELECT TOP 1 Id
            FROM dbo.Assinaturas
            WHERE Id = ?
            """,
            (assinatura_id,),
            fetch=True
        )
        if not atual:
            return jsonify({'error': 'Assinatura não encontrada.'}), 404

        executar(
            """
            UPDATE dbo.Assinaturas
            SET Status = 'cancelada',
                DataFim = SYSUTCDATETIME()
            WHERE Id = ?
            """,
            (assinatura_id,)
        )
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _api_error('Falha ao cancelar assinatura (admin).', e)


# ============================================================
#  ROTA: GET /api/dashboard
# ============================================================
@app.route('/api/dashboard', methods=['GET'])
@require_auth
def dashboard():
    try:
        resumo = executar(
            "SELECT * FROM dbo.vw_ResumoFinanceiro",
            fetch=True
        )
        assinaturas = executar(
            """
            SELECT
                COUNT(*) AS Total,
                SUM(CASE WHEN Status = 'ativa'     THEN 1 ELSE 0 END) AS Ativas,
                SUM(CASE WHEN Status = 'cancelada' THEN 1 ELSE 0 END) AS Canceladas
            FROM dbo.Assinaturas
            """,
            fetch=True
        )
        return jsonify({
            "resumoFinanceiro": resumo,
            "assinaturas": assinaturas[0] if assinaturas else {}
        }), 200
    except Exception as e:
        return _api_error('Falha ao carregar dashboard.', e)


# ============================================================
#  ROTA: GET /api/historico
# ============================================================
@app.route('/api/historico', methods=['GET'])
@require_auth
def historico():
    try:
        resultado = executar(
            """
            SELECT
                AssinaturaId,
                Plano,
                Periodo,
                StatusAssinatura,
                DataInicio,
                DataFim,
                Valor,
                Metodo,
                StatusPagamento,
                DataPagamento
            FROM dbo.vw_Dashboard
            WHERE UsuarioId = ?
            ORDER BY DataInicio DESC
            """,
            (g.user_id,),
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao carregar histórico.', e)


# ============================================================
#  ROTAS: CONTATOS CONFIÁVEIS DO DASHBOARD
# ============================================================
@app.route('/api/contatos', methods=['GET'])
@require_auth
def listar_contatos():
    try:
        resultado = executar(
            """
            SELECT Id, Nome, Relacao, PaisCodigo, DDI, Numero, NumeroFormatado, CriadoEm
            FROM dbo.ContatosConfiaveis
            WHERE UsuarioId = ? AND Ativo = 1
            ORDER BY CriadoEm DESC, Id DESC
            """,
            (g.user_id,),
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return _api_error('Falha ao listar contatos.', e)


@app.route('/api/contatos', methods=['POST'])
@require_auth
def criar_contato():
    data = request.get_json(silent=True) or {}
    nome = (data.get('nome') or '').strip()
    relacao = (data.get('relacao') or '').strip()
    pais_codigo = (data.get('pais') or '').strip().upper()[:2] or None
    ddi = (data.get('ddi') or '').strip()
    numero = (data.get('numero') or '').strip()
    numero_fmt = (data.get('numeroFmt') or '').strip() or None

    if len(nome) < 2 or not relacao or not numero:
        return jsonify({'error': 'Dados inválidos.'}), 400

    digitos = ''.join(c for c in numero if c.isdigit())
    if len(digitos) < 8 or len(digitos) > 18:
        return jsonify({'error': 'Número inválido.'}), 400

    if ddi:
        ddi_digitos = ''.join(c for c in ddi if c.isdigit())
        ddi = ddi_digitos if ddi_digitos else None

    try:
        executar(
            """
            INSERT INTO dbo.ContatosConfiaveis
                (UsuarioId, Nome, Relacao, PaisCodigo, DDI, Numero, NumeroFormatado, Ativo)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (g.user_id, nome, relacao, pais_codigo, ddi, numero, numero_fmt)
        )
        return jsonify({'ok': True}), 201
    except Exception as e:
        return _api_error('Falha ao criar contato.', e)


@app.route('/api/contatos/<int:contato_id>', methods=['DELETE'])
@require_auth
def excluir_contato(contato_id: int):
    try:
        executar(
            """
            UPDATE dbo.ContatosConfiaveis
            SET Ativo = 0,
                AtualizadoEm = SYSUTCDATETIME()
            WHERE Id = ? AND UsuarioId = ?
            """,
            (contato_id, g.user_id)
        )
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _api_error('Falha ao excluir contato.', e)


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=DEBUG_ENABLED,
        threaded=True
    )