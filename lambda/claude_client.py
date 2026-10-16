"""Ponte entre a skill Alexa e a API do Claude."""

import os
import re

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
# A Alexa encerra a requisição após ~8 s; deixamos folga para a resposta de voz.
TIMEOUT_SECONDS = float(os.environ.get("CLAUDE_TIMEOUT_SECONDS", "6.5"))
MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "1024"))
EFFORT = os.environ.get("CLAUDE_EFFORT", "low")
# Quantas trocas (pergunta + resposta) ficam na memória da sessão.
MAX_TURNS = int(os.environ.get("CLAUDE_MAX_TURNS", "6"))

SYSTEM_PROMPT = (
    "Você é o Claude, conversando com o usuário por meio de um dispositivo Alexa. "
    "Sua resposta será convertida em fala, então responda em português do Brasil, "
    "em no máximo três frases curtas e naturais. Não use markdown, listas, emojis, "
    "URLs ou blocos de código. Se a pergunta exigir uma resposta longa, dê um resumo "
    "e ofereça detalhar."
)

FALLBACK_SPEECH = "Desculpe, não consegui pensar em uma resposta agora. Pode tentar de novo?"
REFUSAL_SPEECH = "Desculpe, não posso ajudar com esse pedido."

_client = None


def _get_client():
    global _client
    if _client is None:
        # Sem retentativas: não há tempo para elas dentro do limite da Alexa.
        _client = anthropic.Anthropic(timeout=TIMEOUT_SECONDS, max_retries=0)
    return _client


def _to_speech(text):
    """Remove marcações que soariam estranhas quando lidas em voz alta."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"[*_#`>]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def ask_claude(question, history, client=None):
    """Envia a pergunta ao Claude e devolve (fala, histórico atualizado).

    O histórico guarda só o texto de cada turno: os atributos de sessão da Alexa
    são pequenos, e um histórico sem blocos de thinking nunca contém um bloco
    invalidado quando cortamos os turnos mais antigos.
    """
    client = client or _get_client()
    messages = history + [{"role": "user", "content": question}]

    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
            output_config={"effort": EFFORT},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APITimeoutError:
        return "Essa pergunta exigiu mais tempo do que a Alexa permite. Tente algo mais simples.", history
    except anthropic.RateLimitError:
        return "Estou recebendo muitas perguntas agora. Tente de novo em instantes.", history
    except anthropic.AuthenticationError:
        return "A chave da API do Claude não está configurada corretamente.", history
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        return FALLBACK_SPEECH, history

    if response.stop_reason == "refusal":
        return REFUSAL_SPEECH, history

    answer = _to_speech(
        " ".join(block.text for block in response.content if block.type == "text")
    )
    if not answer:
        return FALLBACK_SPEECH, history

    new_history = messages + [{"role": "assistant", "content": answer}]
    return answer, new_history[-MAX_TURNS * 2:]
