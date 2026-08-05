import pickle
import psycopg2
from conexao import get_connection

NOME_MODELO = 'river_predator_pt'


def carregar_modelo_do_banco():
    """Retorna o modelo desserializado, ou None se ainda não existir no banco."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT dados FROM modelos_ia WHERE nome = %s", (NOME_MODELO,))
        row = cur.fetchone()
        if not row:
            return None
        return pickle.loads(bytes(row[0]))
    finally:
        conn.close()


def salvar_modelo_no_banco(modelo) -> None:
    """Serializa e grava (ou atualiza) o modelo no banco."""
    dados = pickle.dumps(modelo)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO modelos_ia (nome, dados, atualizado_em)
            VALUES (%s, %s, NOW())
            ON CONFLICT (nome) DO UPDATE
            SET dados = EXCLUDED.dados, atualizado_em = NOW()
            """,
            (NOME_MODELO, psycopg2.Binary(dados)),
        )
        conn.commit()
    finally:
        conn.close()