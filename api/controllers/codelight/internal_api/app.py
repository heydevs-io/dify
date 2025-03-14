from flask_restful import Resource, marshal_with, reqparse
from werkzeug.exceptions import BadRequest, Forbidden

from models.account import TenantAccountJoin, TenantAccountJoinRole
from services.account_service import AccountService, TenantService
from controllers.inner_api.wraps import inner_api_only
from controllers.codelight import api
from controllers.console.wraps import setup_required
from fields.app_fields import app_detail_fields
from libs.login import login_required
from services.app_service import AppService

ALLOW_CREATE_APP_MODES = [
    "chat",
    "agent-chat",
    "advanced-chat",
    "workflow",
    "completion",
]


class CodelightAppListApi(Resource):
    @setup_required
    @inner_api_only
    @marshal_with(app_detail_fields)
    def post(self):
        """Create app"""
        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str, required=True, location="json")
        parser.add_argument("description", type=str, location="json")
        parser.add_argument("mode", type=str, choices=ALLOW_CREATE_APP_MODES, location="json")
        parser.add_argument("icon_type", type=str, location="json")
        parser.add_argument("icon", type=str, location="json")
        parser.add_argument("icon_background", type=str, location="json")
        parser.add_argument("tenant_id", type=str, required=True, location="json")
        parser.add_argument("account_id", type=str, required=True, location="json")
        args = parser.parse_args()

        # Check if the account is the owner of the tenant
        account = AccountService.load_user(args["account_id"])

        if not account:
            raise BadRequest("Account not found")

        tenant_join = TenantAccountJoin.query.filter_by(tenant_id=args["tenant_id"], account_id=account.id).first()

        if not tenant_join.role == TenantAccountJoinRole.OWNER.value:
            raise Forbidden("Only the tenant owner can create apps")

        if "mode" not in args or args["mode"] is None:
            raise BadRequest("mode is required")

        app_service = AppService()
        app = app_service.create_app(args["tenant_id"], args, account)

        return app, 201


api.add_resource(CodelightAppListApi, "/apps")
