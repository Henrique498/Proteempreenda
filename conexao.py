# conexao.py — Proteempreenda
# Módulo central de conexão com o SQL Server via pyodbc

import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()  # Carrega variáveis de ambiente do .env 


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _build_connection_string() -> str:
    driver = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    server = os.getenv('DB_SERVER', '')
    database = os.getenv('DB_NAME', '')
    trusted = _as_bool(os.getenv('DB_TRUSTED', 'no'))
    encrypt = 'yes' if _as_bool(os.getenv('DB_ENCRYPT', 'yes')) else 'no'
    trust_cert = 'yes' if _as_bool(os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'yes')) else 'no'

    parts = [
        f"Driver={{{driver}}}",
        f"Server={server}",
        f"Database={database}",
        f"Encrypt={encrypt}",
        f"TrustServerCertificate={trust_cert}",
        "Connection Timeout=10",
    ]

    if trusted:
        parts.append('Trusted_Connection=yes')
    else:
        parts.append(f"UID={os.getenv('DB_USER', '')}")
        parts.append(f"PWD={os.getenv('DB_PASS', '')}")

    return ';'.join(parts) + ';'


def get_connection() -> pyodbc.Connection:
    """
    Retorna uma conexão ativa com o SQL Server.
    Levanta exceção se falhar — trate com try/except no chamador.
    """
    return pyodbc.connect(_build_connection_string())


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