import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI


# --------------------------------------------------
# 1. APPLICATION CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

st.set_page_config(
    page_title="Nova AI | Multi-Model Chatbot",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# 2. MODEL CONFIGURATION
# --------------------------------------------------

PROVIDERS = {
    "Groq": {
        "env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-20b",
        "class": ChatGroq,
        "description": "Fast AI inference powered by Groq.",
    },
    "Google Gemini": {
        "env": "GOOGLE_API_KEY",
        "model": "gemini-3.8-flash",
        "class": ChatGoogleGenerativeAI,
        "description": "Google's Gemini AI model.",
    },
    "OpenAI": {
        "env": "OPENAI_API_KEY",
        "model": "gpt-4.1-mini",
        "class": ChatOpenAI,
        "description": "OpenAI's language models.",
    },
    "Mistral": {
        "env": "MISTRAL_API_KEY",
        "model": "mistral-small-latest",
        "class": ChatMistralAI,
        "description": "Mistral AI language models.",
    },
}

SYSTEM_PROMPT = """
You are Nova, a helpful AI assistant.

Your responsibilities:
- Give clear and accurate answers.
- Explain technical concepts in beginner-friendly language.
- Use headings and lists when they improve readability.
- Be honest when you are uncertain.
- Never claim to have searched the live web unless a search tool was actually used.
"""


# --------------------------------------------------
# 3. SESSION STATE
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "selected_provider" not in st.session_state:
    st.session_state.selected_provider = "Groq"

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# --------------------------------------------------
# 4. MODEL CREATION
# --------------------------------------------------

def create_model(provider_name):
    """Initialize the selected language model."""

    config = PROVIDERS[provider_name]
    api_key = os.getenv(config["env"])

    if not api_key:
        raise ValueError(
            f"{config['env']} is missing. "
            "Add the required API key to your .env file."
        )

    return config["class"](
        model=config["model"],
        temperature=0.7,
        api_key=api_key,
    )


# --------------------------------------------------
# 5. CHAT RESPONSE
# --------------------------------------------------

def generate_response(provider_name, conversation):
    """Generate an answer using the selected provider."""

    model = create_model(provider_name)

    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    for message in conversation:
        if message["role"] == "user":
            messages.append(HumanMessage(content=message["content"]))

        elif message["role"] == "assistant":
            from langchain_core.messages import AIMessage

            messages.append(AIMessage(content=message["content"]))

    response = model.invoke(messages)

    answer = response.content

    if isinstance(answer, str):
        return answer

    if isinstance(answer, list):
        text_parts = []

        for block in answer:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)

        return "\n".join(text_parts) or str(answer)

    return str(answer)


# --------------------------------------------------
# 6. SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.markdown("# ✦ Nova AI")
    st.caption("Your multi-model AI workspace")

    st.divider()

    st.markdown("### Choose your model")

    provider_names = list(PROVIDERS.keys())

    selected_provider = st.selectbox(
        "AI Provider",
        provider_names,
        index=provider_names.index(
            st.session_state.selected_provider
        ),
        key="provider_selector",
    )

    if selected_provider != st.session_state.selected_provider:
        st.session_state.selected_provider = selected_provider
        st.rerun()

    config = PROVIDERS[selected_provider]

    st.caption(f"Model: `{config['model']}`")
    st.caption(config["description"])

    if os.getenv(config["env"]):
        st.success("API key configured", icon="✅")
    else:
        st.warning("API key not configured", icon="⚠️")

    st.divider()

    if st.button("＋ New chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()

    st.markdown("### About")

    st.write(
        "Nova AI brings multiple language-model providers "
        "together in one conversational interface."
    )

    st.caption("Built with Python, LangChain and Streamlit.")


# --------------------------------------------------
# 7. MAIN CHAT AREA
# --------------------------------------------------

st.markdown("# ✦ Nova AI")
st.markdown(
    "### One workspace. Multiple AI models."
)

st.caption(
    f"Currently using **{selected_provider}** · "
    f"`{PROVIDERS[selected_provider]['model']}`"
)

st.divider()


# Welcome screen
if not st.session_state.messages:

    st.markdown("## What can I help you with?")

    st.write(
        "Ask a question, learn something new, "
        "or work through a coding problem."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "💻 Explain a Python concept",
            use_container_width=True,
        ):
            st.session_state.pending_prompt = (
                "Explain Python decorators with a simple example."
            )
            st.rerun()

    with col2:
        if st.button(
            "🧠 Learn about AI",
            use_container_width=True,
        ):
            st.session_state.pending_prompt = (
                "Explain the difference between AI, "
                "machine learning, and deep learning."
            )
            st.rerun()


# Display conversation history
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --------------------------------------------------
# 8. USER INPUT AND RESPONSE
# --------------------------------------------------

prompt = st.chat_input("Message Nova AI...")

if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None


if prompt:

    # Display and save the user's message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate the assistant's response
    with st.chat_message("assistant"):

        with st.spinner(f"{selected_provider} is thinking..."):

            try:
                answer = generate_response(
                    selected_provider,
                    st.session_state.messages,
                )

                st.markdown(answer)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

            except Exception as error:

                st.error(
                    f"Unable to generate a response using "
                    f"{selected_provider}."
                )

                error_text = str(error)

                if "insufficient_quota" in error_text.lower():
                    st.warning(
                        "Your API account may have insufficient credits."
                    )

                elif "429" in error_text or "rate limit" in error_text.lower():
                    st.warning(
                        "The provider may be rate-limiting requests. "
                        "Wait a little before trying again."
                    )

                elif "401" in error_text or "unauthorized" in error_text.lower():
                    st.warning(
                        "Check your API key and provider authentication."
                    )

                else:
                    st.caption(f"Technical details: {error}")

                # Remove the unanswered user message so a failed
                # request doesn't become part of the chat history.
                st.session_state.messages.pop()