import base64
import os
import uuid

import httpx
import streamlit as st
from dotenv import load_dotenv


st.set_page_config(page_title="IMMCAD", page_icon="logo/logo.png", layout="wide")

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN")
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "en-CA")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
REQUEST_TIMEOUT_SECONDS = float(os.getenv("UI_API_TIMEOUT_SECONDS", "30"))


def add_custom_css() -> None:
    custom_css = """
    <style>
        body { font-family: 'Arial', sans-serif; }
        .st-chat-input {
            border-radius: 15px; padding: 10px;
            border: 1px solid #ddd; margin-bottom: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
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
        .chat-input-container {
            position: fixed; bottom: 0; width: 100%;
            background-color: #f0f0f0; padding: 20px;
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
            display: flex; gap: 10px;
        }
        .chat-input { flex-grow: 1; }
        .st-title {
            font-family: 'Arial', sans-serif; font-weight: bold;
            color: #333; display: flex; align-items: center;
            gap: 15px; margin-top: 20px; margin-bottom: 20px;
        }
        .logo { width: 40px; height: 30px; }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def _render_title() -> None:
    logo_path = "logo/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode()
        st.markdown(
            f"""
            <div class="st-title">
                <img src="data:image/png;base64,{encoded_image}" alt="IMMCAD Logo" class="logo">
                <span>IMMCAD - Canadian Immigration Information Assistant</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="st-title">
                <span>IMMCAD - Canadian Immigration Information Assistant</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_sidebar() -> None:
    st.sidebar.header("About IMMCAD")
    st.sidebar.markdown(
        """
IMMCAD is a Canadian immigration information assistant.

Runtime:
- UI: Streamlit
- Backend: FastAPI (`/api/chat`)

Disclaimer:
- Informational responses only, not legal advice.
"""
    )
    st.sidebar.caption(f"API base URL: {API_BASE_URL}")


def _require_hardened_auth_config() -> None:
    if ENVIRONMENT in {"production", "prod", "ci"} and not API_BEARER_TOKEN:
        st.error("API_BEARER_TOKEN is required when ENVIRONMENT is production/prod/ci.")
        st.stop()


def _build_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {API_BEARER_TOKEN}"
    return headers


def _format_error_message(response: httpx.Response) -> str:
    trace_id = response.headers.get("x-trace-id", "")
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    error = payload.get("error", {})
    message = error.get("message", response.text or "Unexpected API error")
    envelope_trace_id = error.get("trace_id")
    resolved_trace_id = envelope_trace_id or trace_id
    if resolved_trace_id:
        return f"{message} (trace_id={resolved_trace_id})"
    return message


def call_chat_api(message: str, session_id: str) -> dict:
    payload = {
        "session_id": session_id,
        "message": message,
        "locale": DEFAULT_LOCALE,
        "mode": "standard",
    }
    url = f"{API_BASE_URL}/api/chat"

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload, headers=_build_headers())
    except httpx.RequestError as exc:
        raise RuntimeError(f"Unable to reach API at {url}: {exc}") from exc

    if response.status_code >= 400:
        raise RuntimeError(_format_error_message(response))

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("Chat API returned invalid JSON response.") from exc


def _render_citations(citations: list[dict]) -> str:
    if not citations:
        return ""
    lines = ["", "Sources:"]
    for item in citations:
        title = item.get("title", "Source")
        pin = item.get("pin", "")
        url = item.get("url", "")
        if pin:
            lines.append(f"- {title} ({pin}) - {url}")
        else:
            lines.append(f"- {title} - {url}")
    return "\n".join(lines)


def _format_assistant_message(payload: dict) -> str:
    answer = str(payload.get("answer", "")).strip()
    citations = payload.get("citations", [])
    fallback_used = payload.get("fallback_used", {})
    disclaimer = str(payload.get("disclaimer", "")).strip()

    sections = [answer]
    citations_block = _render_citations(citations)
    if citations_block:
        sections.append(citations_block)

    if fallback_used.get("used"):
        provider = fallback_used.get("provider", "unknown")
        reason = fallback_used.get("reason", "provider_error")
        sections.append(f"\nFallback provider used: {provider} (reason={reason})")

    if disclaimer:
        sections.append(f"\nDisclaimer: {disclaimer}")

    return "\n".join(sections).strip()


add_custom_css()
_require_hardened_auth_config()
_render_title()
_render_sidebar()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

st.markdown("<div class='chat-input-container'>", unsafe_allow_html=True)
prompt = st.chat_input("Ask a Canadian immigration information question.")
st.markdown("</div>", unsafe_allow_html=True)

if prompt and prompt.strip():
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        response_payload = call_chat_api(prompt, st.session_state.thread_id)
    except RuntimeError as exc:
        st.error(str(exc))
    else:
        assistant_text = _format_assistant_message(response_payload)
        with st.chat_message("assistant"):
            st.markdown(assistant_text)

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": assistant_text})
