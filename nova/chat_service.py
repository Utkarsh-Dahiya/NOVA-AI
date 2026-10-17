"""Talking to the models: build messages, stream replies, classify errors.

No Streamlit code lives here either.
"""

from dataclasses import dataclass, asdict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from nova.providers import PROVIDERS, create_model, redact_secrets

SYSTEM_PROMPT = """
You are Nova, a helpful AI assistant.

Your responsibilities:
- Give clear and accurate answers.
- Explain technical concepts in beginner-friendly language.
- Use headings and lists when they improve readability.
- Be honest when you are uncertain.
- Never claim to have searched the live web unless a search tool was actually used.
"""


def build_messages(conversation):
    """Convert our simple {"role", "content"} dicts to LangChain messages."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for message in conversation:
        if message["role"] == "user":
            messages.append(HumanMessage(content=message["content"]))
        elif message["role"] == "assistant":
            messages.append(AIMessage(content=message["content"]))
    return messages


def extract_text(content):
    """Providers return either a string or a list of content blocks.
    Keep only the visible text (same idea as the original app)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content) if content else ""


class EmptyResponse(Exception):
    """The provider answered, but with no text."""


def stream_response(provider_name, conversation):
    """Yield the answer piece by piece. Raises on any failure, and the
    caller turns the exception into a friendly message."""
    model = create_model(provider_name)
    received_text = False

    # .stream() is real streaming where the provider supports it. LangChain
    # falls back to one big chunk otherwise, so this is always safe.
    for chunk in model.stream(build_messages(conversation)):
        text = extract_text(chunk.content)
        if text:
            received_text = True
            yield text

    if not received_text:
        raise EmptyResponse("The model returned an empty response.")


@dataclass
class NovaError:
    category: str   # quota | rate_limit | auth | model | network | missing_key | empty | other
    title: str
    hint: str
    details: str

    def to_dict(self):
        return asdict(self)


def classify_error(error, provider_name):
    """Turn any exception into a short, useful message. Branches follow the
    original app (quota, 429, 401) plus a few more common cases."""
    raw = redact_secrets(str(error))
    text = raw.lower()
    details = raw[:400]
    env_name = PROVIDERS[provider_name]["env"]
    model_name = PROVIDERS[provider_name]["model"]

    if isinstance(error, ValueError) and "is missing" in text:
        return NovaError("missing_key", f"{provider_name} is not configured",
                         f"Add {env_name} to your .env file and restart the app.", details)
    if isinstance(error, EmptyResponse):
        return NovaError("empty", f"{provider_name} returned an empty answer",
                         "Try again, or rephrase your message.", details)
    if "insufficient_quota" in text or "exceeded your current quota" in text or "credit" in text:
        return NovaError("quota", f"{provider_name} has no credits left",
                         "The account appears to be out of quota. Add credits, or switch model.", details)
    if "429" in text or "rate limit" in text or "rate_limit" in text or "resource_exhausted" in text:
        return NovaError("rate_limit", f"{provider_name} is rate-limiting requests",
                         "Wait a little, then retry. You can also switch model.", details)
    if "401" in text or "403" in text or "unauthorized" in text or "api key" in text or "permission" in text:
        return NovaError("auth", f"{provider_name} rejected the API key",
                         f"Check {env_name} and the permissions on that key.", details)
    if "404" in text or "not found" in text or "does not exist" in text or "not supported" in text:
        return NovaError("model", f"{provider_name} could not use model '{model_name}'",
                         "The model name may be unavailable to your account. "
                         "Nova never changes model names for you; edit nova/providers.py.", details)
    if any(word in text for word in (
            "connect", "timeout", "timed out", "network", "name or service",
            "getaddrinfo", "errno", "unreachable", "ssl")):
        return NovaError("network", f"Could not reach {provider_name}",
                         "Check your internet connection and try again.", details)
    return NovaError("other", f"{provider_name} could not answer",
                     "Retry, or switch to another model.", details)
