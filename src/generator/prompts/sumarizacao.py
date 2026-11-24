"""Prompt de sumarização — agrupa o conteúdo extraído em um contexto unificado, focado no ângulo
(subtema) escolhido para o ciclo."""

PROMPT_SUMARIZACAO = """Você é um assistente de pesquisa. Abaixo estão trechos de artigos extraídos \
de fontes externas sobre a vida da igreja presbiteriana: tesouraria e gestão financeira, \
notícias e documentos da IPB, concílios, sociedades internas e temas afins.

O tema (ângulo) definido para o novo artigo é: "{angulo}".

Sua tarefa: produzir um resumo unificado e coeso, em português, reunindo APENAS o que for \
relevante para escrever um novo artigo original sob esse ângulo específico. Extraia dos textos \
os fatos, dados, argumentos e exemplos que ajudem a desenvolver "{angulo}"; ignore o que fugir \
desse foco. Se os textos tocarem o assunto por outra perspectiva, reenquadre-a para o ângulo \
pedido. Não copie frases literais — sintetize as ideias com suas palavras, em linguagem simples \
e direta (frases curtas, termos técnicos explicados).

Preserve com exatidão, quando aparecerem nos textos: nomes de documentos (ex.: Constituição da \
IPB, Código de Disciplina, Princípios de Liturgia, manuais das sociedades internas), concílios e \
órgãos, números de artigos e resoluções, datas e valores. Indique a fonte de cada um. Não \
acrescente nenhum desses dados que não esteja nos textos.

Artigos de referência:

{artigos}

Responda apenas com o resumo unificado, em texto corrido, sem introduções do tipo "aqui está o resumo".
"""


def montar_prompt_sumarizacao(artigos: list[dict], angulo: str) -> str:
    blocos = []
    for artigo in artigos:
        blocos.append(
            f"### Fonte: {artigo.get('fonte', 'desconhecida')}\n"
            f"Título: {artigo.get('titulo', '')}\n\n"
            f"{artigo.get('corpo', '')}"
        )
    return PROMPT_SUMARIZACAO.format(angulo=angulo, artigos="\n\n---\n\n".join(blocos))
