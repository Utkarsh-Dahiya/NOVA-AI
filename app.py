"""NOVA AI — Beyond Conversation.

This file is the thin "glue" between the interface and the backend:

    nova/ui/components.py   draws things (HTML, CSS, widgets)
    nova/state.py           remembers things (chats, provider status)
    nova/chat_service.py    talks to the models (streaming, errors)
    nova/providers.py       knows the providers (env vars, model names)

Run with:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Nova AI | Beyond Conversation",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="auto",
)

from nova.chat_service import classify_error, stream_response  # noqa: E402
from nova.providers import PROVIDERS  # noqa: E402
from nova.state import (  # noqa: E402
    current_conversation, init_state, record_failure, record_success,
    retry_last, submit_message,
)
from nova.ui.components import (  # noqa: E402
    ASSISTANT_AVATAR, THINKING_HTML, chat_header, error_card, inject_css,
    landing_screen, render_message, render_sidebar,
)


def answer_last_message(conversation, header_slot):
    """Stream the assistant's reply. Returns a NovaError dict or None."""
    provider = st.session_state.selected_provider
    model_name = PROVIDERS[provider]["model"]
    header_slot.markdown(chat_header(provider, busy=True), unsafe_allow_html=True)

    error = None
    answer = ""
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        slot = st.empty()
        slot.markdown(THINKING_HTML, unsafe_allow_html=True)  # shown until the first chunk
        try:
            for piece in stream_response(provider, conversation["messages"]):
                answer += piece
                slot.markdown(answer + " ▍")
            slot.markdown(answer)
        except Exception as exc:  # any provider failure becomes a friendly card
            slot.empty()
            error = classify_error(exc, provider).to_dict()

    if error:
        conversation["error"] = error
        record_failure(provider, error["category"])
    else:
        conversation["messages"].append(
            {"role": "assistant", "content": answer, "provider": provider, "model": model_name}
        )
        record_success(provider)
    st.session_state.awaiting = False
    return error


def chat_screen(conversation):
    provider = st.session_state.selected_provider
    header_slot = st.empty()
    header_slot.markdown(chat_header(provider), unsafe_allow_html=True)

    for message in conversation["messages"]:
        render_message(message)

    if st.session_state.awaiting and conversation["messages"][-1]["role"] == "user":
        # Streamlit keeps the previous screen's leftover elements (e.g. the
        # landing composer) visible, dimmed, until the run ends. Streaming
        # can take seconds, so overwrite those leftovers with empty slots.
        for _ in range(8):
            st.empty()
        answer_last_message(conversation, header_slot)
        st.rerun()  # redraw from stored state (copy buttons, sidebar status, error card)

    if conversation["error"]:
        st.markdown(error_card(conversation["error"]), unsafe_allow_html=True)
        st.button(
            f"↻ Retry with {provider}", on_click=retry_last,
            help="Your message is kept. Switch model in the sidebar first if you like.",
        )

    prompt = st.chat_input("Message Nova AI…")
    if prompt:
        submit_message(prompt)
        st.rerun()


def main():
    init_state()
    inject_css()
    render_sidebar()

    conversation = current_conversation()
    if conversation is None:
        text = landing_screen()
        if text:
            submit_message(text)
            st.rerun()  # switches to conversation mode
    else:
        chat_screen(conversation)


main()
