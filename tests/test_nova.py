"""Offline tests for Nova AI. Run from the project folder:

    python tests/test_nova.py

IMPORTANT: these use a stand-in model to test the UI plumbing (streaming,
history, error handling). They do NOT prove Groq or Gemini work. For that,
chat with them yourself using your real keys.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langchain_core.messages import AIMessageChunk  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from nova.chat_service import classify_error, extract_text  # noqa: E402
from nova.providers import PROVIDERS  # noqa: E402

KEY_VARS = [c["env"] for c in PROVIDERS.values()]


class StandInModel:
    """Streams a fixed answer word by word, or fails with a given error."""

    def __init__(self, text="Hello **world** from the stand-in", fail=None, fail_after=0):
        self.text, self.fail, self.fail_after, self.seen = text, fail, fail_after, None

    def stream(self, messages):
        self.seen = messages
        for i, word in enumerate(self.text.split(" ")):
            if self.fail and i >= self.fail_after:
                raise self.fail
            yield AIMessageChunk(content=word + " ")
        if self.fail and self.fail_after == 0:
            raise self.fail


def fresh_app(env=None):
    for var in KEY_VARS:
        os.environ.pop(var, None)
    os.environ.update(env or {})
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    return at


def send(at, text, provider=None):
    """Same effect as typing in the chat box, via the real state helpers."""
    if provider:
        at.session_state["selected_provider"] = provider
    if at.session_state["current_id"] is None:
        import uuid
        cid = uuid.uuid4().hex[:8]
        convs = dict(at.session_state["conversations"])
        convs[cid] = {"id": cid, "title": text[:30], "messages": [], "error": None}
        at.session_state["conversations"] = convs
        at.session_state["current_id"] = cid
    conv = at.session_state["conversations"][at.session_state["current_id"]]
    conv["messages"].append({"role": "user", "content": text})
    conv["error"] = None
    at.session_state["awaiting"] = True
    at.run()
    return conv


def conv_of(at):
    return at.session_state["conversations"][at.session_state["current_id"]]


results = []


def check(name, condition):
    results.append((name, bool(condition)))
    print(("PASS  " if condition else "FAIL  ") + name)


# 1. startup with NO keys
at = fresh_app()
check("starts with no keys and no exception", not at.exception)
check("landing screen shown (no conversation)", at.session_state["current_id"] is None)

# 2. missing key through the REAL code path (nothing patched)
conv = send(at, "hello", "Groq")
check("missing key: no crash", not at.exception)
check("missing key: error category", conv["error"] and conv["error"]["category"] == "missing_key")
check("missing key: user message kept for retry", conv["messages"][-1]["role"] == "user")
check("missing key: status is 'failing' (but no-key shows as missing)",
      at.session_state["provider_status"]["Groq"]["state"] == "failing")

# 3. streaming success with the stand-in model, then model switch keeps history
at = fresh_app()
model_a = StandInModel("First answer from A")
with patch("nova.chat_service.create_model", return_value=model_a):
    conv = send(at, "question one", "Groq")
check("stream: assistant message saved", conv["messages"][-1]["role"] == "assistant")
check("stream: text joined correctly", conv["messages"][-1]["content"].strip() == "First answer from A")
check("stream: provider recorded on reply", conv["messages"][-1]["provider"] == "Groq")
check("stream: awaiting flag cleared", at.session_state["awaiting"] is False)
check("stream: status verified", at.session_state["provider_status"]["Groq"]["state"] == "ok")

model_b = StandInModel("Second answer from B")
with patch("nova.chat_service.create_model", return_value=model_b):
    conv = send(at, "question two", "Google Gemini")
sent_roles = [type(m).__name__ for m in model_b.seen]
check("switch: new provider got full history",
      sent_roles == ["SystemMessage", "HumanMessage", "AIMessage", "HumanMessage"])
check("switch: reply labelled with new provider", conv["messages"][-1]["provider"] == "Google Gemini")
check("switch: no exception while rendering", not at.exception)

# 4. provider errors are classified, never crash, and don't leak keys
secret = "sk-test-SECRET-1234567890"
cases = [
    ("Error code: 429 - rate limit exceeded", "rate_limit"),
    ("insufficient_quota: You exceeded your current quota", "quota"),
    ("401 Unauthorized: invalid api key " + secret, "auth"),
    ("404 model not found", "model"),
    ("Connection error", "network"),
    ("[Errno -2] Name or service not known", "network"),
    ("something odd", "other"),
]
os.environ["OPENAI_API_KEY"] = secret
for text, expected in cases:
    err = classify_error(Exception(text), "OpenAI")
    check(f"classify '{text[:28]}' -> {expected}", err.category == expected)
    check("  details never contain the API key", secret not in err.details)
os.environ.pop("OPENAI_API_KEY")

at = fresh_app()
with patch("nova.chat_service.create_model",
           return_value=StandInModel("partial text here", fail=Exception("429 rate limit"), fail_after=2)):
    conv = send(at, "will fail midway", "Mistral")
check("mid-stream failure: no crash", not at.exception)
check("mid-stream failure: partial text NOT saved as an answer", conv["messages"][-1]["role"] == "user")
check("mid-stream failure: status shows failing/rate_limit",
      at.session_state["provider_status"]["Mistral"] == {"state": "failing", "category": "rate_limit"})

# 5. REAL provider call with a dummy key: must fail cleanly (no network/valid key here)
at = fresh_app({"GROQ_API_KEY": "gsk_dummy_key_for_error_path_test"})
conv = send(at, "hi", "Groq")
os.environ.pop("GROQ_API_KEY")
check("real call, dummy key: app survives", not at.exception)
check("real call, dummy key: friendly error stored", conv["error"] is not None)
check("real call, dummy key: key not leaked", "gsk_dummy_key" not in conv["error"]["details"])

# 6. chat history actions
at = fresh_app()
with patch("nova.chat_service.create_model", return_value=StandInModel("ok")):
    send(at, "chat one", "Groq")
    first_id = at.session_state["current_id"]
    # New chat button is in the sidebar
    [b for b in at.sidebar.button if "New chat" in b.label][0].click().run()
check("new chat: returns to landing", at.session_state["current_id"] is None)
check("new chat: old conversation kept", first_id in at.session_state["conversations"])
at.button(key=f"open_{first_id}").click().run()
check("history: reopen conversation", at.session_state["current_id"] == first_id)
at.button(key=f"del_{first_id}").click().run()
check("history: delete conversation", first_id not in at.session_state["conversations"]
      and at.session_state["current_id"] is None)

# 7. content-block parsing (Gemini-style lists)
check("extract_text: string", extract_text("abc") == "abc")
check("extract_text: blocks, ignores non-text",
      extract_text([{"type": "thinking", "thinking": "x"}, {"type": "text", "text": "Hi"}]) == "Hi")

# 8. provider table untouched
check("model names unchanged",
      PROVIDERS["Groq"]["model"] == "openai/gpt-oss-20b"
      and PROVIDERS["Google Gemini"]["model"] == "gemini-3.8-flash"
      and PROVIDERS["OpenAI"]["model"] == "gpt-4.1-mini"
      and PROVIDERS["Mistral"]["model"] == "mistral-small-latest")
check("env var names unchanged",
      [c["env"] for c in PROVIDERS.values()] ==
      ["GROQ_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "MISTRAL_API_KEY"])

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
