"""Prompt de sumarização — agrupa o conteúdo extraído do Módulo 1 em um contexto unificado."""

PROMPT_SUMARIZACAO = """Você é um assistente de pesquisa. Abaixo estão trechos de artigos extraídos \
de fontes externas, todos relacionados a um mesmo tema central para tesouraria e gestão \
financeira de igrejas presbiterianas.

Sua tarefa: produzir um resumo unificado e coeso desses conteúdos, em português, que sirva \
como contexto de referência para a redação de um novo artigo original. Não copie frases \
literais dos textos-fonte — sintetize as ideias, fatos e argumentos principais.

Artigos de referência:

{artigos}

Responda apenas com o resumo unificado, em texto corrido, sem introduções do tipo "aqui está o resumo".
"""


def montar_prompt_sumarizacao(artigos: list[dict]) -> str:
    blocos = []
    for artigo in artigos:
        blocos.append(
            f"### Fonte: {artigo.get('fonte', 'desconhecida')}\n"
            f"Título: {artigo.get('titulo', '')}\n\n"
            f"{artigo.get('corpo', '')}"
        )
    return PROMPT_SUMARIZACAO.format(artigos="\n\n---\n\n".join(blocos))
