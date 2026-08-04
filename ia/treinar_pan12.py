import os
import zipfile
import xml.etree.ElementTree as ET
import pickle
from river import feature_extraction, naive_bayes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Aponta diretamente para o zip de treinamento na pasta extraída
ZIP_PATH = r"c:\Users\henrique.lsilva33\Downloads\pan12-sexual-predator-identification-test-and-training\pan12-sexual-predator-identification-training-corpus-2012-05-01.zip"
MODEL_OUTPUT = os.path.join(BASE_DIR, "modelo_river.pkl")

def treinar():
    if not os.path.exists(ZIP_PATH):
        print(f"❌ Arquivo não encontrado em: {ZIP_PATH}")
        return

    print(f"📦 Lendo corpus de treinamento em: {ZIP_PATH}...")

    pipeline = feature_extraction.BagOfWords() | naive_bayes.MultinomialNB()
    predadores = set()

    with zipfile.ZipFile(ZIP_PATH, 'r') as z:
        # 1. Carrega lista de IDs
        pred_files = [f for f in z.namelist() if f.endswith('predators.txt')]
        if pred_files:
            with z.open(pred_files[0]) as f:
                for line in f:
                    pred_id = line.decode('utf-8', errors='ignore').strip()
                    if pred_id:
                        predadores.add(pred_id)
            print(f"👥 Total de IDs mapeados: {len(predadores)}")

        # 2. Processa mensagens
        xml_files = [f for f in z.namelist() if f.endswith('.xml')]
        print(f"📄 Processando {len(xml_files)} arquivo(s) XML...")

        total_mensagens = 0

        for xml_file in xml_files:
            with z.open(xml_file) as f:
                try:
                    tree = ET.parse(f)
                    root = tree.getroot()

                    for msg in root.findall('.//message'):
                        author = msg.find('author')
                        text = msg.find('text')

                        if text is not None and text.text:
                            mensagem_texto = text.text.strip()
                            author_id = author.text.strip() if author is not None and author.text else ""

                            is_predator = author_id in predadores
                            pipeline.learn_one(mensagem_texto, is_predator)
                            total_mensagens += 1

                except Exception:
                    continue

        print(f"Treinamento concluído com sucesso! {total_mensagens} mensagens processadas.")

    # 3. Salva o modelo
    with open(MODEL_OUTPUT, "wb") as f:
        pickle.dump(pipeline, f)

    print(f"Modelo salvo com sucesso em: {MODEL_OUTPUT}")

if __name__ == "__main__":
    treinar()