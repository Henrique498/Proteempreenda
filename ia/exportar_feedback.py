"""Puxa o feedback dos responsáveis (tabela feedback_ia) para o treino.
Rode da RAIZ do projeto, com o .env:  python -m ia.exportar_feedback
O arquivo gerado tem mensagens reais: NÃO suba para o git (veja .gitignore)."""
import json
import os

from dotenv import load_dotenv

load_dotenv()

from conexao import get_connection  # noqa: E402

try:
    from .normalizacao import normalizar_texto
except ImportError:
    from normalizacao import normalizar_texto

SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exemplos_feedback.json")


def main():
    existentes = {}
    if os.path.exists(SAIDA):
        with open(SAIDA, "r", encoding="utf-8") as f:
            for ex in json.load(f).get("exemplos", []):
                existentes[normalizar_texto(ex["texto"])] = ex

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, texto, is_predator FROM feedback_ia ORDER BY id")
        rows = cur.fetchall()
    finally:
        conn.close()

    ultimo_id = 0
    for fid, texto, is_pred in rows:
        existentes[normalizar_texto(texto)] = {"texto": texto, "is_predator": bool(is_pred)}  # o mais recente vence
        ultimo_id = max(ultimo_id, fid)

    exemplos = list(existentes.values())
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump({"exemplos": exemplos}, f, ensure_ascii=False, indent=1)

    risco = sum(1 for e in exemplos if e["is_predator"])
    print(f"{len(rows)} feedback(s) lidos do banco -> {len(exemplos)} exemplos únicos "
          f"({risco} risco, {len(exemplos) - risco} normais) em {SAIDA}")
    if ultimo_id:
        print("\nDepois de retreinar e enviar o modelo novo, o log antigo pode ser limpo "
              "(o modelo já aprendeu esses casos):")
        print(f"   DELETE FROM feedback_ia WHERE id <= {ultimo_id};")


if __name__ == "__main__":
    main()