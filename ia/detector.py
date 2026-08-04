import unicodedata


def _normalizar(texto: str) -> str:
    texto = (texto or '').lower()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto


# Categorias e termos flexibilizados para evitar falhas por variações de frases
CATEGORIAS_RISCO = {
    'aliciamento': {
        'peso': 3,
        'termos': [
            'segredo', 'segredinho', 'nosso segredo', 'fica entre nos',
            'nao conta', 'nao conte', 'nao fale', 'seus pais',
            'voce e madura', 'especial pra mim', 'confia em mim',
            'manda foto', 'manda uma foto', 'manda nude', 'nudes',
            'tira a roupa', 'sem roupa', 'foto sem roupa',
        ],
    },
    'isolamento': {
        'peso': 2,
        'termos': [
            'apaga', 'apague', 'deleta', 'delete', 'esconde', 'esconder',
            'nao mostra', 'nao deixa ninguem', 'so entre nos', 'guarda segredo',
            'ninguem vai entender', 'limpa o chat', 'destroi a mensagem',
        ],
    },
    'encontro_pessoal': {
        'peso': 3,
        'termos': [
            'vamos nos encontrar', 'te ver pessoalmente', 'seu endereco',
            'onde voce mora', 'qual sua escola', 'te busco',
            'vou ai te buscar', 'marca um lugar', 'posso ir ai',
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
            'eu te amo', 'unica pessoa que me entende',
            'ninguem te entende', 'seus pais nao te entendem',
            'so eu me importo', 'pode confiar em mim', 'sou seu melhor amigo',
        ],
    },
}


def analisar_texto(texto: str) -> dict:
    """Analisa um texto e retorna a pontuação de risco e categorias detectadas."""
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
        "Não conta para os seus pais sobre a nossa conversa, tá",
        "Apaga essas mensagens antes que alguém veja",
        "manda uma foto sua sem roupa, só nossa mesmo",
    ]
    for t in testes:
        print(t, '->', analisar_texto(t))