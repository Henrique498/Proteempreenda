"""Envia ia/modelo_river.pkl para o Supabase.  Da raiz:  python -m ia.enviar_modelo"""
import os
import pickle

from dotenv import load_dotenv

load_dotenv()

from ia.model_store import salvar_modelo_no_banco  # noqa: E402

CAMINHO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelo_river.pkl")

if __name__ == "__main__":
    with open(CAMINHO, "rb") as f:
        modelo = pickle.load(f)
    salvar_modelo_no_banco(modelo)
    print("ok: modelo enviado ao banco. Agora faça Manual Deploy -> Restart no Render.")