import re
import unicodedata


def _normalizar(texto: str) -> str:
    texto = (texto or '').lower()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', texto)


# Peso 3 = sinal forte (sozinho já merece atenção).
# Peso 1 = sinal fraco (palavra comum: só conta junto de outros sinais).
# Os termos são buscados como palavra inteira ("apaga" não casa com "apagado").
CATEGORIAS_RISCO = {
    'aliciamento': {
        'fortes': [
            'nosso segredo', 'fica entre nos', 'nao conta pra ninguem',
            'nao conte pra ninguem', 'nao conta pros seus pais',
            'nao conta pra sua mae', 'nao fala pra sua mae',
            'seus pais nao podem saber', 'seus pais nao precisam saber',
            'voce e madura', 'especial pra mim',
            'manda foto sem roupa', 'manda uma foto sua sem roupa',
            'manda nude', 'manda nudes', 'me manda um nude',
            'tira a roupa', 'sem roupa', 'me mostra seu corpo',
        ],
        'fracos': ['segredo', 'segredinho', 'confia em mim', 'seus pais'],
    },
    'isolamento': {
        'fortes': [
            'apaga a conversa', 'apaga essa conversa', 'apaga as mensagens',
            'deleta as mensagens', 'limpa o chat', 'destroi a mensagem',
            'pra ninguem ver', 'ninguem vai entender', 'so entre nos',
            'guarda segredo', 'outro app',
        ],
        'fracos': ['apaga', 'apague', 'deleta', 'esconde'],
    },
    'encontro_pessoal': {
        'fortes': [
            'vamos nos encontrar', 'te ver pessoalmente', 'te busco na escola',
            'vou ai te buscar', 'marca um lugar', 'posso ir ai',
            'sozinha em casa', 'sozinho em casa', 'seu endereco',
        ],
        'fracos': ['onde voce mora', 'qual sua escola'],
    },
    'conteudo_impropio': {
        'fortes': [
            'nudes', 'nude', 'pelado', 'pelada', 'peladinha', 'video intimo',
            'conteudo sensual', 'nu na camera', 'tira a blusa', 'tira a calcinha',
        ],
        'fracos': [],
    },
    'manipulacao_emocional': {
        'fortes': [
            'seus pais nao te entendem', 'so eu me importo',
            'unica pessoa que te entende', 'ninguem te entende',
        ],
        'fracos': ['pode confiar em mim', 'sou seu melhor amigo'],
    },
}

PESO_FORTE = 3
PESO_FRACO = 1


def _contem(texto_norm: str, termo: str) -> bool:
    return re.search(r'(?<!\w)' + re.escape(termo) + r'(?!\w)', texto_norm) is not None


def analisar_texto(texto: str) -> dict:
    """Pontuação de risco por palavras-chave (conservadora: 1 palavra fraca NÃO alerta)."""
    texto_norm = _normalizar(texto)
    pontuacao = 0
    categorias_detectadas = []

    for categoria, cfg in CATEGORIAS_RISCO.items():
        fortes = [t for t in cfg['fortes'] if _contem(texto_norm, t)]
        # um termo fraco só vale se não estiver dentro de um forte já achado
        fracos = [t for t in cfg['fracos']
                  if _contem(texto_norm, t) and not any(t in f for f in fortes)]
        if fortes or fracos:
            pontuacao += PESO_FORTE * len(fortes) + PESO_FRACO * len(fracos)
            categorias_detectadas.append({'categoria': categoria, 'termos': fortes + fracos})

    # Sinais de categorias diferentes juntos reforçam o risco (ex.: segredo + apagar).
    if len(categorias_detectadas) >= 2:
        pontuacao += 2

    if pontuacao >= 6:
        nivel = 'perigo'
    elif pontuacao >= 3:
        nivel = 'atencao'
    else:
        nivel = 'seguro'

    return {'pontuacao': pontuacao, 'nivel': nivel, 'categorias': categorias_detectadas}