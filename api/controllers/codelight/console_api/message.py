import logging

from flask_login import current_user
from flask_restful import Resource, fields, marshal_with, reqparse
from flask_restful.inputs import int_range
from werkzeug.exceptions import Forbidden, InternalServerError, NotFound

from controllers.codelight import api
from controllers.console.app.error import (
    CompletionRequestError,
    ProviderModelCurrentlyNotSupportError,
    ProviderNotInitializeError,
    ProviderQuotaExceededError,
)
from controllers.console.app.wraps import get_app_model
from controllers.console.explore.error import AppSuggestedQuestionsAfterAnswerDisabledError
from controllers.console.wraps import setup_required
from controllers.console.wraps import account_initialization_required, cloud_edition_billing_resource_check
from core.app.entities.app_invoke_entities import InvokeFrom
from core.errors.error import ModelCurrentlyNotSupportError, ProviderTokenNotInitError, QuotaExceededError
from core.model_runtime.errors.invoke import InvokeError
from extensions.ext_database import db
from fields.conversation_fields import annotation_fields, message_detail_fields
from libs.helper import uuid_value
from libs.infinite_scroll_pagination import InfiniteScrollPagination
from libs.login import login_required
from models.model import AppMode, Conversation, Message, MessageAnnotation, MessageFeedback
from services.annotation_service import AppAnnotationService
from services.errors.conversation import ConversationNotExistsError
from services.errors.message import MessageNotExistsError, SuggestedQuestionsAfterAnswerDisabledError
from services.message_service import MessageService

class CodelightChatMessageListApi(Resource):
    message_pagination_fields = {
        "page": fields.Integer,
        "limit": fields.Integer,
        "total": fields.Integer,
        "has_more": fields.Boolean,
        "data": fields.List(fields.Nested(message_detail_fields)),
    }    

    @setup_required
    @login_required
    @get_app_model(mode=[AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT])
    @account_initialization_required
    @marshal_with(message_pagination_fields)
    def get(self, app_model):
        parser = reqparse.RequestParser()
        parser.add_argument("conversation_id", required=True, type=uuid_value, location="args")
        parser.add_argument("page", type=int, default=1,  location="args")
        parser.add_argument("limit", type=int, default=20, location="args")
        args = parser.parse_args()
        conversation = (
            db.session.query(Conversation)
            .filter(Conversation.id == args["conversation_id"], Conversation.app_id == app_model.id)
            .first()
        )

        if not conversation:
            raise NotFound("Conversation Not Exists.")

        # Calculate offset based on page and limit
        offset = (args["page"] - 1) * args["limit"]
        # Get total number of messages in the conversation
        total_messages = (
            db.session.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .count()
        )
        
        # Query messages with pagination
        history_messages = (
            db.session.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(args["limit"])
            .offset(offset)
            .all()
        )

        # Check if there are more messages
        has_more = (args["page"] * args["limit"]) < total_messages

        # Reverse the order of messages (optional, based on your requirement)
        history_messages = list(reversed(history_messages))

        return {
            "page": args["page"],
            "limit": args["limit"],
            "total": total_messages,
            "has_more": has_more,
            "data": history_messages,
        }

api.add_resource(CodelightChatMessageListApi, "/apps/<uuid:app_id>/chat-messages", endpoint="console_chat_messages1")