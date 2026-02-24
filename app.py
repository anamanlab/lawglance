"""Legacy Streamlit UI for IMMCAD (backend thin client).

Production runtime uses `frontend-web` + `src/immcad_api`.
This app is kept only for local development and migration troubleshooting.
"""

from __future__ import annotations

import base64
import re
import os
from urllib.parse import quote, urlsplit, urlunsplit
import uuid

from dotenv import load_dotenv
import streamlit as st

from legacy_api_client import LegacyApiClient

_MARKDOWN_SPECIAL_CHARS_PATTERN = re.compile(r"([\\`*_{}\[\]()#+\-.!])")


def _escape_markdown_text(value: object, *, default: str = "") -> str:
    text = str(value if value is not None else default).strip()
    if not text:
        text = default
    return _MARKDOWN_SPECIAL_CHARS_PATTERN.sub(r"\\\1", text)


def _safe_http_url(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.netloc:
        return None
    safe_path = quote(parts.path, safe="/:@%+~._-")
    safe_query = quote(parts.query, safe="=&%+~._-/:")
    safe_fragment = quote(parts.fragment, safe="%+~._-")
    return urlunsplit((scheme, parts.netloc, safe_path, safe_query, safe_fragment))


def add_custom_css() -> None:
    custom_css = """
    <style>
        body { font-family: 'Arial', sans-serif; }
        .st-chat-input {
            border-radius: 15px; padding: 10px;
            border: 1px solid #ddd; margin-bottom: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        .stButton > button {
            background-color: #0066cc; color: white;
            font-size: 16px; border-radius: 20px;
            padding: 10px 20px; margin-top: 5px;
            transition: background-color 0.3s ease;
        }
        .stButton > button:hover { background-color: #0052a3; }
        .st-chat-message-assistant {
            background-color: #f7f7f7; border-radius: 15px;
            padding: 15px; margin-bottom: 15px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .st-chat-message-user {
            background-color: #d9f0ff; border-radius: 15px;
            padding: 15px; margin-bottom: 15px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .st-title {
            font-family: 'Arial', sans-serif; font-weight: bold;
            color: #333; display: flex; align-items: center;
            gap: 15px; margin-top: 20px; margin-bottom: 20px;
        }
        .logo { width: 40px; height: 30px; }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def render_title() -> None:
    logo_path = "logo/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode()
        st.markdown(
            f"""
            <div class="st-title">
                <img src="data:image/png;base64,{encoded_image}" alt="IMMCAD Logo" class="logo">
                <span>IMMCAD - Legacy Dev Chat (API-backed)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="st-title">
                <span>IMMCAD - Legacy Dev Chat (API-backed)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_assistant_markdown(
    *,
    answer: str,
    citations: tuple[dict[str, object], ...],
    disclaimer: str | None,
    trace_id: str | None,
) -> str:
    lines: list[str] = [answer]

    if citations:
        lines.append("")
        lines.append("**Citations**")
        for citation in citations:
            title = _escape_markdown_text(citation.get("title", "Source"), default="Source")
            url = _safe_http_url(citation.get("url"))
            pin = _escape_markdown_text(citation.get("pin", ""), default="")
            if url:
                if pin:
                    lines.append(f"- [{title}]({url}) ({pin})")
                else:
                    lines.append(f"- [{title}]({url})")
            else:
                if pin:
                    lines.append(f"- {title} ({pin})")
                else:
                    lines.append(f"- {title}")

    if disclaimer:
        lines.append("")
        lines.append(f"_{disclaimer}_")

    if trace_id:
        lines.append("")
        lines.append(f"`trace_id: {trace_id}`")

    return "\n".join(lines)


def main() -> None:
    st.set_page_config(page_title="IMMCAD Legacy Dev UI", page_icon="logo/logo.png", layout="wide")
    load_dotenv()
    add_custom_css()
    render_title()

    st.warning(
        "Legacy development interface only. Production runtime uses frontend-web "
        "(Next.js) with the immcad_api backend."
    )

    api_base_url = (
        os.getenv("IMMCAD_STREAMLIT_API_BASE_URL")
        or os.getenv("IMMCAD_API_BASE_URL")
        or "http://127.0.0.1:8000"
    )
    api_bearer_token = os.getenv("IMMCAD_API_BEARER_TOKEN") or os.getenv("API_BEARER_TOKEN")

    st.sidebar.header("Legacy UI Configuration")
    st.sidebar.markdown(
        f"""
**API Base URL:** `{api_base_url}`

**Bearer Token:** `{"configured" if api_bearer_token else "not configured"}`

This UI sends all chat requests to `/api/chat` and does not run local retrieval,
embeddings, vector stores, or providers.
"""
    )

    if st.sidebar.button("Reset Session"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []

    thread_id = st.session_state.thread_id
    client = LegacyApiClient(api_base_url=api_base_url, bearer_token=api_bearer_token)

    for message in st.session_state.messages:
        role = "user" if message["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask a Canadian immigration question...")
    if not prompt or not prompt.strip():
        return

    prompt = prompt.strip()
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Querying IMMCAD API..."):
            result = client.send_chat(session_id=thread_id, message=prompt, locale="en-CA", mode="standard")
        if result.ok and result.answer:
            assistant_markdown = build_assistant_markdown(
                answer=result.answer,
                citations=result.citations,
                disclaimer=result.disclaimer,
                trace_id=result.trace_id,
            )
            st.markdown(assistant_markdown)
            st.session_state.messages.append({"role": "assistant", "content": assistant_markdown})
        else:
            error_message = result.error_message or "Unable to complete request."
            error_code = result.error_code or "UNKNOWN_ERROR"
            trace_line = f"\n\n`trace_id: {result.trace_id}`" if result.trace_id else ""
            assistant_markdown = (
                "I could not complete the request through the IMMCAD API.\n\n"
                f"**Error:** `{error_code}`\n\n"
                f"{error_message}{trace_line}"
            )
            st.error(assistant_markdown)
            st.session_state.messages.append({"role": "assistant", "content": assistant_markdown})


if __name__ == "__main__":
    main()
