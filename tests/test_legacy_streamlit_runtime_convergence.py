from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "app.py"

FORBIDDEN_APP_PATTERNS = (
    r"from lawglance_main import",
    r"\bimport lawglance_main\b",
    r"from chains import",
    r"\bimport chains\b",
    r"from cache import",
    r"\bimport cache\b",
    r"from prompts import",
    r"\bimport prompts\b",
    r"from langchain",
    r"langchain_",
    r"OpenAIEmbeddings",
    r"ChatOpenAI",
    r"Chroma\(",
)


def test_streamlit_app_is_thin_api_client() -> None:
    app_source = APP_PATH.read_text(encoding="utf-8")
    assert "LegacyApiClient" in app_source
    assert "client.send_chat(" in app_source
    assert "/api/chat" in app_source


def test_streamlit_app_does_not_embed_local_rag_runtime() -> None:
    app_source = APP_PATH.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_APP_PATTERNS:
        assert re.search(pattern, app_source) is None
