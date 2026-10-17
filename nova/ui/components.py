"""Everything that DRAWS the interface. Nothing here calls an AI model.

Functions return HTML strings or draw Streamlit widgets. The only
decisions made here are visual ones; app.py decides what happens next.
"""

import html
from pathlib import Path

import streamlit as st

from nova.providers import PROVIDERS
from nova.state import (
    delete_conversation, new_chat, open_conversation,
    provider_status, sync_provider,
)

CSS_PATH = Path(__file__).parent / "styles.css"

USER_AVATAR = ":material/person:"
ASSISTANT_AVATAR = ":material/auto_awesome:"

# (button label, text that is placed into the composer)
PROMPT_CARDS = [
    ("Explain Python decorators",
     "Explain Python decorators with a simple example."),
    ("AI vs machine learning vs deep learning",
     "Explain the difference between AI, machine learning, and deep learning."),
    ("Help me debug my code",
     "I'm going to paste some code that has a bug. Walk me through how to find and fix it, step by step.\n\n"),
    ("Plan a 4-week study schedule",
     "Help me build a 4-week study plan for learning data structures, with weekly goals."),
]

STATE_COLOR = {"ok": "green", "untested": "blue", "failing": "red", "missing": "gray"}
STATE_SENTENCE = {
    "ok": "Verified: the last real request succeeded.",
    "untested": "API key found, but no request has been made yet, so availability is unknown.",
    "failing": "The last real request failed. Retrying may work, or pick another model.",
    "missing": "No API key in the environment. Add it to your .env file.",
}


# ---------------------------------------------------------------- styling

def inject_css():
    css = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def orb_html(mini=False, busy=False):
    """The animated core. Pure HTML + CSS (see styles.css, section 3)."""
    classes = "nova-orb" + (" mini" if mini else "") + (" busy" if busy else "")
    return (
        f'<div class="{classes}" role="img" aria-label="Nova AI core">'
        '<div class="glow"></div><div class="ring r3"></div>'
        '<div class="ring r2"></div><div class="ring r1"></div>'
        '<div class="orbit"><i></i></div><div class="orbit o2"><i></i></div>'
        '<div class="core"></div></div>'
    )


# ---------------------------------------------------------- model selector

def _label(provider_name):
    state, word = provider_status(provider_name)
    return f":{STATE_COLOR[state]}[●] {provider_name} · {word}"


def provider_selector(key, horizontal=False):
    """A radio group (keyboard + screen-reader friendly). The coloured dot
    is backed by a text word, so colour is never the only signal."""
    st.session_state[key] = st.session_state.selected_provider
    labels = {name: _label(name) for name in PROVIDERS}  # computed once per run
    st.radio(
        "Model", list(PROVIDERS), key=key, horizontal=horizontal,
        format_func=labels.get, label_visibility="collapsed",
        on_change=sync_provider, args=(key,),
    )


def status_card(provider_name):
    state, _ = provider_status(provider_name)
    config = PROVIDERS[provider_name]
    detail = html.escape(STATE_SENTENCE[state])
    return (
        '<div class="nova-status-card">'
        f'<span class="nova-dot {state}"></span> <span class="state">{html.escape(provider_name)}</span><br>'
        f'Model <code>{html.escape(config["model"])}</code><br>{detail}</div>'
    )


# ----------------------------------------------------------------- sidebar

