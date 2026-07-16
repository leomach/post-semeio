from google.genai import errors

from src.generator import llm_client


def _api_error(code: int, retry_delay: str | None = None):
    detalhes = {"error": {"code": code, "status": "X", "details": []}}
    if retry_delay is not None:
        detalhes["error"]["details"].append(
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay}
        )
    return errors.APIError(code, detalhes, response=None)


def test_erro_transitorio_reconhece_status_retryaveis():
    for code in (429, 500, 502, 503, 504):
        assert llm_client._erro_transitorio(_api_error(code)) is True


def test_erro_transitorio_ignora_erros_definitivos():
    for code in (400, 401, 403, 404):
        assert llm_client._erro_transitorio(_api_error(code)) is False


def test_extrai_retry_delay_do_servidor():
    exc = _api_error(429, retry_delay="24.29s")
    assert llm_client._retry_delay_do_servidor(exc) == 24.29


def test_retry_delay_ausente_retorna_none():
    exc = _api_error(503)
    assert llm_client._retry_delay_do_servidor(exc) is None


def test_esperar_respeita_retry_delay_do_servidor(monkeypatch):
    class OutcomeFake:
        def exception(self):
            return _api_error(429, retry_delay="30s")

    class RetryStateFake:
        outcome = OutcomeFake()
        attempt_number = 1
        seconds_since_start = 0
        next_action = None

        class retry_object:
            pass

    # 30s pedido pelo servidor deve prevalecer sobre o exponencial (que na 1ª tentativa é ~2s),
    # respeitando o teto de 60s.
    espera = llm_client._esperar(RetryStateFake())
    assert espera == 30.0
