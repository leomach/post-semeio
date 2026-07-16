"""Persona, tom de voz e prompt de geração do post de blog (RF06-RF09 + SEO)."""

TOM_DE_VOZ = (
    "Tom respeitoso, institucional e sóbrio, alinhado ao princípio presbiteriano de "
    "\"decência e ordem\" (1 Coríntios 14:40). Evitar sensacionalismo, informalidade "
    "excessiva ou linguagem de vendas agressiva."
)

PERSONA_ALVO = (
    "Tesoureiros, pastores e membros de conselhos locais de igrejas da Igreja "
    "Presbiteriana do Brasil (IPB), preocupados com boa gestão financeira e "
    "obrigações fiscais/administrativas da igreja local."
)

INSTRUCAO_CTA = (
    "Ao longo do texto (preferencialmente próximo à conclusão), inclua uma menção natural "
    "e não-comercial ao Semeio, uma plataforma de gestão financeira voltada à tesouraria de "
    "igrejas da IPB, como um recurso que pode apoiar a boa prática descrita no artigo. "
    "Essa menção deve soar como uma sugestão pertinente ao contexto, nunca como propaganda "
    "colada ao final do texto."
)

PROMPT_ARTIGO = """Você é um redator de conteúdo institucional e especialista em SEO para o \
blog do Semeio, plataforma de gestão financeira para tesourarias de igrejas da Igreja \
Presbiteriana do Brasil (IPB).

Tom de voz: {tom}

Público-alvo: {persona}

Instrução de CTA: {cta}

Com base no contexto de referência abaixo, escreva um post de blog original e otimizado para \
SEO. Primeiro identifique a PALAVRA-CHAVE PRINCIPAL do tema (ex.: "conciliação bancária da \
igreja", "prestação de contas da igreja") e use-a de forma natural no título, no resumo e no \
primeiro parágrafo do conteúdo.

Requisitos obrigatórios de SEO:
- O título deve conter a palavra-chave principal de forma natural e atrativa.
- O resumo deve ter entre 150 e 160 caracteres, conter a palavra-chave e funcionar como uma \
chamada que dê vontade de clicar (será usado como meta description).
- O conteúdo deve ter PROFUNDIDADE REAL: no mínimo 700 palavras (não entregue menos que isso; \
desenvolva cada seção com exemplos concretos e explicações completas).
- O conteúdo é Markdown e deve começar os títulos de seção em `##` (H2). NÃO use `#` (H1) em \
nenhum lugar do conteúdo — o H1 é reservado ao título do post, que vai no campo "titulo".
- Use hierarquia de headings coerente: `##` para seções e `###` para subseções. NUNCA pule \
níveis (ex.: nunca vá de `##` direto para `####`).
- Use ao menos uma lista (com `-` ou numerada).
- Inclua ao menos dois links internos em Markdown para páginas do produto Semeio, usando \
exatamente estes caminhos relativos: `/funcionalidades` e `/precos` (ex.: \
`[recursos do Semeio](/funcionalidades)`). Os links devem aparecer de forma natural no texto.
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
  "conteudo": "## Primeira seção\\n\\nParágrafo com a palavra-chave...\\n\\n## Segunda seção\\n\\n- item\\n\\n[recursos](/funcionalidades) ...",
  "capa_alt": "Descrição objetiva e descritiva da imagem de capa (acessibilidade + SEO de imagem).",
  "seo_titulo": "Título alternativo para a tag <title>, entre 50 e 60 caracteres.",
  "seo_descricao": "Meta description alternativa, se diferente do resumo.",
  "tags": ["tag relevante 1", "tag relevante 2"]
}}
"""


def montar_prompt_artigo(contexto: str) -> str:
    return PROMPT_ARTIGO.format(tom=TOM_DE_VOZ, persona=PERSONA_ALVO, cta=INSTRUCAO_CTA, contexto=contexto)
