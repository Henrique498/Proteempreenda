# api.py — Proteempreenda
# Flask API com SQL Server — usa conexao.py como módulo central

from flask import Flask, request, jsonify
from flask_cors import CORS
from conexao import executar, get_connection
import pyodbc

app = Flask(__name__)
CORS(app)


# ============================================================
#  ROTA: POST /api/checkout
#  Registra um novo pagamento na tabela dbo.[User]
#  (compatibilidade com o código HTML existente)
# ============================================================
@app.route('/api/checkout', methods=['POST'])
def checkout():
    data   = request.get_json(silent=True) or {}
    nome   = (data.get('nome')   or '').strip()
    plano  = (data.get('plano')  or '').strip()
    periodo = (data.get('periodo') or '').strip()
    metodo = (data.get('metodo') or '').strip()
    valor  = data.get('valor')

    if not nome or not plano or not periodo or not metodo or valor is None:
        return jsonify({"error": "Dados inválidos. Preencha todos os campos."}), 400

    try:
        executar(
            """
            INSERT INTO dbo.[User] (Nome, Plano, Periodo, Metodo, Valor)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nome, plano, periodo, metodo, float(valor))
        )
        return jsonify({"ok": True, "mensagem": "Assinatura registrada com sucesso!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
#  ROTA: GET /api/usuarios
#  Retorna todos os usuários cadastrados
# ============================================================
@app.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    try:
        resultado = executar(
            "SELECT Id, Nome, Email, Ativo, CriadoEm FROM dbo.Usuarios ORDER BY CriadoEm DESC",
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
#  ROTA: GET /api/planos
#  Retorna os planos disponíveis
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
        return jsonify({"error": str(e)}), 500


# ============================================================
#  ROTA: GET /api/dashboard
#  Dados agregados para o dashboard.html
# ============================================================
@app.route('/api/dashboard', methods=['GET'])
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
        return jsonify({"error": str(e)}), 500


# ============================================================
#  ROTA: GET /api/historico
#  Histórico de pagamentos da tabela dbo.[User] (legado)
# ============================================================
@app.route('/api/historico', methods=['GET'])
def historico():
    try:
        resultado = executar(
            "SELECT * FROM dbo.[User] ORDER BY CreatedAt DESC",
            fetch=True
        )
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)