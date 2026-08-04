"""
Extrai uma amostra balanceada do corpus PAN12, traduz para PT-BR
offline (argos-translate) e salva em pan12_pt.jsonl.

Rodar UMA VEZ. Depois, treinar_pan12_pt.py lê o JSONL (rápido, sem
depender de tradução de novo).

Instalar antes:
    pip install argostranslate --break-system-packages
"""

import os
import json
import zipfile
import random
import xml.etree.ElementTree as ET

import argostranslate.package
import argostranslate.translate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_PATH = r"c:\Users\henrique.lsilva33\Downloads\pan12-sexual-predator-identification-test-and-training\pan12-sexual-predator-identification-training-corpus-2012-05-01.zip"
OUTPUT_JSONL = os.path.join(BASE_DIR, "pan12_pt.jsonl")

# Tamanho da amostra final (ajuste conforme o tempo que você tem).
# Mantemos proporção ~1:3 entre mensagens de risco e mensagens normais,
# pra não afogar o classificador com exemplos negativos demais nem de menos.
N_RISCO = 1500
N_SEGURO = 4500

random.seed(42)


def instalar_modelo_traducao():
    print("🔎 Verificando pacote de tradução en->pt...")
    argostranslate.package.update_package_index()
    disponiveis = argostranslate.package.get_available_packages()
    pacote = next(
        p for p in disponiveis if p.from_code == "en" and p.to_code == "pt"
    )
    caminho = pacote.download()
    argostranslate.package.install_from_path(caminho)
    print("✅ Pacote de tradução en->pt instalado.")


def traduzir(texto: str) -> str:
    try:
        return argostranslate.translate.translate(texto, "en", "pt")
    except Exception:
        return texto  # se falhar, mantém original em vez de perder o exemplo


def extrair_mensagens():
    if not os.path.exists(ZIP_PATH):
        print(f"❌ Arquivo não encontrado em: {ZIP_PATH}")
        return [], []

    print(f"📦 Lendo corpus de treinamento em: {ZIP_PATH}...")
    predadores = set()
    mensagens_risco = []
    mensagens_seguras = []

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        pred_files = [f for f in z.namelist() if f.endswith("predators.txt")]
        if pred_files:
            with z.open(pred_files[0]) as f:
                for line in f:
                    pid = line.decode("utf-8", errors="ignore").strip()
                    if pid:
                        predadores.add(pid)
        print(f"👥 Total de IDs de predadores mapeados: {len(predadores)}")

        xml_files = [f for f in z.namelist() if f.endswith(".xml")]
        print(f"📄 Processando {len(xml_files)} arquivo(s) XML...")

        for xml_file in xml_files:
            # Corta cedo se já temos amostra suficiente de sobra (mais rápido)
            if len(mensagens_risco) >= N_RISCO * 3 and len(mensagens_seguras) >= N_SEGURO * 3:
                break
            with z.open(xml_file) as f:
                try:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    for msg in root.findall(".//message"):
                        author = msg.find("author")
                        text = msg.find("text")
                        if text is None or not text.text:
                            continue
                        texto = text.text.strip()
                        if len(texto) < 3:
                            continue
                        author_id = author.text.strip() if author is not None and author.text else ""
                        if author_id in predadores:
                            mensagens_risco.append(texto)
                        else:
                            mensagens_seguras.append(texto)
                except Exception:
                    continue

    print(f"📊 Coletadas {len(mensagens_risco)} mensagens de risco e {len(mensagens_seguras)} seguras (antes da amostragem).")
    return mensagens_risco, mensagens_seguras


def main():
    instalar_modelo_traducao()
    risco, seguras = extrair_mensagens()

    if not risco or not seguras:
        print("❌ Não há mensagens suficientes para amostrar. Verifique o ZIP_PATH.")
        return

    amostra_risco = random.sample(risco, min(N_RISCO, len(risco)))
    amostra_seguras = random.sample(seguras, min(N_SEGURO, len(seguras)))

    print(f"🌐 Traduzindo {len(amostra_risco) + len(amostra_seguras)} mensagens (en -> pt)...")

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out:
        for i, texto in enumerate(amostra_risco):
            texto_pt = traduzir(texto)
            out.write(json.dumps({"texto": texto_pt, "is_predator": True}, ensure_ascii=False) + "\n")
            if i % 100 == 0:
                print(f"  risco: {i}/{len(amostra_risco)}")

        for i, texto in enumerate(amostra_seguras):
            texto_pt = traduzir(texto)
            out.write(json.dumps({"texto": texto_pt, "is_predator": False}, ensure_ascii=False) + "\n")
            if i % 100 == 0:
                print(f"  seguras: {i}/{len(amostra_seguras)}")

    print(f"💾 Corpus traduzido salvo em: {OUTPUT_JSONL}")


if __name__ == "__main__":
    main()