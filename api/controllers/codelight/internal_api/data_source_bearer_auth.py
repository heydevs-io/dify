import uuid
from flask_restful import Resource, reqparse

from controllers.codelight import api
from controllers.console.auth.error import ApiKeyAuthFailedError
from services.auth.api_key_auth_service import ApiKeyAuthService
from controllers.console.wraps import setup_required
from controllers.inner_api.wraps import inner_api_only


class CodelightApiKeyAuthDataSourceBinding(Resource):
    @setup_required
    @inner_api_only
    def post(self, tenant_id: uuid.UUID):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "category", type=str, required=True, nullable=False, location="json"
        )
        parser.add_argument(
            "provider", type=str, required=True, nullable=False, location="json"
        )
        parser.add_argument(
            "credentials", type=dict, required=True, nullable=False, location="json"
        )
        args = parser.parse_args()
        ApiKeyAuthService.validate_api_key_auth_args(args)

        try:
            ApiKeyAuthService.create_provider_auth(tenant_id, args)
        except Exception as e:
            raise ApiKeyAuthFailedError(str(e))
        return {"result": "success"}, 200


api.add_resource(
    CodelightApiKeyAuthDataSourceBinding, "/tenants/<uuid:tenant_id>/data-sources"
)
