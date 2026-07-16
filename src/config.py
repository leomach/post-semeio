"""Constantes e paths centrais do pipeline."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

FONTES_PATH = DATA_DIR / "fontes.yaml"
ESTADO_PATH = DATA_DIR / "estado.json"

CONTEUDO_EXTRAIDO_PATH = OUTPUT_DIR / "conteudo_extraido.json"
ARTIGO_PATH = OUTPUT_DIR / "artigo.md"
POST_BLOG_PATH = OUTPUT_DIR / "post_blog.json"
CARROSSEL_PATH = OUTPUT_DIR / "carrossel.json"

# Scraping
USER_AGENT = "SemeioContentBot/1.0 (+contato: leandromachado@cogtime.com.br)"
RATE_LIMIT_SECONDS = float(os.environ.get("SCRAPER_RATE_LIMIT_SECONDS", "4"))
HTTP_TIMEOUT_SECONDS = 20
MAX_RETRIES = 3
CIRCUIT_BREAKER_FALHAS_CONSECUTIVAS = 3

# LLM
GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or "gemini-2.5-pro"
LLM_TIMEOUT_SECONDS = 60
# Teto de espera entre tentativas ao LLM. Alto o bastante para acomodar o retryDelay que a
# API sugere em respostas 429 (ex.: "retry in 24s") sem bater de novo antes da janela pedida.
RETRY_WAIT_MAX_SECONDS = 60

# Telegram
TELEGRAM_MAX_MENSAGEM = 4096
TELEGRAM_API_BASE = "https://api.telegram.org"

# Artigo / Post de blog (SEO)
ARTIGO_MIN_SUBTITULOS = 2
BLOG_RESUMO_MAX = 280
BLOG_RESUMO_IDEAL_MIN = 150
BLOG_RESUMO_IDEAL_MAX = 160
BLOG_CONTEUDO_MIN_PALAVRAS = 600
BLOG_MIN_TAGS = 2
BLOG_SEO_TITULO_IDEAL_MAX = 60
BLOG_SLUG_MAX = 60
# Páginas do produto para links internos (SEO). Caminhos relativos — ajuste se o site do
# Semeio usar outras rotas.
BLOG_LINKS_INTERNOS = ("/funcionalidades", "/precos")

# Carrossel
CARROSSEL_MIN_SLIDES = 4
CARROSSEL_MAX_SLIDES = 7
CARROSSEL_MIN_HASHTAGS = 3