def render_sidebar():
    ss = st.session_state
    with st.sidebar:
        st.markdown(
            f'<div class="nova-side-brand">{orb_html(mini=True)}<span class="brand">NOVA AI</span></div>',
            unsafe_allow_html=True,
        )
        st.button("＋ New chat", type="primary", use_container_width=True, on_click=new_chat)

        st.markdown('<div class="nova-label">Model</div>', unsafe_allow_html=True)
        provider_selector("prov_side")
        st.markdown(status_card(ss.selected_provider), unsafe_allow_html=True)

        st.markdown('<div class="nova-label">Conversations</div>', unsafe_allow_html=True)
        with st.container(key="history"):
            if not ss.conversations:
                st.caption("Nothing yet. Your chats will appear here.")
            for conv_id, conv in reversed(list(ss.conversations.items())):
                is_current = conv_id == ss.current_id
                left, right = st.columns([5, 1], vertical_alignment="center")
                left.button(
                    ("● " if is_current else "") + conv["title"],
                    key=f"open_{conv_id}", use_container_width=True,
                    on_click=open_conversation, args=(conv_id,),
                )
                right.button(
                    "", icon=":material/close:", key=f"del_{conv_id}",
                    help="Delete this conversation",
                    on_click=delete_conversation, args=(conv_id,),
                )
        st.caption("Chats live in this browser session only.")


# ----------------------------------------------------------------- landing

def landing_screen():
    """Draws the first screen. Returns the submitted text, or None."""
    st.markdown(
        '<div class="nova-hero">' + orb_html() +
        '<div class="nova-wordmark">NOVA AI</div>'
        '<div class="nova-headline">Beyond Conversation.</div>'
        '<div class="nova-sub">One workspace, four minds. Ask, build and explore '
        'with the model that fits the moment.</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="nova-label">Model</div>', unsafe_allow_html=True)
    provider_selector("prov_main", horizontal=True)

    submitted_text = None
    with st.form("landing_form", clear_on_submit=True):
        text = st.text_area(
            "Message Nova AI", key="composer", height=110,
            placeholder="Ask anything, or choose a starting point below…",
            label_visibility="collapsed",
        )
        hint, send = st.columns([3, 1], vertical_alignment="center")
        hint.caption("Ctrl + Enter to send")
        if send.form_submit_button("Send ↑", use_container_width=True):
            if text.strip():
                submitted_text = text.strip()

    st.markdown('<div class="nova-label">Start with</div>', unsafe_allow_html=True)
    with st.container(key="prompt_cards"):
        columns = st.columns(2)
        for i, (label, prompt) in enumerate(PROMPT_CARDS):
            columns[i % 2].button(
                label, key=f"card_{i}", use_container_width=True,
                on_click=_fill_composer, args=(prompt,),
            )
    return submitted_text


def _fill_composer(prompt):
    """Prompt cards fill the input. They do not send anything."""
    st.session_state.composer = prompt


# -------------------------------------------------------------------- chat

def chat_header(provider_name, busy=False):
    state, _ = provider_status(provider_name)
    model = html.escape(PROVIDERS[provider_name]["model"])
    return (
        f'<div class="nova-topbar">{orb_html(mini=True, busy=busy)}'
        '<span class="brand">NOVA AI</span>'
        f'<span class="nova-chip" title="Current provider"><span class="nova-dot {state}"></span>'
        f'<b>{html.escape(provider_name)}</b> · {model}</span></div>'
    )


THINKING_HTML = '<div class="nova-thinking" role="status"><i></i><i></i><i></i>&nbsp;Thinking…</div>'


def render_message(message):
    role = message["role"]
    with st.chat_message(role, avatar=USER_AVATAR if role == "user" else ASSISTANT_AVATAR):
        st.markdown(message["content"])
        if role == "assistant":
            meta, copy = st.columns([5, 2], vertical_alignment="center")
            if message.get("provider"):
                meta.markdown(
                    f'<div class="nova-meta">{html.escape(message["provider"])} · '
                    f'{html.escape(message.get("model", ""))}</div>',
                    unsafe_allow_html=True,
                )
            with copy.popover("Copy", icon=":material/content_copy:", use_container_width=True):
                st.caption("Use the copy icon at the top right of the box.")
                st.code(message["content"], language=None, wrap_lines=True)


def error_card(error):
    return (
        '<div class="nova-error" role="alert">'
        f'<h4>{html.escape(error["title"])}</h4><p>{html.escape(error["hint"])}</p>'
        f'<small>Details: {html.escape(error["details"])}</small></div>'
    )
