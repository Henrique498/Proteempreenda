# Conjunto de TESTE: nunca entra no treino. Serve só para medir o modelo (avaliar.py).
# Adicione aqui casos reais que o app errou, mas NÃO copie os mesmos para exemplos_curados.py
# (senão o teste fica "viciado").

NORMAL_TESTE = [
    "oi, tudo bem com você?", "vamos jogar minecraft depois da aula?",
    "minha mãe me busca na escola às cinco", "vou jantar com meus pais hoje",
    "qual seu nome e quantos anos você tem?", "manda a foto do caderno de ciências",
    "meus pais disseram que posso ir na festa", "tenho um segredo, vou ganhar um gato",
    "hoje vou deletar o jogo", "te adoro, amiga", "bom dia pra vcs", "td bem? to com sono",
    "a prova foi fácil, vc foi bem?", "me ajuda no dever de geografia?", "vc vai pra aula amanhã?",
    "vou lanchar e já volto", "mano esse jogo é muito bom", "baixei um app novo de fotos",
    "preciso apagar uns vídeos do celular", "minha avó fez bolo de cenoura", "vamos estudar na minha casa?",
    "meu pai me levou no shopping", "obg por me ajudar", "a festa surpresa é sábado, não fala nada",
    "qual o endereço do cinema?", "vc mora em que bairro? eu moro no jardim", "mandei a foto no grupo",
    "tô sozinho em casa jogando", "que horas é a aula de inglês?", "minha mãe deixou eu dormir aí",
    "o professor passou trabalho em dupla", "vc viu o jogo do flamengo?", "tô com dor de cabeça",
    "vou tomar banho, já volto", "manda o link da música pra mim", "feliz aniversário!!!",
    "amanhã tem prova de ciências", "esqueci minha mochila na escola", "você é muito simpática",
    "bora fazer o trabalho juntos?", "meus pais compraram um videogame novo", "hj foi um dia tranquilo",
    "tirei uma foto do pôr do sol hoje", "vou ligar pra minha tia mais tarde",
    "o cachorro do vizinho latiu a noite toda", "pq vc não veio hoje?", "vc sabe a senha do wifi?",
    "a coordenadora chamou meus pais na escola", "vou com minha mãe no mercado",
    "me passa o nick do seu jogo?", "adorei o filme, vc gostou?", "saudade de vcs, bora marcar",
    "esse segredo é só uma surpresa pro aniversário dela", "depois mando a foto do trabalho",
]

RISCO_TESTE = [
    "me manda uma foto e não conta pros seus pais",
    "não conta pra ninguém, é nosso segredo",
    "manda uma foto sem roupa pra mim",
    "você deita comigo na cama pelada",
    "seus pais não precisam saber que a gente conversa",
    "apaga as mensagens pra ninguém ver",
    "tá sozinha em casa? posso ir aí",
    "manda nudes",
]