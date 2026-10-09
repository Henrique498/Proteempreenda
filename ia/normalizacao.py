"""Normalização de texto: usada IGUAL no treino e na análise (se mudar aqui, retreine)."""
import re

GIRIAS = {
    "vc": "você", "vcs": "vocês", "voce": "você", "pq": "porque", "pk": "porque",
    "tb": "também", "tbm": "também", "n": "não", "nao": "não", "blz": "beleza",
    "td": "tudo", "tds": "todos", "mt": "muito", "mto": "muito", "msg": "mensagem",
    "hj": "hoje", "q": "que", "cmg": "comigo", "ctg": "contigo", "obg": "obrigado",
    "vlw": "valeu", "ngm": "ninguém", "nd": "nada", "sdd": "saudade", "fds": "fim de semana",
    "pf": "por favor", "pfv": "por favor", "pfvr": "por favor", "mds": "meu deus",
    "tá": "está", "ta": "está", "to": "estou", "tô": "estou", "mae": "mãe", "pai": "pai",
}


def normalizar_texto(texto: str) -> str:
    t = (texto or "").lower()
    t = re.sub(r"https?://\S+|www\.\S+", " link ", t)      # links viram a palavra "link"
    t = re.sub(r"(.)\1{2,}", r"\1", t)                      # "nãooooo" -> "não", "kkkk" -> "k"
    t = re.sub(r"[^\w\s?!,.]", " ", t)                      # remove emoji e símbolos
    t = re.sub(r"\b(\w+)\b", lambda m: GIRIAS.get(m.group(1), m.group(1)), t)
    return re.sub(r"\s+", " ", t).strip()