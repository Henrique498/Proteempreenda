"""Mede o modelo local contra conjunto_teste.py.  Rode da raiz:  python -m ia.avaliar"""
import os
import pickle

try:
    from .conjunto_teste import NORMAL_TESTE, RISCO_TESTE
    from .decisao import decidir
    from .detector import analisar_texto
    from .exemplos_curados import NORMAL, RISCO
    from .normalizacao import normalizar_texto
except ImportError:
    from conjunto_teste import NORMAL_TESTE, RISCO_TESTE
    from decisao import decidir
    from detector import analisar_texto
    from exemplos_curados import NORMAL, RISCO
    from normalizacao import normalizar_texto

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelo_river.pkl")


def classificar(modelo, texto):
    t = normalizar_texto(texto)
    prob = float(modelo.predict_proba_one(t).get(True, 0.0))
    return decidir(analisar_texto(t)["nivel"], prob), prob


def main():
    with open(MODEL_PATH, "rb") as f:
        modelo = pickle.load(f)

    treino = {normalizar_texto(t) for t in NORMAL + RISCO}
    vazados = [t for t in NORMAL_TESTE + RISCO_TESTE if normalizar_texto(t) in treino]
    if vazados:
        print(f"ATENÇÃO: {len(vazados)} frase(s) de teste também estão no treino (resultado otimista):")
        for t in vazados:
            print("   -", t)

    falsos_alarmes, perigos_falsos, perdidos = [], [], []
    for t in NORMAL_TESTE:
        nivel, p = classificar(modelo, t)
        if nivel != "seguro":
            falsos_alarmes.append((nivel, p, t))
        if nivel == "perigo":
            perigos_falsos.append(t)
    for t in RISCO_TESTE:
        nivel, p = classificar(modelo, t)
        if nivel == "seguro":
            perdidos.append((nivel, p, t))

    n, r = len(NORMAL_TESTE), len(RISCO_TESTE)
    print(f"\nNORMAIS  : {n - len(falsos_alarmes)}/{n} ficaram seguros "
          f"(falsos alarmes: {len(falsos_alarmes)}, dos quais 'perigo': {len(perigos_falsos)})")
    print(f"DE RISCO : {r - len(perdidos)}/{r} geraram alerta (não detectados: {len(perdidos)})")
    for nivel, p, t in falsos_alarmes:
        print(f"  FALSO ALARME [{nivel} ia={p:.2f}] {t}")
    for nivel, p, t in perdidos:
        print(f"  NÃO DETECTOU [ia={p:.2f}] {t}")


if __name__ == "__main__":
    main()