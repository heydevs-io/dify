import logging

from flask_restful import fields, marshal_with, reqparse  # type: ignore
from flask_restful.inputs import int_range  # type: ignore
from werkzeug.exceptions import InternalServerError, NotFound

import services
from controllers.web import api
from controllers.web.error import (
    AppMoreLikeThisDisabledError,
    AppSuggestedQuestionsAfterAnswerDisabledError,
    CompletionRequestError,
    NotChatAppError,
    NotCompletionAppError,
    ProviderModelCurrentlyNotSupportError,
    ProviderNotInitializeError,
    ProviderQuotaExceededError,
)
from controllers.web.wraps import WebApiResource
from core.app.entities.app_invoke_entities import InvokeFrom
from core.errors.error import ModelCurrentlyNotSupportError, ProviderTokenNotInitError, QuotaExceededError
from core.model_runtime.errors.invoke import InvokeError
from fields.conversation_fields import message_file_fields
from fields.message_fields import agent_thought_fields, feedback_fields, retriever_resource_fields
from fields.raws import FilesContainedField
from libs import helper
from libs.helper import TimestampField, uuid_value
from models.model import AppMode
from services.app_generate_service import AppGenerateService
from services.errors.app import MoreLikeThisDisabledError
from services.errors.conversation import ConversationNotExistsError
from services.errors.message import MessageNotExistsError, SuggestedQuestionsAfterAnswerDisabledError
from services.message_service import MessageService


class MessageListApi(WebApiResource):
    message_fields = {
        "id": fields.String,
        "conversation_id": fields.String,
        "parent_message_id": fields.String,
        "inputs": FilesContainedField,
        "query": fields.String,
        "answer": fields.String(attribute="re_sign_file_url_answer"),
        "message_files": fields.List(fields.Nested(message_file_fields)),
        "feedback": fields.Nested(feedback_fields, attribute="user_feedback", allow_null=True),
        "retriever_resources": fields.List(fields.Nested(retriever_resource_fields)),
        "created_at": TimestampField,
        "agent_thoughts": fields.List(fields.Nested(agent_thought_fields)),
        "status": fields.String,
        "error": fields.String,
    }

    message_infinite_scroll_pagination_fields = {
        "limit": fields.Integer,
        "has_more": fields.Boolean,
        "data": fields.List(fields.Nested(message_fields)),
    }

    @marshal_with(message_infinite_scroll_pagination_fields)
    def get(self, app_model, end_user):
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode not in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            raise NotChatAppError()

        parser = reqparse.RequestParser()
        parser.add_argument("conversation_id", required=True, type=uuid_value, location="args")
        parser.add_argument("first_id", type=uuid_value, location="args")
        parser.add_argument("limit", type=int_range(1, 100), required=False, default=20, location="args")
        args = parser.parse_args()

        try:
            return MessageService.pagination_by_first_id(
                app_model, end_user, args["conversation_id"], args["first_id"], args["limit"]
            )
        except services.errors.conversation.ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")
        except services.errors.message.FirstMessageNotExistsError:
            raise NotFound("First Message Not Exists.")


class MessageFeedbackApi(WebApiResource):
    def post(self, app_model, end_user, message_id):
        message_id = str(message_id)

        parser = reqparse.RequestParser()
        parser.add_argument("rating", type=str, choices=["like", "dislike", None], location="json")
        parser.add_argument("content", type=str, location="json", default=None)
        args = parser.parse_args()

        try:
            MessageService.create_feedback(
                app_model=app_model,
                message_id=message_id,
                user=end_user,
                rating=args.get("rating"),
                content=args.get("content"),
            )
        except services.errors.message.MessageNotExistsError:
            raise NotFound("Message Not Exists.")

        return {"result": "success"}


class MessageMoreLikeThisApi(WebApiResource):
    def get(self, app_model, end_user, message_id):
        if app_model.mode != "completion":
            raise NotCompletionAppError()

        message_id = str(message_id)

        parser = reqparse.RequestParser()
        parser.add_argument(
            "response_mode", type=str, required=True, choices=["blocking", "streaming"], location="args"
        )
        args = parser.parse_args()

        streaming = args["response_mode"] == "streaming"

        try:
            response = AppGenerateService.generate_more_like_this(
                app_model=app_model,
                user=end_user,
                message_id=message_id,
                invoke_from=InvokeFrom.WEB_APP,
                streaming=streaming,
            )

            return helper.compact_generate_response(response)
        except MessageNotExistsError:
            raise NotFound("Message Not Exists.")
        except MoreLikeThisDisabledError:
            raise AppMoreLikeThisDisabledError()
        except ProviderTokenNotInitError as ex:
            raise ProviderNotInitializeError(ex.description)
        except QuotaExceededError:
            raise ProviderQuotaExceededError()
        except ModelCurrentlyNotSupportError:
            raise ProviderModelCurrentlyNotSupportError()
        except InvokeError as e:
            raise CompletionRequestError(e.description)
        except ValueError as e:
            raise e
        except Exception:
            logging.exception("internal server error.")
            raise InternalServerError()


