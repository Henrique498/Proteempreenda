"""Regra única de decisão (usada pelo servidor e pelo avaliar.py)."""

ORDEM = {"seguro": 0, "atencao": 1, "perigo": 2}
LIMIAR_ATENCAO = 0.60
LIMIAR_PERIGO = 0.90


def nivel_modelo(prob: float) -> str:
    if prob >= LIMIAR_PERIGO:
        return "perigo"
    if prob >= LIMIAR_ATENCAO:
        return "atencao"
    return "seguro"


def decidir(nivel_detector: str, prob: float) -> str:
    nivel_ia = nivel_modelo(prob)
    if nivel_detector == "perigo":
        return "perigo"          # termos fortes de aliciamento bastam
    if nivel_ia == "perigo" and nivel_detector == "seguro":
        return "atencao"         # só o modelo desconfiou: no máximo atenção
    return max(nivel_detector, nivel_ia, key=lambda n: ORDEM[n])