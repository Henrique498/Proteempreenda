# conexao.py — Proteempreenda
# Módulo central de conexão com o SQL Server via pyodbc

import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()  # Carrega variáveis de ambiente do .env 
# ============================================================
#  STRING DE CONEXÃO — SQL Server (Windows Authentication)
#  Autenticação Windows (Trusted_Connection) — sem usuário/senha
# ============================================================
CONNECTION_STRING = (
    f"Driver={{{os.getenv('DB_DRIVER')}}};"
    f"Server={os.getenv('DB_SERVER')};"
    f"Database={os.getenv('DB_NAME')};"
    f"Trusted_Connection=yes;"
)


def get_connection() -> pyodbc.Connection:
    """
    Retorna uma conexão ativa com o SQL Server.
    Levanta exceção se falhar — trate com try/except no chamador.
    """
    return pyodbc.connect(CONNECTION_STRING)


def executar(sql: str, params: tuple = (), fetch: bool = False):
    """
    Executa um SQL simples (INSERT, UPDATE, DELETE ou SELECT).

    Parâmetros:
        sql    — string SQL com ? como placeholder
        params — tupla de valores
        fetch  — True para SELECT (retorna lista de dicts)

    Retorno:
        Lista de dicts se fetch=True, senão None.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)

        if fetch:
            colunas = [col[0] for col in cur.description]
            linhas  = cur.fetchall()
            return [dict(zip(colunas, row)) for row in linhas]

        conn.commit()
        return None
    finally:
        conn.close()


def testar_conexao() -> bool:
    """
    Testa se a conexão está funcionando.
    Retorna True se OK, False caso contrário.
    """
    try:
        conn = get_connection()
        conn.close()
        print("[OK] Conexão com SQL Server estabelecida.")
        return True
    except Exception as e:
        print(f"[ERRO] Falha na conexão: {e}")
        return False


# Teste rápido ao rodar direto: python conexao.py
if __name__ == "__main__":
    testar_conexao()