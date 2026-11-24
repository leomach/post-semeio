"""Persona, tom de voz e prompt de geração do post de blog (RF06-RF09 + SEO)."""

TOM_DE_VOZ = (
    "Leve, acolhedor e fácil de ler, como uma conversa com um irmão da igreja que entende do "
    "assunto e quer ajudar. Respeitoso, sem gírias e sem sensacionalismo, coerente com o "
    "princípio de \"decência e ordem\" (1 Coríntios 14:40) — mas nunca burocrático. Mesmo quando "
    "o tema é técnico (fiscal, contábil, constitucional), o texto flui: explica com exemplos do "
    "dia a dia em vez de empilhar termos. Nada de linguagem de vendas."
)

PERSONA_ALVO = (
    "Tesoureiros (muitos deles voluntários, sem formação em contabilidade), pastores, "
    "presbíteros, diáconos e líderes de sociedades internas de igrejas da Igreja Presbiteriana "
    "do Brasil (IPB). Leem no celular, entre outros compromissos, e querem entender rápido o que "
    "fazer na prática."
)

# Regras verificáveis funcionam melhor com o modelo do que adjetivos ("leve", "fluido").
GUIA_DE_ESCRITA = """\
- Frases curtas: a maioria com até 20 palavras. Uma ideia por frase.
- Parágrafos de 2 a 4 frases. Texto respirando, nada de blocos longos.
- Fale com o leitor usando "você" e, quando fizer sentido, "a sua igreja".
- Voz ativa ("o tesoureiro confere o extrato"), não passiva ("o extrato deve ser conferido").
- Todo termo técnico ou sigla é explicado com palavras simples na primeira vez que aparece \
(ex.: "a EFD-Reinf, a declaração mensal que informa à Receita...").
- Use exemplos concretos da vida da igreja local (a oferta do domingo, a reunião do Conselho, \
a tesouraria da SAF) para explicar as ideias.
- Use listas para passos e checklists; use negrito com moderação, só no que o leitor não pode \
perder.
- Comece cada seção indo direto ao ponto, sem rodeios.
- Termine com algo prático: o que o leitor pode fazer ainda esta semana.
- NÃO use estas expressões, que deixam o texto pesado: "é fundamental", "é de suma \
importância", "no cenário atual", "nos dias de hoje", "nesse sentido", "vale ressaltar", \
"cabe destacar", "faz-se necessário", "no que tange", "outrossim", "diante disso", "em suma".
- Fidelidade acima de tudo: NÃO invente números de artigos, resoluções, datas, valores, \
estatísticas ou citações. Cite documento, concílio ou artigo apenas se estiver no contexto de \
referência; na dúvida, fale de forma geral ("a Constituição da IPB prevê que...") sem número."""

INSTRUCAO_CTA = (
    "Ao longo do texto (preferencialmente próximo à conclusão), inclua uma menção natural "
    "e não-comercial ao Semeio, uma plataforma de gestão financeira voltada à tesouraria de "
    "igrejas da IPB, como um recurso que pode apoiar a boa prática descrita no artigo. "
    "Essa menção deve soar como uma sugestão pertinente ao contexto, nunca como propaganda "
    "colada ao final do texto. Se o tema não for financeiro (uma notícia da IPB, uma sociedade "
    "interna, a liturgia), faça a ponte por um aspecto prático e real — a organização, a "
    "prestação de contas, a tesouraria da sociedade — sem forçar."
)

