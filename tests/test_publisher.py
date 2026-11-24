import json

import httpx
import pytest

from src.publisher import main as publisher_main
from src.publisher import semeio_api


def _post(**extra):
    post = {
        "palavra_chave": "tesouraria da igreja",
        "titulo": "Como organizar a tesouraria da igreja",
        "slug": "organizar-tesouraria-igreja",
        "resumo": "Um guia prático para tesoureiros.",
        "conteudo": "## Introdução\n\nCorpo do artigo em Markdown.",
        "capa_url": "",
        "capa_alt": "Tesoureiro organizando documentos",
        "seo_titulo": "Tesouraria da igreja: guia",
        "seo_descricao": "Guia de tesouraria.",
        "tags": ["tesouraria", "gestão"],
        "status": "Publicado",
    }
    post.update(extra)
    return post


class RespostaFake:
    def __init__(self, status_code, corpo=None, texto=""):
        self.status_code = status_code
        self._corpo = corpo
        self.text = texto

    def json(self):
        if self._corpo is None:
            raise ValueError("sem JSON")
        return self._corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erro", request=httpx.Request("POST", "http://x"), response=self)


def _client_fake(respostas, chamadas):
    class ClientFake:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json, headers):
            chamadas.append((url, json, headers))
            return respostas.pop(0)

    return ClientFake


@pytest.fixture(autouse=True)
def _sem_espera(monkeypatch):
    # As tentativas do tenacity não podem esperar de verdade nos testes.
    monkeypatch.setattr(semeio_api._postar.retry, "sleep", lambda _: None)


# ── Payload ──

def test_payload_leva_os_campos_da_api():
    payload = semeio_api.montar_payload(_post(), status="publicado")
    assert payload == {
        "titulo": "Como organizar a tesouraria da igreja",
        "slug": "organizar-tesouraria-igreja",
        "resumo": "Um guia prático para tesoureiros.",
        "conteudo": "## Introdução\n\nCorpo do artigo em Markdown.",
        "status": "publicado",
        "tags": ["tesouraria", "gestão"],
        "seo_titulo": "Tesouraria da igreja: guia",
        "seo_descricao": "Guia de tesouraria.",
        "capa_alt": "Tesoureiro organizando documentos",
    }


def test_payload_omite_opcionais_acima_do_limite_do_django():
    payload = semeio_api.montar_payload(
        _post(seo_titulo="x" * 71, seo_descricao="y" * 181, tags=["ok", "z" * 61] + [f"t{i}" for i in range(12)]),
        status="rascunho",
    )
    assert "seo_titulo" not in payload
    assert "seo_descricao" not in payload
    assert "z" * 61 not in payload["tags"]
    assert len(payload["tags"]) == 10


def test_payload_so_manda_capa_com_url_absoluta():
    assert "capa_url" not in semeio_api.montar_payload(_post(capa_url="imagem.png"), status="publicado")
    payload = semeio_api.montar_payload(_post(capa_url="https://cdn.exemplo.com/capa.png"), status="publicado")
    assert payload["capa_url"] == "https://cdn.exemplo.com/capa.png"


def test_payload_recusa_status_desconhecido():
    with pytest.raises(ValueError):
        semeio_api.montar_payload(_post(), status="arquivado")


# ── Publicação ──

def test_publicar_envia_token_e_devolve_resposta(monkeypatch):
    monkeypatch.setenv("SEMEIO_BLOG_TOKEN", "token-abc")
    chamadas = []
    corpo = {"id": 7, "slug": "organizar-tesouraria-igreja", "status": "publicado",
             "url": "https://somossemeio.com.br/blog/organizar-tesouraria-igreja/", "admin_url": "https://api/admin/7/"}
    monkeypatch.setattr(semeio_api.httpx, "Client", _client_fake([RespostaFake(201, corpo)], chamadas))

    resultado = semeio_api.publicar_post(_post(), status="publicado")

    assert resultado == {**corpo, "ja_existia": False}
    url, payload, headers = chamadas[0]
    assert url == semeio_api.SEMEIO_API_URL
    assert headers == {"Authorization": "Bearer token-abc"}
    assert payload["status"] == "publicado"


def test_slug_repetido_nao_e_erro(monkeypatch):
    monkeypatch.setenv("SEMEIO_BLOG_TOKEN", "token-abc")
    corpo = {"erro": "Já existe", "campo": "slug", "id": 7, "url": "https://site/blog/x/", "admin_url": "https://adm/7/"}
    monkeypatch.setattr(semeio_api.httpx, "Client", _client_fake([RespostaFake(409, corpo)], []))

    resultado = semeio_api.publicar_post(_post(), status="publicado")

    assert resultado["ja_existia"] is True
    assert resultado["id"] == 7


