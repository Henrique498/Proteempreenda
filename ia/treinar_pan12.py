"""Treina o modelo base. Rode da RAIZ do projeto:  python -m ia.treinar_pan12"""
import json
import os
import pickle
import random
import xml.etree.ElementTree as ET

from river import feature_extraction, naive_bayes

try:
    from .exemplos_curados import NORMAL, RISCO
    from .normalizacao import normalizar_texto
except ImportError:  # rodando como script solto
    from exemplos_curados import NORMAL, RISCO
    from normalizacao import normalizar_texto

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XML_PATH = os.path.join(BASE_DIR, "pan12-br-all-isys-conversation-corpus.xml")
MODEL_OUTPUT = os.path.join(BASE_DIR, "modelo_river.pkl")
FEEDBACK_JSON = os.path.join(BASE_DIR, "exemplos_feedback.json")  # gerado por exportar_feedback.py


def _carregar_predadores():
    ids = set()
    for file in os.listdir(BASE_DIR):
        if file.endswith(".txt") and "predator" in file.lower():
            with open(os.path.join(BASE_DIR, file), "r", encoding="utf-8") as f:
                ids |= {l.strip() for l in f if l.strip()}
    return ids


def treinar():
    if not os.path.exists(XML_PATH):
        print(f"Arquivo XML não encontrado: {XML_PATH}")
        return
    predadores = _carregar_predadores()
    if not predadores:
        print("Nenhum arquivo .txt de predadores encontrado na pasta ia/.")
        return

    pos, neg = [], []
    for msg in ET.parse(XML_PATH).getroot().findall(".//message"):
        author, text = msg.find("author"), msg.find("text")
        if text is None or not text.text:
            continue
        aid = author.text.strip() if author is not None and author.text else ""
        (pos if aid in predadores else neg).append(text.text.strip())

    dados = [(t, True) for t in pos] + [(t, False) for t in neg]
    dados += [(t, True) for t in RISCO] + [(t, False) for t in NORMAL]

    n_fb = 0
    if os.path.exists(FEEDBACK_JSON):
        with open(FEEDBACK_JSON, "r", encoding="utf-8") as f:
            for ex in json.load(f).get("exemplos", []):
                dados.append((ex["texto"], bool(ex["is_predator"])))
                n_fb += 1

    dados = [(normalizar_texto(t), y) for t, y in dados]
    dados = [(t, y) for t, y in dados if t]
    random.seed(42)
    random.shuffle(dados)

    pipeline = feature_extraction.BagOfWords(ngram_range=(1, 2)) | naive_bayes.MultinomialNB(alpha=1.0)
    for texto, rotulo in dados:
        pipeline.learn_one(texto, rotulo)

    print(f"Corpus: {len(pos)} risco / {len(neg)} normais")
    print(f"Curados: {len(RISCO)} risco / {len(NORMAL)} normais | feedback dos responsáveis: {n_fb}")
    with open(MODEL_OUTPUT, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"Modelo salvo em {MODEL_OUTPUT}")
    print("Próximo passo: python -m ia.avaliar")


if __name__ == "__main__":
    treinar()