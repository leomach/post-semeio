"""Prompt de extração de pontos-chave e geração de roteiro de carrossel + legenda (RF10-RF12)."""

PROMPT_CARROSSEL = """Você é um redator de conteúdo para redes sociais do Semeio, plataforma de \
gestão financeira para tesourarias de igrejas da Igreja Presbiteriana do Brasil (IPB).

Tom de voz: {tom}

Público-alvo: {persona}

A partir do artigo de blog abaixo, extraia de 4 a 7 pontos principais e transforme-os em um \
roteiro de carrossel para Instagram, seguindo esta estrutura:
- Slide 1: tipo "hook" — gancho que desperta interesse
- Slides intermediários: tipo "conteudo" — pontos de valor resumidos do artigo
- Slide final: tipo "cta" — convite para ler o artigo completo e conhecer o Semeio

Também escreva uma legenda (caption) coerente com o roteiro e uma lista de ao menos 3 hashtags \
relevantes (tema de tesouraria/gestão financeira eclesiástica).

Artigo de referência:
{artigo}

Responda apenas com JSON válido, sem markdown code fence (sem ```), sem texto antes ou depois, \
seguindo exatamente este formato:
{{
  "slides": [
    {{"ordem": 1, "tipo": "hook", "texto": "..."}},
    {{"ordem": 2, "tipo": "conteudo", "texto": "..."}}
  ],
  "legenda": "...",
  "hashtags": ["#exemplo1", "#exemplo2", "#exemplo3"]
}}
"""


def montar_prompt_carrossel(artigo_markdown: str, tom: str, persona: str) -> str:
    return PROMPT_CARROSSEL.format(tom=tom, persona=persona, artigo=artigo_markdown)