def test_recusa_4xx_nao_repete(monkeypatch):
    monkeypatch.setenv("SEMEIO_BLOG_TOKEN", "token-abc")
    chamadas = []
    resposta = RespostaFake(400, {"erro": "resumo: muito longo", "campo": "resumo"})
    monkeypatch.setattr(semeio_api.httpx, "Client", _client_fake([resposta], chamadas))

    with pytest.raises(semeio_api.PublicacaoRecusada, match="resumo"):
        semeio_api.publicar_post(_post(), status="publicado")
    assert len(chamadas) == 1


def test_erro_5xx_repete_e_depois_desiste(monkeypatch):
    monkeypatch.setenv("SEMEIO_BLOG_TOKEN", "token-abc")
    chamadas = []
    respostas = [RespostaFake(502, texto="bad gateway") for _ in range(semeio_api.MAX_RETRIES)]
    monkeypatch.setattr(semeio_api.httpx, "Client", _client_fake(respostas, chamadas))

    with pytest.raises(httpx.HTTPStatusError):
        semeio_api.publicar_post(_post(), status="publicado")
    assert len(chamadas) == semeio_api.MAX_RETRIES


def test_erro_5xx_que_se_resolve_publica(monkeypatch):
    monkeypatch.setenv("SEMEIO_BLOG_TOKEN", "token-abc")
    corpo = {"id": 1, "url": "u", "admin_url": "a", "status": "publicado"}
    respostas = [RespostaFake(503, texto="indisponível"), RespostaFake(201, corpo)]
    monkeypatch.setattr(semeio_api.httpx, "Client", _client_fake(respostas, []))

    assert semeio_api.publicar_post(_post(), status="publicado")["id"] == 1


def test_resposta_sem_json_mostra_o_corpo(monkeypatch):
    # Ex.: a Cloudflare barrando o servidor do pipeline com uma página HTML.
    monkeypatch.setenv("SEMEIO_BLOG_TOKEN", "token-abc")
    resposta = RespostaFake(403, texto="<html>Attention Required! | Cloudflare</html>")
    monkeypatch.setattr(semeio_api.httpx, "Client", _client_fake([resposta], []))

    with pytest.raises(semeio_api.PublicacaoRecusada, match="Cloudflare"):
        semeio_api.publicar_post(_post(), status="publicado")


def test_sem_token_nao_chama_a_api(monkeypatch):
    monkeypatch.delenv("SEMEIO_BLOG_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="SEMEIO_BLOG_TOKEN"):
        semeio_api.publicar_post(_post(), status="publicado")


# ── Entrypoint ──

def test_main_grava_a_publicacao(monkeypatch, tmp_path):
    post_path, publicacao_path = tmp_path / "post_blog.json", tmp_path / "publicacao.json"
    post_path.write_text(json.dumps(_post()), encoding="utf-8")
    monkeypatch.setattr(publisher_main, "POST_BLOG_PATH", post_path)
    monkeypatch.setattr(publisher_main, "PUBLICACAO_PATH", publicacao_path)
    monkeypatch.setattr(publisher_main, "publicar_post",
                        lambda post: {"id": 3, "url": "u", "admin_url": "a", "ja_existia": False})

    assert publisher_main.main() == 0
    assert json.loads(publicacao_path.read_text(encoding="utf-8"))["id"] == 3


def test_main_falha_sem_gravar_publicacao(monkeypatch, tmp_path):
    post_path, publicacao_path = tmp_path / "post_blog.json", tmp_path / "publicacao.json"
    post_path.write_text(json.dumps(_post()), encoding="utf-8")
    monkeypatch.setattr(publisher_main, "POST_BLOG_PATH", post_path)
    monkeypatch.setattr(publisher_main, "PUBLICACAO_PATH", publicacao_path)

    def falhar(post):
        raise semeio_api.PublicacaoRecusada("400")

    monkeypatch.setattr(publisher_main, "publicar_post", falhar)

    assert publisher_main.main() == 1
    assert not publicacao_path.exists()  # o notificador cai no fallback manual


def test_main_sem_post_nao_faz_nada(monkeypatch, tmp_path):
    monkeypatch.setattr(publisher_main, "POST_BLOG_PATH", tmp_path / "inexistente.json")
    assert publisher_main.main() == 0