PROMPT_ARTIGO = """Você escreve o blog do Semeio, plataforma de gestão financeira para \
tesourarias de igrejas da Igreja Presbiteriana do Brasil (IPB). Você conhece SEO e, acima de \
tudo, sabe explicar coisas sérias de um jeito simples, claro e agradável de ler.

Tom de voz: {tom}

Público-alvo: {persona}

Guia de escrita (obrigatório):
{guia}

Instrução de CTA: {cta}

Com base no contexto de referência abaixo, escreva um post de blog original, gostoso de ler e \
otimizado para SEO. O tema pode ser financeiro, institucional (notícias, concílios, documentos \
da IPB), das sociedades internas ou da vida da igreja local: siga o ângulo do contexto. Primeiro identifique a PALAVRA-CHAVE PRINCIPAL do tema (ex.: "conciliação bancária da \
igreja", "prestação de contas da igreja") e use-a de forma natural no título, no resumo e no \
primeiro parágrafo do conteúdo.

Requisitos obrigatórios de SEO:
- O título deve conter a palavra-chave principal de forma natural e atrativa, em linguagem \
simples (prefira "Como fazer a conciliação bancária da igreja" a "A importância da \
conciliação bancária no contexto eclesiástico").
- O resumo deve ter entre 150 e 160 caracteres, conter a palavra-chave e funcionar como uma \
chamada que dê vontade de clicar (será usado como meta description).
- O conteúdo deve ter PROFUNDIDADE REAL: no mínimo 700 palavras (não entregue menos que isso). \
Profundidade vem de exemplos e explicações práticas, não de frases longas: o texto continua \
leve e fácil mesmo sendo completo. Para chegar lá, organize o post em 4 a 6 seções `##`, cada \
uma com 2 a 4 parágrafos curtos, e traga em cada seção pelo menos um exemplo da vida da igreja \
ou um passo prático.
- O conteúdo é Markdown e deve começar os títulos de seção em `##` (H2). NÃO use `#` (H1) em \
nenhum lugar do conteúdo — o H1 é reservado ao título do post, que vai no campo "titulo".
- Use hierarquia de headings coerente: `##` para seções e `###` para subseções. NUNCA pule \
níveis (ex.: nunca vá de `##` direto para `####`).
- Use ao menos uma lista (com `-` ou numerada).
- Inclua ao menos dois links internos em Markdown para páginas do produto Semeio, usando \
exatamente estes caminhos relativos, com a barra final: `/funcionalidades/` e `/precos/` (ex.: \
`[recursos do Semeio](/funcionalidades/)`). Os links devem aparecer de forma natural no texto.
- A palavra-chave principal deve aparecer no primeiro parágrafo do conteúdo.

Contexto de referência:
{contexto}

Responda APENAS com JSON válido, sem markdown code fence (sem ```), sem texto antes ou depois, \
seguindo exatamente este formato:
{{
  "palavra_chave": "a palavra-chave principal escolhida",
  "titulo": "Título do post com a palavra-chave (H1, sem # no texto)",
  "slug": "slug-curto-com-a-palavra-chave",
  "resumo": "Resumo/meta description entre 150 e 160 caracteres, com a palavra-chave.",
  "conteudo": "## Primeira seção\\n\\nParágrafo com a palavra-chave...\\n\\n## Segunda seção\\n\\n- item\\n\\n[recursos](/funcionalidades/) ...",
  "capa_alt": "Descrição objetiva e descritiva da imagem de capa (acessibilidade + SEO de imagem).",
  "seo_titulo": "Título alternativo para a tag <title>, entre 50 e 60 caracteres.",
  "seo_descricao": "Meta description alternativa, se diferente do resumo.",
  "tags": ["tag relevante 1", "tag relevante 2"]
}}
"""


PROMPT_EXPANSAO = """Você escreve o blog do Semeio. O post abaixo ficou curto: tem {palavras} \
palavras e precisa de pelo menos {minimo}. Reescreva-o com pelo menos {alvo} palavras.

Como expandir:
- Mantenha o mesmo tom leve, as mesmas seções `##` e os links internos que já existem.
- Ganhe tamanho com exemplos da vida da igreja, passos práticos e perguntas que o leitor faria, \
não com frases longas nem repetição.
- Use só fatos do contexto de referência: não invente artigos, resoluções, datas, valores ou \
estatísticas.

Guia de escrita (obrigatório):
{guia}

Contexto de referência:
{contexto}

Post atual (Markdown):
{conteudo}

Responda APENAS com o conteúdo completo em Markdown, começando pela primeira seção `##`, sem \
code fence e sem texto antes ou depois.
"""


def montar_prompt_expansao(conteudo: str, contexto: str, palavras: int, minimo: int) -> str:
    return PROMPT_EXPANSAO.format(
        palavras=palavras, minimo=minimo, alvo=minimo + 150, guia=GUIA_DE_ESCRITA,
        contexto=contexto, conteudo=conteudo,
    )


def montar_prompt_artigo(contexto: str) -> str:
    return PROMPT_ARTIGO.format(
        tom=TOM_DE_VOZ, persona=PERSONA_ALVO, guia=GUIA_DE_ESCRITA, cta=INSTRUCAO_CTA, contexto=contexto
    )
