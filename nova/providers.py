"""Provider configuration and model creation.

This file is the single source of truth for the four AI providers.
It has NO Streamlit code, so it could be reused by a CLI or API later.
The provider names, env-var names and model names are exactly the ones
from the original app.py.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI

# .env sits next to app.py, one folder above this package.
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

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


def has_api_key(provider_name):
    """True if the provider's env variable is set. This does NOT mean
    the provider actually works (quota, rate limits, bad key...)."""
    return bool(os.getenv(PROVIDERS[provider_name]["env"]))


def create_model(provider_name):
    """Initialize the selected language model (same logic as before)."""
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


def redact_secrets(text):
    """Remove any configured API key from a piece of text, so an error
    message can never leak a secret onto the screen."""
    for config in PROVIDERS.values():
        key = os.getenv(config["env"])
        if key and len(key) > 6:
            text = text.replace(key, "[redacted]")
    return text
