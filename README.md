# Semeio Content Pipeline

Pipeline automatizado de pesquisa, geração e distribuição de conteúdo de marketing para o
**Semeio**, plataforma de gestão financeira voltada à tesouraria de igrejas da Igreja
Presbiteriana do Brasil (IPB).

A cada execução (agendada semanalmente ou disparada manualmente), o pipeline:

1. **Pesquisa** conteúdo relevante em fontes cadastradas em `data/fontes.yaml` (`src/scraper/`).
2. **Gera** um post de blog original e otimizado para SEO via Gemini (`src/generator/`), salvo
   em `output/post_blog.json` (título, slug, resumo/meta description, conteúdo em Markdown,
   `capa_alt`, `seo_titulo`, `seo_descricao`, tags e `status`). Uma versão legível também é
   escrita em `output/artigo.md`. A pauta-base é escolhida com **diversidade temática**: cada
   palavra-chave em `data/fontes.yaml` pertence a um `eixo`, e um eixo publicado nos últimos
   `TEMA_COOLDOWN_POSTS` posts (default 3, ver `src/config.py`) entra em *cooldown* e não é
   reaproveitado — evitando repetir o mesmo assunto em posts seguidos. O eixo de cada post
   publicado fica registrado em `data/estado.json` (`historico_posts`).
3. **Deriva** um roteiro de carrossel + legenda para Instagram a partir do artigo, salvo em
   `output/carrossel.json`.
4. **Publica** o post direto no blog do Semeio pela API de integração do Django
   (`src/publisher/`): `POST https://api.somossemeio.com.br/api/integracao/blog/posts` com
   `Authorization: Bearer <SEMEIO_BLOG_TOKEN>`. Por padrão o post vai ao ar na hora
   (`BLOG_STATUS=publicado`); com `BLOG_STATUS=rascunho` fica no admin para revisão. Reenvio
   do mesmo post (mesmo slug) não duplica. Resposta salva em `output/publicacao.json`.
5. **Avisa** no Telegram (`src/notifier/`) com o link do post no site e no admin, e manda o
   roteiro do carrossel. Se a publicação falhar, o post vai completo ao Telegram, com aviso,
   para publicação manual — o conteúdo gerado nunca se perde.

O post é gerado seguindo um checklist de SEO (palavra-chave no título/slug/resumo/1º parágrafo,
resumo de 150–160 caracteres, headings H2/H3 sem saltos, links internos para páginas do produto,
≥2 tags e conteúdo com profundidade). Os caminhos dos links internos (`/funcionalidades`,
`/precos`) ficam em `src/config.py` (`BLOG_LINKS_INTERNOS`) — ajuste se o site usar outras rotas.

Detalhes completos de requisitos e decisões arquiteturais em
[`PRD-Semeio-Content-Pipeline.md`](./PRD-Semeio-Content-Pipeline.md).

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# preencha GEMINI_API_KEY, SEMEIO_BLOG_TOKEN, TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env
```

Execute os módulos em sequência (cada um lê a saída do anterior em `output/`):

```bash
python -m src.scraper.main      # gera output/conteudo_extraido.json e atualiza data/estado.json
python -m src.generator.main    # gera output/artigo.md e output/carrossel.json
python -m src.publisher.main    # publica no blog do Semeio (output/publicacao.json)
python -m src.notifier.main     # avisa no Telegram e manda o carrossel
```

Se não houver conteúdo novo no ciclo (nenhum link inédito encontrado pelo scraper), os módulos
2-5 encerram sem erro e sem enviar nada — não há "conteúdo incompleto" para notificar.

## Testes

```bash
pytest
```

Os testes não fazem chamadas reais de rede, LLM, API do Semeio ou Telegram (tudo mockado via
`monkeypatch`).

## Execução via GitHub Actions

O workflow em `.github/workflows/pipeline.yml` roda semanalmente (segunda-feira, 12h UTC) e
também pode ser disparado manualmente pela aba **Actions → Pipeline Semeio Content → Run
workflow**, escolhendo se o post entra como `publicado` ou `rascunho`.

Secrets necessários no repositório (**Settings → Secrets and variables → Actions**):

- `GEMINI_API_KEY`
- `SEMEIO_BLOG_TOKEN` — o mesmo valor de `BLOG_INTEGRATION_TOKEN` no Django (Railway). Para
  trocar, mude nos dois lados.
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Variável opcional (**Settings → Secrets and variables → Actions → Variables**):

- `GEMINI_MODEL` (default: `gemini-2.5-pro`, definido em `src/config.py`)
- `BLOG_STATUS` (default: `publicado`) — `rascunho` para o post ficar no admin do Semeio até
  alguém revisar e publicar. Vale para a execução agendada; a manual usa a opção do disparo.

Variável opcional adicional:

- `TEMA_COOLDOWN_POSTS` (default: `3`) — quantos posts recentes mantêm seus eixos temáticos em
  cooldown antes de o assunto poder se repetir.

Ao final de cada execução, o próprio workflow commita e faz push de `data/estado.json`
atualizado (histórico de links já processados **e** dos eixos temáticos já publicados) — por
isso o job precisa de permissão de escrita em conteúdo (`permissions: contents: write`, já
configurado no workflow).

## Editando fontes e palavras-chave

Fontes de pesquisa e palavras-chave ficam em `data/fontes.yaml`, editável via PR — sem painel
administrativo (fora de escopo na v1, ver seção 8 do PRD).
