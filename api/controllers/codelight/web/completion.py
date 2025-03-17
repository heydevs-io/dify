"""
Codelight Chat API Controller

This module is a modified version of the original completion.py file from the web controllers.
Original source: api/controllers/web/completion.py

Key modifications:
- Customized for Codelight application
- Added support for custom model selection (model_name and model_provider)
- Modified error handling for Codelight-specific cases
- Updated service calls to use Codelight's AppGenerateService

It provides endpoints for processing chat messages with support for different app modes
and streaming responses.
"""

import logging

from flask_restful import reqparse
from werkzeug.exceptions import InternalServerError, NotFound

import services
from controllers.codelight import api
from controllers.codelight.error import (
    AppUnavailableError,
    CompletionRequestError,
    ConversationCompletedError,
    NotChatAppError,
    ProviderModelCurrentlyNotSupportError,
    ProviderNotInitializeError,
    ProviderQuotaExceededError,
)
from controllers.web.error import InvokeRateLimitError as InvokeRateLimitHttpError
from controllers.web.wraps import WebApiResource
from core.app.entities.app_invoke_entities import InvokeFrom
from core.errors.error import ModelCurrentlyNotSupportError, ProviderTokenNotInitError, QuotaExceededError
from core.model_runtime.errors.invoke import InvokeError
from libs import helper
from libs.helper import uuid_value
from models.model import AppMode
from controllers.codelight.services.app_generate_service import AppGenerateService
from services.errors.llm import InvokeRateLimitError

class CodelightChatApi(WebApiResource):
    def post(self, app_model, end_user):
        app_mode = AppMode.value_of(app_model.mode)
        
        if app_mode not in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            raise NotChatAppError()
        
        parser = reqparse.RequestParser()
        parser.add_argument("inputs", type=dict, required=True, location="json")
        parser.add_argument("query", type=str, required=True, location="json")
        parser.add_argument("files", type=list, required=False, location="json")
        parser.add_argument("response_mode", type=str, choices=["blocking", "streaming"], location="json")
        parser.add_argument("conversation_id", type=uuid_value, location="json")
        parser.add_argument("parent_message_id", type=uuid_value, required=False, location="json")
        parser.add_argument("retriever_from", type=str, required=False, default="web_app", location="json")
        parser.add_argument("model_name", type=str, required=False, default="gpt-4o-mini", location="json")
        parser.add_argument("model_provider", type=str, required=False, default="openai", location="json")

        args = parser.parse_args()

        streaming = args["response_mode"] == "streaming"
        args["auto_generate_name"] = False

        try:
            response = AppGenerateService.generate(
                app_model=app_model, user=end_user, args=args, invoke_from=InvokeFrom.WEB_APP, streaming=streaming, model_name=args["model_name"], model_provider=args["model_provider"]
            )

            return helper.compact_generate_response(response)
        except services.errors.conversation.ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")
        except services.errors.conversation.ConversationCompletedError:
            raise ConversationCompletedError()
        except services.errors.app_model_config.AppModelConfigBrokenError:
            logging.exception("App model config broken.")
            raise AppUnavailableError()
        except ProviderTokenNotInitError as ex:
            raise ProviderNotInitializeError(ex.description)
        except QuotaExceededError:
            raise ProviderQuotaExceededError()
        except ModelCurrentlyNotSupportError:
            raise ProviderModelCurrentlyNotSupportError()
        except InvokeRateLimitError as ex:
            raise InvokeRateLimitHttpError(ex.description)
        except InvokeError as e:
            raise CompletionRequestError(e.description)
        except ValueError as e:
            raise e
        except Exception as e:
            logging.exception("internal server error.")
            raise InternalServerError()

api.add_resource(CodelightChatApi, "/chat-messages")
