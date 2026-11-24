# Notas de qualidade (Andre) - o que observar em cada video e corrigir nos proximos

Regra: os videos publicados sao testes. Nao refazer o que ja saiu; anotar, corrigir o motor e melhorar os proximos.

## Corrigido (entra no proximo video)
- Audio: musica estava alta. Agora voz 100% e musica 30% (loudnorm nas duas, musica x0.30).
- Fala lenta: taxa da voz subiu de +4..12% para +18..27%, pausa entre frases 0.22 -> 0.10 s.
- Uma voz so: agora narrador + voz fixa por personagem (vozes.py), com cameras no personagem que fala.
- Divisao de falas: roteiro traz "falas" [{quem, texto}] e o roteirista e o critico cobram dialogo natural.
- Ceu x fala: "manha seguinte" aparecia de noite. Agora a hora do dia (dia, manha, amanhecer, tarde, entardecer, noite, madrugada) vem do texto da cena e muda ceu, luz, mar e fogueiras.

## Para observar / a fazer
- conves: faixa escura marrom-avermelhada no terco inferior da tela na camera 'ampla' (visivel em todas as horas).
- Laboratorio do Apollo e a sala de Houston; conves em formato de caravela nao serve para Titanic.
- Cenarios do futuro (cidade neon/robos) ainda nao existem: perfil 'futuro' usa cidade/laboratorio/lua.
- Votacao A/B: o proximo episodio deve seguir a opcao mais votada (falta ler os comentarios via API).
- Formato "meme dancante" com ratos 3D (ideia do Andre, original, sem usar videos de terceiros).
- Thumbnail 403 (canal sem verificacao de telefone).

## Super atualizacao (24/11): DIRETOR (camera com historia), legenda certa, som novo
- `diretor.py`: cada cena pode ter `beats` (batidas). Cada batida = uma fala OU uma acao muda (`"texto": "", "dur": 1.8`) e diz:
  `cam` (alvo: ponto do cenario, personagem `f0/f1`, entidade `ptero/iceberg`, `grupo`), `mov` (corte/pan/chicote/zoom/recua/segue/tremor),
  `pov` (camera = olho do protagonista), `maos` (aponta/binoculo/sino/telefone), `acoes` (olha/aponta/susto/anda/corre/esconde/abaixa/comemora),
  `evento` (entidade com trajetoria entre pontos), `sfx` (whoosh/asas/impacto/susto/sino/telefone/gelo/vento/passos...), `clima` da musica.
  Roteiro antigo (so `falas`) ganha direcao automatica: a camera vai para o que a fala cita, plano de reacao em fala longa, A/B em dois chicotes.
- Pontos e entidades por cenario: `catalogo_cenas.PONTOS/ENTIDADES` (o `coerencia.py` bloqueia alvo/trajetoria que nao existe).
  2D: `selva-cretaceo` (pontos em cena2d_cretaceo.js, pterossauro gigante voando/pousando/andando). 3D: `gavea` (cesto da gavea do Titanic, iceberg).
- Legenda: um bloco por fala, so enquanto a pessoa fala (nunca junta o fim de uma fala com o comeco da outra).
- Som: `sfx.py` (efeitos sintetizados, sem direitos), trilhas Kevin MacLeod CC-BY por clima (credito automatico na descricao), ducking da musica sob a voz,
  narrador muda de video pra video e personagens ganham vozes Multilingual diferentes (`vozes.py`).
- Rodizio diario: 3 Shorts 2D + 1 Short 3D (o 3D sai como 2o Short do dia) em `publish.alternar`.

## Regra do Andre: TEMAS QUENTES (24/11/2026) - vale para TODOS os canais
- Sempre escolher temas que geram clique e debate: Chernobyl, Peste Negra, "voce e o imperador de Roma / Marco Aurelio",
  "voce e Gengis Khan perdendo terreno: retoma ou expande?", Napoleao na Russia, Nero e o incendio de Roma, decisoes impossiveis.
- Pesar a mao no drama e na decisao (formato POV / escolha A ou B), sempre com fato real.
- Terceiro Reich: nunca mostrar suastica nem simbolos, nunca escrever "nazista/nazismo/Hitler/suastica" (usar "Terceiro Reich",
  "o regime", "o ditador de bigodinho"); ponto de vista de gente comum tentando sobreviver/fugir; humor so contra o ditador e o
  regime, nunca contra as vitimas; nada de glorificar (YouTube desmonetiza apologia).
- Motor 2D tem cenarios proprios para isso: 'roma' (Forum + Coliseu; hora 'incendio' = ano 64, sem Coliseu) e 'chernobyl'
  (noite/madrugada/dia/evacuacao). O roteirista.py escreve direto em 2D quando o tema bate com esses cenarios (PRESETS_2D).
- 3D: papeis novos gengis/mongol/mongol2 (perfil 'mongol') e campones/camponesa/medico-peste (perfil 'peste').

## Regra do Andre: HISTORIA CONSTRUIDA (24/11/2026, 2a rodada)
- O video e um FILME em primeira pessoa: comeca com VOCE sozinho no lugar; cada personagem ENTRA (chega andando)
  quando fala, quando a camera vai nele ou quando o narrador o cita pelo nome. Nunca o elenco inteiro de cara.
- Corte para um lugar novo: so aparece quem participa dali (quem mora no lugar ja esta la; ninguem e teletransportado).
  Figurante generico que nao participa vira fundo do cenario (ex.: controladores em Houston), nunca na abertura.
- Figurante repetido nunca e clone: a 2a/3a copia do mesmo papel muda pele, cabelo, barba, roupa e altura (2D e 3D).
- Acao e deslocamento: cena com "acao": "anda" (voce caminha, camera avanca com passos) ou "porta" (abre a porta).
- Legenda: fim de frase SEMPRE fecha o bloco ("LUA. 14" nunca mais).
- Efeito de cena (decolagem etc.) anda pelo trecho inteiro, nao reinicia a cada corte (o foguete que subia e voltava).
  Na decolagem a tripulacao esta DENTRO do foguete: ninguem fica na base.
- Luz/efeito tem que bater com o texto (coerencia.py camada 7): "luz branca" com alarme vermelho = ERRO.
- Longo: ficha-dossie (nome, cargo, datas, missao) quando a pessoa real e citada; sem foto de pessoa real.
- Narracao: personas (voz + tom + ritmo fixos no video) em rodizio; dois videos seguidos nunca tem a mesma.
- qualidade.py inspeciona a DIRECAO antes do render (programador pula o que tiver erro; supervisor lista tudo).
