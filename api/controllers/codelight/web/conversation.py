from flask_restful import marshal_with, reqparse
from flask_restful.inputs import int_range
from werkzeug.exceptions import NotFound

from controllers.codelight import api
from controllers.web.error import NotChatAppError
from controllers.web.wraps import WebApiResource
from core.app.entities.app_invoke_entities import InvokeFrom
from fields.conversation_fields import (
    codelight_web_conversation_pagination_fields,
    codelight_web_conversation_fields,
)
from models.model import AppMode
from services.conversation_service import ConversationService
from services.errors.conversation import ConversationNotExistsError


class CodelightWebConversationListApi(WebApiResource):
    @marshal_with(codelight_web_conversation_pagination_fields)
    def get(self, app_model, end_user):
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode not in [AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT]:
            raise NotChatAppError()

        parser = reqparse.RequestParser()
        parser.add_argument(
            "page", type=int_range(1, 99999), required=False, default=1, location="args"
        )
        parser.add_argument(
            "take", type=int_range(1, 100), required=False, default=20, location="args"
        )
        args = parser.parse_args()

        take = args.get("take")
        page = args.get("page")

        try:
            conversations = ConversationService.pagination_by_page(
                app_model=app_model,
                user=end_user,
                page=page,
                take=take,
                invoke_from=InvokeFrom.WEB_APP,
            )

            print(conversations)

            return conversations
        except ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")


class CodelightWebConversationApi(WebApiResource):
    @marshal_with(codelight_web_conversation_fields)
    def get(self, app_model, end_user, c_id):
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode not in [AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT]:
            raise NotChatAppError()

        try:
            conversation = ConversationService.get_conversation(
                app_model=app_model, user=end_user, conversation_id=str(c_id)
            )
            return conversation
        except ConversationNotExistsError:
            raise NotFound("Conversation Not Found.")


api.add_resource(CodelightWebConversationListApi, "/web/conversations")
api.add_resource(CodelightWebConversationApi, "/web/conversations/<uuid:c_id>")
