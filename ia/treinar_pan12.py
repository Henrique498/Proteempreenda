import os
import pickle
import random
import xml.etree.ElementTree as ET

from river import feature_extraction, naive_bayes

from exemplos_curados import NORMAL, RISCO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XML_PATH = os.path.join(BASE_DIR, "pan12-br-all-isys-conversation-corpus.xml")
MODEL_OUTPUT = os.path.join(BASE_DIR, "modelo_river.pkl")


def treinar():
    predadores = set()
    for file in os.listdir(BASE_DIR):
        if file.endswith(".txt") and "predator" in file.lower():
            with open(os.path.join(BASE_DIR, file), "r", encoding="utf-8") as f:
                predadores |= {l.strip() for l in f if l.strip()}
    print(f"IDs de predadores: {len(predadores)}")

    pos, neg = [], []
    for msg in ET.parse(XML_PATH).getroot().findall(".//message"):
        author, text = msg.find("author"), msg.find("text")
        if text is None or not text.text:
            continue
        aid = author.text.strip() if author is not None and author.text else ""
        (pos if aid in predadores else neg).append(text.text.strip().lower())

    # MUDANÇA PRINCIPAL: usa TODAS as mensagens normais (antes só 4%).
    # Assim o modelo aprende que "oi", "escola", "pais" etc. são conversa comum.
    dados = [(t, True) for t in pos] + [(t, False) for t in neg]
    dados += [(t.lower(), True) for t in RISCO] + [(t.lower(), False) for t in NORMAL]
    random.seed(42)
    random.shuffle(dados)

    pipeline = feature_extraction.BagOfWords(ngram_range=(1, 2)) | naive_bayes.MultinomialNB(alpha=1.0)
    for texto, rotulo in dados:
        pipeline.learn_one(texto, rotulo)

    print(f"Risco: {len(pos)} + {len(RISCO)} curados | Normal: {len(neg)} + {len(NORMAL)} curados")
    with open(MODEL_OUTPUT, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"Modelo salvo em {MODEL_OUTPUT}")


if __name__ == "__main__":
    treinar()