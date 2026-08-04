import unicodedata


def _normalizar(texto: str) -> str:
    texto = (texto or '').lower()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto


# Pesos por categoria — ajuste conforme os testes da equipe.
# Termos ficam em minúsculo e sem acento (a normalização cuida disso).
CATEGORIAS_RISCO = {
    'aliciamento': {
        'peso': 3,
        'termos': [
            'segredo', 'segredinho', 'nosso segredo', 'e nosso segredo',
            'nao conta pra ninguem', 'nao conta pra sua mae', 'nao conta pro seu pai',
            'fica entre nos', 'voce e madura pra sua idade', 'voce e especial pra mim',
            'confia em mim', 'me manda uma foto', 'manda foto sua', 'manda uma nude',
            'tira a roupa', 'sem roupa', 'foto sem roupa',
        ],
    },
    'isolamento': {
        'peso': 2,
        'termos': [
            'nao fala pra ninguem', 'so entre nos dois', 'apaga essa conversa',
            'deleta isso', 'deleta essa conversa', 'nao mostra pra sua mae',
            'nao mostra pro seu pai', 'guarda segredo', 'ninguem vai entender isso',
            'nao deixa ninguem ver',
        ],
    },
    'encontro_pessoal': {
        'peso': 3,
        'termos': [
            'vamos nos encontrar', 'quero te ver pessoalmente', 'me passa seu endereco',
            'onde voce mora', 'qual sua escola', 'te busco de carro',
            'vou ai te buscar', 'marca um lugar pra gente se ver', 'posso ir ai',
        ],
    },
    'conteudo_impropio': {
        'peso': 3,
        'termos': [
            'nudes', 'pelado', 'peladinha', 'genital', 'video intimo',
            'conteudo sensual', 'nu na camera', 'tira a blusa', 'tira a calcinha',
        ],
    },
    'manipulacao_emocional': {
        'peso': 1,
        'termos': [
            'eu te amo', 'voce e a unica pessoa que me entende',
            'ninguem te entende como eu', 'seus pais nao te entendem',
            'sou o unico que se importa com voce', 'voce pode confiar em mim',
            'sou seu melhor amigo', 'ninguem liga pra voce como eu ligo',
        ],
    },
}


def analisar_texto(texto: str) -> dict:
    """Analisa um texto e retorna pontuação de risco + categorias detectadas."""
    texto_norm = _normalizar(texto)
    pontuacao = 0
    categorias_detectadas = []

    for categoria, config in CATEGORIAS_RISCO.items():
        termos_encontrados = [t for t in config['termos'] if t in texto_norm]
        if termos_encontrados:
            pontuacao += config['peso'] * len(termos_encontrados)
            categorias_detectadas.append({
                'categoria': categoria,
                'termos': termos_encontrados,
            })

    if pontuacao >= 5:
        nivel = 'perigo'
    elif pontuacao >= 2:
        nivel = 'atencao'
    else:
        nivel = 'seguro'

    return {
        'pontuacao': pontuacao,
        'nivel': nivel,
        'categorias': categorias_detectadas,
    }


if __name__ == '__main__':
    testes = [
        "oi, você viu a lição de matemática?",
        "não conta pra sua mãe que a gente conversou, é nosso segredo",
        "manda uma foto sua sem roupa, só nossa mesmo",
    ]
    for t in testes:
        print(t, '->', analisar_texto(t))