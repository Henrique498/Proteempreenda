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
    driver = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server').strip()
    server = os.getenv('DB_SERVER', '').strip()
    database = os.getenv('DB_NAME', '').strip()
    trusted = _as_bool(os.getenv('DB_TRUSTED', 'no'))
    encrypt = 'yes' if _as_bool(os.getenv('DB_ENCRYPT', 'no')) else 'no'
    trust_cert = 'yes' if _as_bool(os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'yes')) else 'no'

    if not server:
        raise RuntimeError('DB_SERVER não definido no arquivo .env.')
    if not database:
        raise RuntimeError('DB_NAME não definido no arquivo .env.')

    parts = [
        f"Driver={{{driver}}}",
        f"Server={server}",
        f"Database={database}",
        "Connection Timeout=10",
    ]

    # O driver antigo "SQL Server" costuma rejeitar alguns atributos modernos.
    if driver.lower() != 'sql server':
        parts.append(f"Encrypt={encrypt}")
        parts.append(f"TrustServerCertificate={trust_cert}")

    if trusted:
        parts.append('Trusted_Connection=yes')
        parts.append('Integrated Security=SSPI')
    else:
        user = os.getenv('DB_USER', '').strip()
        password = os.getenv('DB_PASS', '').strip()
        if not user or not password:
            raise RuntimeError('DB_USER/DB_PASS não definidos no arquivo .env.')
        parts.append(f"UID={user}")
        parts.append(f"PWD={password}")

    return ';'.join(parts) + ';'


def get_connection() -> pyodbc.Connection:
    """
    Retorna uma conexão ativa com o SQL Server.
    Levanta exceção se falhar — trate com try/except no chamador.
    """
    conn = pyodbc.connect(_build_connection_string())
    # Timeout de comandos SQL para evitar requisições penduradas.
    conn.timeout = 30
    return conn


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