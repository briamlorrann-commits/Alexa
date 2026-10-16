import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))

import claude_client  # noqa: E402


class FakeClient:
    def __init__(self, response):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self._response = response

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def _response(text, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
    )


def test_returns_speech_and_appends_text_only_history():
    client = FakeClient(_response("**Canberra** é a capital."))
    answer, history = claude_client.ask_claude("qual a capital da Austrália", [], client=client)

    assert answer == "Canberra é a capital."
    assert history == [
        {"role": "user", "content": "qual a capital da Austrália"},
        {"role": "assistant", "content": "Canberra é a capital."},
    ]
    call = client.calls[0]
    assert call["fallbacks"] == "default"
    assert call["betas"] == ["server-side-fallback-2026-07-01"]


def test_refusal_keeps_history_unchanged():
    client = FakeClient(_response("", stop_reason="refusal"))
    previous = [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "olá"}]
    answer, history = claude_client.ask_claude("algo", previous, client=client)

    assert answer == claude_client.REFUSAL_SPEECH
    assert history == previous


def test_history_is_trimmed_to_max_turns():
    client = FakeClient(_response("ok"))
    history = []
    for i in range(claude_client.MAX_TURNS + 3):
        _, history = claude_client.ask_claude(f"pergunta {i}", history, client=client)

    assert len(history) == claude_client.MAX_TURNS * 2
    assert history[0]["role"] == "user"
