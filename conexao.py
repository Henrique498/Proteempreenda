# conexao.py — GuardianNet
# Suporta autenticação Windows (DB_TRUSTED=yes) e SQL Server (usuário+senha)

import pyodbc
import threading
import queue
from dotenv import load_dotenv
import os

load_dotenv()


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _build_connection_string() -> str:
    driver     = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server').strip()
    server     = os.getenv('DB_SERVER', '').strip()
    database   = os.getenv('DB_NAME', '').strip()
    trusted    = _as_bool(os.getenv('DB_TRUSTED', 'no'))
    encrypt    = 'yes' if _as_bool(os.getenv('DB_ENCRYPT', 'no')) else 'no'
    trust_cert = 'yes' if _as_bool(os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'yes')) else 'no'

    if not server:
        raise RuntimeError('DB_SERVER não definido no arquivo .env.')
    if not database:
        raise RuntimeError('DB_NAME não definido no arquivo .env.')

    parts = [
        f"Driver={{{driver}}}",
        f"Server={server}",
        f"Database={database}",
        "Connection Timeout=15",
    ]

    # Encrypt e TrustServerCertificate só para drivers modernos
    if driver.lower() != 'sql server':
        parts.append(f"Encrypt={encrypt}")
        parts.append(f"TrustServerCertificate={trust_cert}")

    if trusted:
        # ── Autenticação Windows ──────────────────────────────────
        parts.append('Trusted_Connection=yes')
        print("[CONEXAO] Usando autenticação Windows.")
    else:
        # ── Autenticação SQL Server (usuário + senha) ─────────────
        user     = os.getenv('DB_USER', '').strip()
        password = os.getenv('DB_PASS', '').strip()

        if not user:
            raise RuntimeError(
                'DB_USER não definido no .env.\n'
                'Use DB_TRUSTED=yes para autenticação Windows\n'
                'ou preencha DB_USER e DB_PASS para autenticação SQL.'
            )
        if not password:
            raise RuntimeError(
                'DB_PASS não definido no .env.\n'
                'Preencha a senha do usuário SQL Server.'
            )

        parts.append(f"UID={user}")
        parts.append(f"PWD={password}")
        print(f"[CONEXAO] Usando autenticação SQL Server com usuário: {user}")

    return ';'.join(parts) + ';'



#  Pool de conexões simples (thread-safe)

_POOL_SIZE    = int(os.getenv('DB_POOL_SIZE', '5'))
_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '15'))

_pool: queue.Queue | None = None
_pool_lock = threading.Lock()


def _criar_conexao_raw() -> pyodbc.Connection:
    conn_str = _build_connection_string()
    conn = pyodbc.connect(conn_str, autocommit=False)
    conn.timeout = 30
    return conn


def _validar_conexao(conn: pyodbc.Connection) -> bool:
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
        sucessos = 0
        for _ in range(_POOL_SIZE):
            try:
                p.put_nowait(_criar_conexao_raw())
                sucessos += 1
            except Exception as e:
                print(f"[POOL] Aviso: não foi possível pré-criar conexão: {e}")
        _pool = p
        print(f"[POOL] Inicializado com {sucessos}/{_POOL_SIZE} conexões.")
        return _pool


def get_connection() -> pyodbc.Connection:
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
    def __init__(self, conn: pyodbc.Connection, pool: queue.Queue):
        self._conn   = conn
        self._pool   = pool
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


def executar(sql: str, params: tuple = (), fetch: bool = False):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        if fetch:
            colunas = [col[0] for col in cur.description]
            return [dict(zip(colunas, row)) for row in cur.fetchall()]
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
    try:
        conn = get_connection()
        conn.close()
        print("[OK] Conexão com SQL Server estabelecida.")
        return True
    except Exception as e:
        print(f"[ERRO] Falha na conexão: {e}")
        return False


def fechar_pool() -> None:
    global _pool
    with _pool_lock:
        if _pool is None:
            return
        while not _pool.empty():
            try:
                _pool.get_nowait().close()
            except Exception:
                pass
        _pool = None
        print("[POOL] Pool encerrado.")


if __name__ == "__main__":
    testar_conexao()