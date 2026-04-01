from flask import Flask, request, jsonify
from flask_cors import CORS
import pyodbc

app = Flask(__name__)
CORS(app)

CONNECTION_STRING = (
    "Driver={SQL Server};"
    "Server=TBS0676774W11-1;"
    "Database=empreenda;"
    "Trusted_Connection=yes;"
    "Encrypt=no;"
)

CREATE_TABLE_SQL = """
IF OBJECT_ID(N'dbo.[User]', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.[User] (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Nome NVARCHAR(150) NOT NULL,
        Plano NVARCHAR(50) NOT NULL,
        Periodo NVARCHAR(20) NOT NULL,
        Metodo NVARCHAR(20) NOT NULL,
        Valor DECIMAL(10,2) NOT NULL,
        CreatedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
"""

INSERT_SQL = """
INSERT INTO dbo.[User] (Nome, Plano, Periodo, Metodo, Valor)
VALUES (?, ?, ?, ?, ?)
"""

@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.get_json(silent=True) or {}
    nome = (data.get('nome') or '').strip()
    plano = (data.get('plano') or '').strip()
    periodo = (data.get('periodo') or '').strip()
    metodo = (data.get('metodo') or '').strip()
    valor = data.get('valor')

    if not nome or not plano or not periodo or not metodo or valor is None:
        return jsonify({"error": "Dados inválidos."}), 400

    try: 
        conn = pyodbc.connect(CONNECTION_STRING)
        cur = conn.cursor()
        cur.execute(CREATE_TABLE_SQL)
        print(INSERT_SQL)        
        cur.execute(INSERT_SQL, nome, plano, periodo, metodo, float(valor))
        cur.commit()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
