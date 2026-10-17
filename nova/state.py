"""Session-state helpers: conversations, provider status, flags.

Everything lives in st.session_state, so it resets when the browser tab
is refreshed (same as the original app). Nothing is written to disk.

st.session_state keys:
  conversations     dict  id -> {"id", "title", "messages", "error"}
  current_id        str|None   which conversation is open (None = landing)
  selected_provider str        "Groq", "Google Gemini", ...
  provider_status   dict  provider -> {"state": "ok"|"failing", "category": str}
  awaiting          bool  True when the last user message needs an answer
"""

import uuid

import streamlit as st

from nova.providers import PROVIDERS, has_api_key


def init_state():
    ss = st.session_state
    ss.setdefault("conversations", {})
    ss.setdefault("current_id", None)
    ss.setdefault("selected_provider", "Groq")
    ss.setdefault("provider_status", {})
    ss.setdefault("awaiting", False)


# ---------- conversations ----------

def current_conversation():
    ss = st.session_state
    return ss.conversations.get(ss.current_id)


def new_chat():
    """Go back to the landing screen. The conversation is only created
    when the first message is sent, so empty chats never pile up."""
    st.session_state.current_id = None
    st.session_state.awaiting = False


def open_conversation(conversation_id):
    st.session_state.current_id = conversation_id
    st.session_state.awaiting = False


def delete_conversation(conversation_id):
    ss = st.session_state
    ss.conversations.pop(conversation_id, None)
    if ss.current_id == conversation_id:
        new_chat()


def make_title(text):
    text = " ".join(text.split())
    return text if len(text) <= 38 else text[:37].rstrip() + "…"


def submit_message(text):
    """Add the user's message and flag that an answer is needed."""
    ss = st.session_state
    conversation = current_conversation()
    if conversation is None:
        conversation_id = uuid.uuid4().hex[:8]
        conversation = {"id": conversation_id, "title": make_title(text),
                        "messages": [], "error": None}
        ss.conversations[conversation_id] = conversation
        ss.current_id = conversation_id
    conversation["messages"].append({"role": "user", "content": text})
    conversation["error"] = None
    ss.awaiting = True


def retry_last():
    conversation = current_conversation()
    if conversation:
        conversation["error"] = None
        st.session_state.awaiting = True


# ---------- provider status ----------

def record_success(provider_name):
    st.session_state.provider_status[provider_name] = {"state": "ok", "category": ""}


def record_failure(provider_name, category):
    st.session_state.provider_status[provider_name] = {"state": "failing", "category": category}


FAILURE_WORDS = {
    "quota": "no credits",
    "rate_limit": "rate limited",
    "auth": "key rejected",
    "model": "model unavailable",
    "network": "unreachable",
    "empty": "empty reply",
    "missing_key": "no key",
    "other": "last request failed",
}


def provider_status(provider_name):
    """Return (state, short_word). Deliberately honest:
       missing  - no API key in the environment
       untested - a key exists, but no real request has been made yet
       ok       - the last real request succeeded
       failing  - the last real request failed (word says why)"""
    if not has_api_key(provider_name):
        return "missing", "no key"
    record = st.session_state.provider_status.get(provider_name)
    if record is None:
        return "untested", "key found, untested"
    if record["state"] == "ok":
        return "ok", "verified"
    return "failing", FAILURE_WORDS.get(record["category"], "failed")


def sync_provider(source_key):
    """Two selectors exist (landing page + sidebar). Keep them in sync."""
    ss = st.session_state
    choice = ss[source_key]
    ss.selected_provider = choice
    for key in ("prov_side", "prov_main"):
        ss[key] = choice
