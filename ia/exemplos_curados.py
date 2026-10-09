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

# Mensagens NORMAIS que não podem alertar (inclui "armadilhas": frases com palavras
# que o detector olha, como pais, segredo, foto, apagar, onde mora, idade...).
# Pode (e deve) aumentar: quanto mais variedade de conversa normal, menos falso alarme.
NORMAL = [
    # cumprimentos e conversa do dia a dia
    "oi tudo bem?", "bom dia, dormiu bem?", "boa noite", "e aí, blz?", "opa, tudo certo?",
    "oii, tava com saudade", "fala mano, beleza?", "boa tarde, tudo bem com você?",
    "tô cansado hoje kkkk", "acordei agora, que sono", "vou dormir, amanhã tem aula",
    "bom dia gente", "até amanhã!", "tchau, falou", "já volto, vou comer",
    "que calor hoje meu deus", "tá chovendo muito aqui", "hoje o dia foi longo",
    # escola
    "a prova de matemática foi difícil", "a professora passou lição de casa",
    "me ajuda com o trabalho de história?", "hoje teve educação física",
    "qual a matéria de amanhã?", "esqueci o caderno em casa", "tirei 8 na prova de ciências",
    "vc fez o dever de português?", "o trabalho em grupo é pra sexta",
    "a aula de inglês foi legal", "preciso estudar pra prova de segunda",
    "o professor faltou hoje, que bom kkk", "vamos estudar juntos na biblioteca?",
    "minha escola fica perto da praça", "a coordenadora marcou reunião de pais",
    "mandei a foto do caderno no grupo da sala", "manda a foto do trabalho de ciências",
    "manda a foto da lousa por favor", "qual o número da página do livro?",
    # jogos
    "vamos jogar roblox hoje?", "bora jogar free fire", "entra no minecraft agora",
    "ganhei uma skin nova no fortnite", "meu amigo me convidou pro servidor",
    "a partida travou de novo", "vc viu o gol do jogo de ontem?", "que horas é o jogo?",
    "manda a foto do gol que você fez", "vou deletar esse jogo, tá travando",
    "baixei outro app de música", "qual o nome do jogo que vc falou?",
    "joguei a noite toda e perdi tudo", "me passa seu nick do jogo?",
    # família e pais (palavras que o detector observa)
    "minha mãe vai me buscar na escola", "vou jantar com meus pais", "meus pais vão viajar amanhã",
    "minha mãe disse que posso dormir na sua casa", "meu pai me levou no cinema",
    "meus pais deixaram eu ir na festa", "vou pedir pros meus pais comprarem",
    "meu tio vem almoçar hoje", "minha avó fez bolo", "minha mãe tá chamando, já volto",
    "meu pai trabalha até tarde", "pedi pra minha mãe e ela deixou",
    "meus pais não sabem que eu tirei 10 e quero fazer surpresa",
    "não conta pra ninguém que eu tirei 10 hahaha", "tenho um segredo: vou ganhar um cachorro!",
    "é segredo, vou dar um presente pra minha mãe", "não conta pro João que a festa é surpresa",
    "a festa surpresa da minha irmã é sábado, não fala nada",
    # fotos, arquivos, apagar (armadilhas)
    "vou te mandar a foto da festa de ontem", "tirei uma foto do meu cachorro",
    "manda a foto do passeio da escola", "me manda o print da conversa do grupo",
    "preciso apagar o arquivo do trabalho", "apaga esse arquivo que ficou duplicado",
    "deletei o vídeo sem querer", "limpei o celular pra liberar espaço",
    "vou apagar as fotos antigas do celular", "esconde o spoiler do episódio kkk",
    "mandei a foto do caderno no grupo", "posta a foto do pôr do sol",
    # onde mora, idade, nome (armadilhas)
    "qual seu nome?", "onde você mora? eu moro no centro", "vc mora perto da escola?",
    "quantos anos você tem? eu tenho 12", "qual o endereço da festa?",
    "me manda o endereço do shopping", "eu moro no bairro novo, e vc?",
    "fiquei sozinho em casa vendo série", "tô sozinha em casa e com fome kkk",
    "você é de que cidade?", "meu aniversário é mês que vem",
    # amizade, sentimentos, elogios
    "você é muito legal", "obrigado pela ajuda no dever", "vc é minha melhor amiga",
    "eu te amo mãe", "te amo pai, boa noite", "saudade de vc", "que bom que você veio",
    "fiquei triste com a briga de hoje", "estou feliz, passei de ano", "você é muito engraçado kkkk",
    "parabéns pelo seu aniversário!", "feliz natal pra toda família", "valeu pela força, mano",
    # passeios e planos
    "quer ir ao shopping com a turma?", "vc vai na festa do João?", "vamos no cinema sábado?",
    "bora andar de bicicleta", "vamos no parque amanhã?", "a gente se vê na escola",
    "meu primo vem passar o fim de semana", "vou na casa da minha avó hoje",
    "vamos marcar o aniversário na pizzaria?", "te encontro na entrada da escola às sete",
    "vou te esperar na porta da sala", "me busca na casa do Pedro depois do jogo?",
    # internet e redes
    "você viu o vídeo daquele youtuber?", "qual a senha do wifi?", "segue meu perfil novo",
    "mudei meu nome no instagram", "vou entrar no grupo da turma", "adicionei vc no grupo",
    "me manda o link do vídeo", "esse filme é muito bom, assiste", "gostei muito da série, assiste também", "o filme que a gente viu foi ótimo", "vc gostou do show de ontem?", "baixei um aplicativo de desenho",
    "qual app vc usa pra editar vídeo?", "criei uma conta nova no tiktok",
    # comida, casa, rotina
    "estou com fome, vou lanchar", "o que tem pra almoçar?", "vou tomar banho e já volto",
    "meu cachorro rasgou o sofá kkk", "tô assistindo série com meu irmão", "vou arrumar meu quarto",
    "hoje tem pizza", "fiz um bolo de chocolate", "meu gato dormiu no meu colo",
]