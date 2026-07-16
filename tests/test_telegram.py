import pytest

from src.notifier import telegram


def test_dividir_mensagem_nao_divide_se_menor_que_limite():
    texto = "mensagem curta"
    assert telegram.dividir_mensagem(texto, limite=100) == [texto]


def test_dividir_mensagem_divide_respeitando_limite():
    texto = "a" * 5000
    partes = telegram.dividir_mensagem(texto, limite=4096)

    assert len(partes) == 2
    assert all(len(parte) <= 4096 for parte in partes)
    assert "".join(partes) == texto


def test_dividir_mensagem_prefere_cortar_em_paragrafo():
    paragrafo_a = "x" * 3000
    paragrafo_b = "y" * 3000
    texto = paragrafo_a + "\n\n" + paragrafo_b

    partes = telegram.dividir_mensagem(texto, limite=4096)

    assert partes[0] == paragrafo_a
    assert partes[1] == paragrafo_b


def test_enviar_levanta_erro_se_credenciais_ausentes(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(RuntimeError):
        telegram._enviar("teste")


def test_enviar_chama_api_com_payload_correto(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-456")

    chamadas = []

    class RespostaFake:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    class ClientFake:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            chamadas.append((url, json))
            return RespostaFake()

    monkeypatch.setattr(telegram.httpx, "Client", ClientFake)

    telegram._enviar("olá mundo")

    assert len(chamadas) == 1
    url, payload = chamadas[0]
    assert "token-123" in url
    assert payload == {"chat_id": "chat-456", "text": "olá mundo"}


def test_enviar_propaga_erro_quando_api_retorna_ok_false(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-456")

    class RespostaFake:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": False, "description": "chat not found"}

    class ClientFake:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            return RespostaFake()

    monkeypatch.setattr(telegram.httpx, "Client", ClientFake)

    with pytest.raises(RuntimeError):
        telegram._enviar("teste")


def test_enviar_post_blog_envia_metadados_e_conteudo(monkeypatch):
    enviados = []
    monkeypatch.setattr(telegram, "_enviar", lambda texto: enviados.append(texto))

    post = {
        "titulo": "Como organizar as finanças da igreja",
        "slug": "organizar-financas-igreja",
        "resumo": "Um guia prático para tesoureiros.",
        "conteudo": "## Introdução\n\nCorpo do artigo em Markdown.",
        "capa_alt": "Tesoureiro organizando documentos",
        "seo_titulo": "Finanças da igreja: guia",
        "seo_descricao": "Guia de finanças.",
        "tags": ["tesouraria", "gestão"],
        "status": "Publicado",
    }

    telegram.enviar_post_blog(post)

    metadados = enviados[0]
    assert telegram.CABECALHO_ARTIGO in metadados
    assert "organizar-financas-igreja" in metadados
    assert "Um guia prático para tesoureiros." in metadados
    assert "tesouraria, gestão" in metadados
    assert "Publicado" in metadados
    assert enviados[1] == telegram.CABECALHO_CONTEUDO
    assert "Corpo do artigo em Markdown." in enviados[2]


def test_enviar_carrossel_envia_cabecalho_slides_legenda_e_hashtags(monkeypatch):
    enviados = []
    monkeypatch.setattr(telegram, "_enviar", lambda texto: enviados.append(texto))

    dados = {
        "slides": [
            {"ordem": 1, "tipo": "hook", "texto": "Gancho inicial"},
            {"ordem": 2, "tipo": "cta", "texto": "Conheça o Semeio"},
        ],
        "legenda": "Legenda de teste",
        "hashtags": ["#tesouraria", "#igreja"],
    }

    telegram.enviar_carrossel(dados)

    assert enviados[0] == telegram.CABECALHO_CARROSSEL
    corpo = enviados[1]
    assert "Gancho inicial" in corpo
    assert "Legenda de teste" in corpo
    assert "#tesouraria" in corpo
