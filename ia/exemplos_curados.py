# Exemplos escritos à mão. EDITE e AUMENTE esta lista: é a forma mais eficaz de
# ensinar a IA. Cada frase nova aqui vira aprendizado no próximo treino.

# Mensagens que DEVEM gerar alerta (aliciamento, pedido de foto, segredo, encontro...)
RISCO = [
    "não conta pra ninguém que a gente conversa",
    "isso é nosso segredo, seus pais não podem saber",
    "manda uma foto sua sem roupa",
    "me manda um nude",
    "tira a roupa e liga a câmera",
    "apaga essa conversa depois",
    "deleta as mensagens pra ninguém ver",
    "você é madura pra sua idade, especial pra mim",
    "vamos nos encontrar sozinhos, eu te busco na escola",
    "qual seu endereço? onde você mora?",
    "seus pais não te entendem, só eu me importo com você",
    "não fala pra sua mãe que eu te chamei",
    "posso ir aí quando seus pais não estiverem em casa",
    "me mostra seu corpo",
    "quer ver uma foto minha pelado?",
    "vem pro meu privado que eu te mando uns presentes",
    "tá sozinha em casa agora?",
    "guarda segredo que eu te dou dinheiro",
    "manda foto de biquíni só pra mim",
    "vamos conversar no outro app pra ninguém ver",
]

# Mensagens NORMAIS que não podem alertar (inclui frases que contêm palavras
# "perigosas" em contexto inocente: pais, segredo, foto, apagar, onde mora...)
NORMAL = [
    "oi tudo bem?", "bom dia, dormiu bem?", "boa noite", "vamos jogar roblox hoje?",
    "a prova de matemática foi difícil", "minha mãe vai me buscar na escola",
    "vou jantar com meus pais", "qual seu nome?", "manda a foto do trabalho de ciências",
    "você é muito legal", "meus pais vão viajar amanhã", "preciso apagar o arquivo do trabalho",
    "vou te mandar a foto da festa de ontem", "a professora passou lição de casa",
    "quer ir ao shopping com a turma?", "não conta pra ninguém que eu tirei 10 hahaha",
    "tenho um segredo: vou ganhar um cachorro!", "minha escola fica perto da praça",
    "onde você mora? eu moro no centro", "vc vai na festa do João?", "meu pai me levou no cinema",
    "obrigado pela ajuda no dever", "bora jogar free fire", "que horas é o jogo?",
    "manda a foto do gol que você fez", "minha mãe disse que posso dormir na sua casa",
    "você viu o vídeo daquele youtuber?", "estou com fome, vou lanchar", "hoje teve educação física",
    "me ajuda com o trabalho de história?", "vou deletar esse jogo, tá travando",
    "qual a senha do wifi?", "mandei a foto do caderno no grupo da sala",
]