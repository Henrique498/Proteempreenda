import os
import zipfile
import xml.etree.ElementTree as ET
import pickle
import random
from river import feature_extraction, naive_bayes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ZIP_PATH = r"c:\Users\henrique.lsilva33\Downloads\pan12-sexual-predator-identification-test-and-training\pan12-sexual-predator-identification-training-corpus-2012-05-01.zip"
MODEL_OUTPUT = os.path.join(BASE_DIR, "modelo_river.pkl")

def treinar():
    if not os.path.exists(ZIP_PATH):
        print(f"❌ Arquivo não encontrado em: {ZIP_PATH}")
        return

    print(f"📦 Lendo corpus de treinamento em: {ZIP_PATH}...")

    pipeline = feature_extraction.BagOfWords(ngram_range=(1, 2)) | naive_bayes.MultinomialNB()
    predadores = set()

    with zipfile.ZipFile(ZIP_PATH, 'r') as z:
        # 1. Busca qualquer arquivo TXT dentro do ZIP que contenha 'predators' no nome
        pred_files = [f for f in z.namelist() if 'predators' in f.lower() and f.endswith('.txt')]
        
        if pred_files:
            print(f"🔍 Arquivo de IDs encontrado: {pred_files[0]}")
            with z.open(pred_files[0]) as f:
                for line in f:
                    pred_id = line.decode('utf-8', errors='ignore').strip()
                    if pred_id:
                        predadores.add(pred_id)
            print(f"👥 Total de IDs mapeados: {len(predadores)}")
        else:
            print("❌ ERRO: O arquivo com os IDs não foi encontrado no ZIP!")
            return

        # 2. Processa as mensagens nos arquivos XML
        xml_files = [f for f in z.namelist() if f.endswith('.xml')]
        print(f"📄 Processando {len(xml_files)} arquivo(s) XML...")

        total_predadores = 0
        total_normais = 0

        random.seed(42)

        for xml_file in xml_files:
            with z.open(xml_file) as f:
                try:
                    tree = ET.parse(f)
                    root = tree.getroot()

                    for msg in root.findall('.//message'):
                        author = msg.find('author')
                        text = msg.find('text')

                        if text is not None and text.text:
                            mensagem_texto = text.text.strip().lower()
                            author_id = author.text.strip() if author is not None and author.text else ""

                            is_predator = author_id in predadores

                            if is_predator:
                                pipeline.learn_one(mensagem_texto, True)
                                total_predadores += 1
                            else:
                                # Amostragem proporcional para balancear com as mensagens de risco (~1:1)
                                if random.random() < 0.035:
                                    pipeline.learn_one(mensagem_texto, False)
                                    total_normais += 1

                except Exception as e:
                    continue

        print("\n✅ Processamento do ZIP concluído!")
        print(f"📊 Mensagens suspeitas processadas: {total_predadores}")
        print(f"📊 Mensagens normais (amostradas): {total_normais}")

    if total_predadores == 0:
        print("⚠️ AVISO: Nenhum ID bateu com as mensagens do XML. Verifique o arquivo.")
        return

    # 3. Salva o modelo treinado e balanceado
    with open(MODEL_OUTPUT, "wb") as f:
        pickle.dump(pipeline, f)

    print(f"💾 Modelo salvo com sucesso em: {MODEL_OUTPUT}")

if __name__ == "__main__":
    treinar()