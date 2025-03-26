from flask_restful import Resource, reqparse
from flask import current_app

from controllers.codelight import api

from controllers.console.wraps import setup_required
from controllers.inner_api.wraps import inner_api_only
from services.account_service import RegisterService


class CodelightAccountAPI(Resource):
    @setup_required
    @inner_api_only
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("email", type=str, required=True, location="json")
        parser.add_argument("name", type=str, required=True, location="json")
        parser.add_argument("password", type=str, required=False, location="json")
        parser.add_argument("interface_language", type=str, required=False, location="json")
        args = parser.parse_args()

        try:
            account = RegisterService.register(
                email=args["email"],
                name=args["name"],
                password=args["password"],
                language=args["interface_language"],
                is_setup=True,
            )

            current_app.logger.info(f"Account created: {account.id} - {account.name}")

            return {
                "message": "Account created successfully.",
                "account_id": account.id,
            }, 201
        except Exception as e:
            current_app.logger.error(f"Account creation failed: {str(e)}")
            return {"message": f"Account creation failed: {str(e)}"}, 400


api.add_resource(CodelightAccountAPI, "/accounts")
