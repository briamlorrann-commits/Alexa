"""Skill Alexa "Assistente Claude": converse com o Claude pelo seu Echo."""

import logging

from ask_sdk_core.dispatch_components import AbstractExceptionHandler, AbstractRequestHandler
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.utils import get_slot_value, is_intent_name, is_request_type
from ask_sdk_model.services.directive import Header, SendDirectiveRequest, SpeakDirective

from claude_client import ask_claude

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HISTORY_KEY = "history"
REPROMPT = "Quer perguntar mais alguma coisa?"


def _send_progressive_response(handler_input, speech):
    """Fala algo enquanto o Claude pensa, para a espera não parecer silêncio."""
    try:
        request_id = handler_input.request_envelope.request.request_id
        directive = SendDirectiveRequest(
            header=Header(request_id=request_id),
            directive=SpeakDirective(speech=speech),
        )
        handler_input.service_client_factory.get_directive_service().enqueue(directive)
    except Exception:  # resposta progressiva é opcional
        logger.warning("Falha ao enviar resposta progressiva", exc_info=True)


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speech = "Olá! Aqui é o Claude. O que você quer saber?"
        return handler_input.response_builder.speak(speech).ask(speech).response


class ChatIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("ChatIntent")(handler_input)

    def handle(self, handler_input):
        question = get_slot_value(handler_input, "query")
        if not question:
            speech = "Não entendi a pergunta. Pode repetir?"
            return handler_input.response_builder.speak(speech).ask(speech).response

        _send_progressive_response(handler_input, "Deixa eu pensar.")

        session = handler_input.attributes_manager.session_attributes
        answer, session[HISTORY_KEY] = ask_claude(question, session.get(HISTORY_KEY, []))

        return handler_input.response_builder.speak(answer).ask(REPROMPT).response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speech = (
            "Você pode me perguntar qualquer coisa, por exemplo: "
            "pergunte como funciona a fotossíntese. Para sair, diga parar."
        )
        return handler_input.response_builder.speak(speech).ask(speech).response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or is_intent_name(
            "AMAZON.StopIntent"
        )(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.speak("Até mais!").set_should_end_session(True).response


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        speech = "Comece sua frase com pergunte ou me diga, por exemplo: pergunte qual a capital da Austrália."
        return handler_input.response_builder.speak(speech).ask(speech).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        speech = "Desculpe, algo deu errado. Pode tentar de novo?"
        return handler_input.response_builder.speak(speech).ask(speech).response


sb = CustomSkillBuilder(api_client=DefaultApiClient())
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(ChatIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
