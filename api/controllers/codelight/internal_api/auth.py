from flask_restful import Resource, reqparse
from flask import request
from controllers.inner_api.wraps import inner_api_only
from services.account_service import AccountService, TenantService
from libs.helper import email, extract_remote_ip
from controllers.console.wraps import setup_required
from controllers.codelight import api
import services


class CodelightLoginWithoutPasswordApi(Resource):
    """Resource for user login without password."""

    @setup_required
    @inner_api_only
    def post(self):
        """Authenticate user and login."""
        parser = reqparse.RequestParser()
        parser.add_argument("email", type=email, required=True, location="json")
        args = parser.parse_args()

        try:
            account = AccountService.authenticate_without_password(args["email"])
        except services.errors.account.AccountLoginError as e:
            return {"code": "unauthorized", "message": str(e)}, 401

        # SELF_HOSTED only have one workspace
        tenants = TenantService.get_join_tenants(account)
        if len(tenants) == 0:
            return {
                "result": "fail",
                "data": "workspace not found, please contact system admin to invite you to join in a workspace",
            }

        token = AccountService.login(account, ip_address=extract_remote_ip(request))

        return {"result": "success", "data": token.access_token}


api.add_resource(CodelightLoginWithoutPasswordApi, "/login-without-password")