class MessageSuggestedQuestionApi(WebApiResource):
    def get(self, app_model, end_user, message_id):
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode not in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            raise NotCompletionAppError()

        message_id = str(message_id)

        try:
            questions = MessageService.get_suggested_questions_after_answer(
                app_model=app_model, user=end_user, message_id=message_id, invoke_from=InvokeFrom.WEB_APP
            )
        except MessageNotExistsError:
            raise NotFound("Message not found")
        except ConversationNotExistsError:
            raise NotFound("Conversation not found")
        except SuggestedQuestionsAfterAnswerDisabledError:
            raise AppSuggestedQuestionsAfterAnswerDisabledError()
        except ProviderTokenNotInitError as ex:
            raise ProviderNotInitializeError(ex.description)
        except QuotaExceededError:
            raise ProviderQuotaExceededError()
        except ModelCurrentlyNotSupportError:
            raise ProviderModelCurrentlyNotSupportError()
        except InvokeError as e:
            raise CompletionRequestError(e.description)
        except Exception:
            logging.exception("internal server error.")
            raise InternalServerError()

        return {"data": questions}

#------------------------------------------------------------------------------
# CODELIGHT_CUSTOMIZATION: Added standard pagination API endpoint
# Version: 1.0.0
# Author: Codelight - Lau Truong
# Date: 2025-03-14
#
# Description: This is a custom implementation added to the original project
# to support traditional page-based pagination as an alternative
# to the infinite scroll pagination in MessageListApi.
#------------------------------------------------------------------------------
class MessagePaginationApi(WebApiResource):
    """Standard pagination API for retrieving messages by page number.
    
    This endpoint provides traditional page-based pagination for message retrieval,
    returning a fixed number of messages per page along with metadata about
    total count and whether more pages exist.
    
    Endpoints:
        GET /messages/pagination
        
    Query Parameters:
        conversation_id (uuid): ID of the conversation to retrieve messages from
        page (int): Page number to retrieve (default: 1)
        limit (int): Number of messages per page (default: 20)
        
    Returns:
        dict: Pagination metadata and list of messages
        
    Raises:
        NotChatAppError: If the app is not configured for chat
        NotFound: If the specified conversation doesn't exist
    """

    message_fields = {
        "id": fields.String,
        "conversation_id": fields.String,
        "inputs": fields.Raw,
        "query": fields.String,
        "answer": fields.String(attribute="re_sign_file_url_answer"),
    }

    message_pagination_fields = {
        "page": fields.Integer,
        "limit": fields.Integer,
        "total": fields.Integer,
        "has_more": fields.Boolean,
        "data": fields.List(fields.Nested(message_fields)),
    }

    @marshal_with(message_pagination_fields)
    def get(self, app_model, end_user):
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode not in [AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT]:
            raise NotChatAppError()

        parser = reqparse.RequestParser()
        parser.add_argument("conversation_id", required=True, type=uuid_value, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("limit", type=int, default=20, location="args")
        args = parser.parse_args()

        try:
            messages, total_count = MessageService.pagination_by_page(
                app_model, end_user, args["conversation_id"], args["page"], args["limit"]
            )
        except services.errors.conversation.ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")

        has_more = (args["page"] * args["limit"]) < total_count

        return {
            "page": args["page"],
            "limit": args["limit"],
            "total": total_count,
            "has_more": has_more,
            "data": messages,
        }

api.add_resource(MessageListApi, "/messages")
api.add_resource(MessageFeedbackApi, "/messages/<uuid:message_id>/feedbacks")
api.add_resource(MessageMoreLikeThisApi, "/messages/<uuid:message_id>/more-like-this")
api.add_resource(MessageSuggestedQuestionApi, "/messages/<uuid:message_id>/suggested-questions")

# CODELIGHT_CUSTOMIZATION: Added standard pagination API endpoint
api.add_resource(MessagePaginationApi, "/messages/pagination")
