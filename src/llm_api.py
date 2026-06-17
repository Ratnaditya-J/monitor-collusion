"""Thin provider-agnostic chat client (OpenAI-compatible).

Defaults to OpenRouter (one key reaches the whole ladder: Claude 3.7, gpt-oss,
Qwen, Llama, DeepSeek, etc.). Set OPENROUTER_API_KEY (or OPENAI_API_KEY with a
matching API_BASE in config). Behavioral collusion is black-box, so no GPU is
needed for any rung.
"""
import os, json, time, urllib.request, urllib.error
from . import config as C


def _key():
    k = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not k:
        raise RuntimeError(
            "No API key. Set OPENROUTER_API_KEY (recommended; reaches the whole "
            "ladder) or OPENAI_API_KEY.")
    return k


def chat(model, messages, max_tokens=512, temperature=1.0, retries=4):
    """Return the assistant text for a chat completion. Retries on transient errors."""
    url = C.API_BASE.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, method="POST", headers={
                "Authorization": f"Bearer {_key()}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Ratnaditya-J/monitor-collusion",
                "X-Title": "monitor-collusion"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode())
            return d["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (429, 500, 502, 503, 529):
                time.sleep(2 * (attempt + 1)); continue
            raise RuntimeError(last)
        except Exception as e:  # noqa
            last = str(e); time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"chat failed after {retries} retries: {last}")


def smoke_test(model):
    """Quick one-call check that the key + model work."""
    return chat(model, [{"role": "user", "content": "Reply with the single word OK."}],
                max_tokens=5, temperature=0)
