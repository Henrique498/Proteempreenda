import os
import xml.etree.ElementTree as ET
import pickle
import random
from river import feature_extraction, naive_bayes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

XML_PATH = os.path.join(BASE_DIR, "pan12-br-all-isys-conversation-corpus.xml")
MODEL_OUTPUT = os.path.join(BASE_DIR, "modelo_river.pkl")


def treinar():
    if not os.path.exists(XML_PATH):
        print(f"❌ Arquivo XML não encontrado em: {XML_PATH}")
        return

    # 1. Procura automaticamente qualquer arquivo .txt de predadores na pasta ia/
    predadores = set()
    txt_encontrados = 0

    for file in os.listdir(BASE_DIR):
        if file.endswith(".txt") and "predator" in file.lower():
            txt_path = os.path.join(BASE_DIR, file)
            txt_encontrados += 1
            print(f"📄 Lendo arquivo de IDs: {file}")
            with open(txt_path, "r", encoding="utf-8") as f:
                for line in f:
                    p_id = line.strip()
                    if p_id:
                        predadores.add(p_id)

    if txt_encontrados == 0:
        print(f"❌ Erro: Nenhum arquivo .txt de predadores foi encontrado na pasta: {BASE_DIR}")
        print("👉 Verifique se o arquivo .txt está salvo DENTRO da pasta 'ia/'.")
        return

    print(f"👥 Total de IDs de predadores mapeados: {len(predadores)}")
    print("📦 Lendo e processando o arquivo XML PT-BR...")

    pipeline = feature_extraction.BagOfWords(ngram_range=(1, 2)) | naive_bayes.MultinomialNB(alpha=1.0)

    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    total_predadores = 0
    total_normais = 0

    random.seed(42)

    # 2. Varre as mensagens dentro da estrutura XML
    for msg in root.findall('.//message'):
        author = msg.find('author')
        text = msg.find('text')

        if text is not None and text.text:
            mensagem_texto = text.text.strip().lower()
            author_id = author.text.strip() if author is not None and author.text else ""

            # Verifica se o autor é predador
            is_predator = author_id in predadores

            if is_predator:
                pipeline.learn_one(mensagem_texto, True)
                total_predadores += 1
            else:
                # Amostragem para manter as classes balanceadas (~1:1)
                if random.random() < 0.04:
                    pipeline.learn_one(mensagem_texto, False)
                    total_normais += 1

    print("\n✅ Treinamento em Português concluído!")
    print(f"📊 Mensagens suspeitas processadas (PT-BR): {total_predadores}")
    print(f"📊 Mensagens normais processadas (PT-BR): {total_normais}")

    # 3. Salva o novo modelo em Português
    with open(MODEL_OUTPUT, "wb") as f:
        pickle.dump(pipeline, f)

    print(f"💾 Modelo salvo com sucesso em: {MODEL_OUTPUT}")


if __name__ == "__main__":
    treinar()