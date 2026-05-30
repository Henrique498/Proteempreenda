# conexao.py — Proteempreenda
# Módulo central de conexão com PostgreSQL (Supabase) via psycopg2

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection() -> psycopg2.extensions.connection:
    """
    Retorna uma conexão ativa com o PostgreSQL.
    Levanta exceção se falhar — trate com try/except no chamador.
    """
    return psycopg2.connect(os.getenv('DATABASE_URL'))


def executar(sql: str, params: tuple = (), fetch: bool = False):
    """
    Executa um SQL simples (INSERT, UPDATE, DELETE ou SELECT).

    Parâmetros:
        sql    — string SQL com %s como placeholder (padrão psycopg2)
        params — tupla de valores
        fetch  — True para SELECT (retorna lista de dicts)

    Retorno:
        Lista de dicts se fetch=True, senão None.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)

        if fetch:
            return [dict(row) for row in cur.fetchall()]

        conn.commit()
        return None
    finally:
        conn.close()


def testar_conexao() -> bool:
    try:
        conn = get_connection()
        conn.close()
        print("[OK] Conexão com PostgreSQL estabelecida.")
        return True
    except Exception as e:
        print(f"[ERRO] Falha na conexão: {e}")
        return False


if __name__ == "__main__":
    testar_conexao()