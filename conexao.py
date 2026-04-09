# conexao.py — GuardianNet
# Módulo central de conexão com o SQL Server via pyodbc + pool de conexões

import pyodbc
import threading
import queue
import time
from dotenv import load_dotenv
import os

load_dotenv()


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _build_connection_string() -> str:
    driver   = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server').strip()
    server   = os.getenv('DB_SERVER', '').strip()
    database = os.getenv('DB_NAME', '').strip()
    trusted  = _as_bool(os.getenv('DB_TRUSTED', 'no'))
    encrypt     = 'yes' if _as_bool(os.getenv('DB_ENCRYPT', 'no')) else 'no'
    trust_cert  = 'yes' if _as_bool(os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'yes')) else 'no'

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

    # Encrypt e TrustServerCertificate só para drivers modernos
    if driver.lower() != 'sql server':
        parts.append(f"Encrypt={encrypt}")
        parts.append(f"TrustServerCertificate={trust_cert}")

    if trusted:
        # Autenticação Windows (só funciona se as máquinas estiverem no mesmo domínio)
        parts.append('Trusted_Connection=yes')
        parts.append('Integrated Security=SSPI')
    else:
        # ── Autenticação SQL Server (usuário + senha) ──────────────
        user     = os.getenv('DB_USER', '').strip()
        password = os.getenv('DB_PASS', '').strip()
        if not user:
            raise RuntimeError(
                'DB_USER não definido no .env. '
                'Defina DB_TRUSTED=yes para autenticação Windows '
                'ou preencha DB_USER e DB_PASS para autenticação SQL.'
            )
        if not password:
            raise RuntimeError(
                'DB_PASS não definido no .env. '
                'Preencha a senha do usuário SQL Server.'
            )
        parts.append(f"UID={user}")
        parts.append(f"PWD={password}")

    return ';'.join(parts) + ';'


# ──────────────────────────────────────────────────────────────
#  Pool de conexões simples (thread-safe)
#  Elimina o overhead de abrir/fechar conexão em cada requisição.
#  Pool size: 5 conexões ativas persistentes.
# ──────────────────────────────────────────────────────────────
_POOL_SIZE    = int(os.getenv('DB_POOL_SIZE', '5'))
_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '10'))  # segundos

_pool: queue.Queue | None = None
_pool_lock = threading.Lock()


def _criar_conexao_raw() -> pyodbc.Connection:
    conn = pyodbc.connect(_build_connection_string(), autocommit=False)
    conn.timeout = 30
    return conn


def _validar_conexao(conn: pyodbc.Connection) -> bool:
    """Verifica se a conexão ainda está viva antes de reutilizá-la."""
    try:
        conn.cursor().execute("SELECT 1")
        return True
    except Exception:
        return False


def _inicializar_pool() -> queue.Queue:
    global _pool
    with _pool_lock:
        if _pool is not None:
            return _pool
        p = queue.Queue(maxsize=_POOL_SIZE)
        for _ in range(_POOL_SIZE):
            try:
                p.put_nowait(_criar_conexao_raw())
            except Exception as e:
                print(f"[POOL] Aviso: não foi possível pré-criar conexão: {e}")
        _pool = p
        print(f"[POOL] Inicializado com {_pool.qsize()} conexões.")
        return _pool


def get_connection() -> pyodbc.Connection:
    """
    Retorna uma conexão do pool.
    Se o pool estiver vazio, cria uma nova conexão temporária.
    Devolva sempre com conn.close() — o __exit__ do pool faz o retorno.
    """
    pool = _inicializar_pool()

    conn = None
    try:
        conn = pool.get(timeout=_POOL_TIMEOUT)
    except queue.Empty:
        print("[POOL] Pool esgotado, criando conexão avulsa.")
        return _criar_conexao_raw()

    if not _validar_conexao(conn):
        try:
            conn.close()
        except Exception:
            pass
        try:
            conn = _criar_conexao_raw()
        except Exception as e:
            raise RuntimeError(f"Falha ao reconectar ao banco: {e}")

    return _PooledConnection(conn, pool)


class _PooledConnection:
    """
    Wrapper que devolve a conexão ao pool ao chamar .close(),
    mantendo a mesma interface de pyodbc.Connection.
    """
    def __init__(self, conn: pyodbc.Connection, pool: queue.Queue):
        self._conn  = conn
        self._pool  = pool
        self._closed = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._pool.put_nowait(self._conn)
        except queue.Full:
            try:
                self._conn.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


# ──────────────────────────────────────────────────────────────
#  Utilitário: executar SQL de forma simples
# ──────────────────────────────────────────────────────────────
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
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
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
        print("[OK] Conexão com SQL Server estabelecida (via pool).")
        return True
    except Exception as e:
        print(f"[ERRO] Falha na conexão: {e}")
        return False


def fechar_pool() -> None:
    """Fecha todas as conexões do pool. Chamar ao encerrar a aplicação."""
    global _pool
    with _pool_lock:
        if _pool is None:
            return
        while not _pool.empty():
            try:
                conn = _pool.get_nowait()
                conn.close()
            except Exception:
                pass
        _pool = None
        print("[POOL] Pool encerrado.")


# Teste rápido ao rodar direto: python conexao.py
if __name__ == "__main__":
    testar_conexao()