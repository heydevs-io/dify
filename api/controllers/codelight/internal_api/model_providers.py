import uuid
from flask_restful import Resource, reqparse

from controllers.console.wraps import setup_required
from controllers.inner_api.wraps import inner_api_only
from core.model_runtime.errors.validate import CredentialsValidateFailedError
from services.model_provider_service import ModelProviderService
from controllers.codelight import api


class CodelightModelProviderApi(Resource):
    @setup_required
    @inner_api_only
    def post(self, tenant_id: uuid.UUID):
        parser = reqparse.RequestParser()
        parser.add_argument("provider", type=str, required=True, location="json")
        parser.add_argument("credentials", type=dict, required=True, nullable=False, location="json")
        args = parser.parse_args()

        model_provider_service = ModelProviderService()

        try:
            model_provider_service.save_provider_credentials(
                tenant_id=str(tenant_id),
                provider=args["provider"],
                credentials=args["credentials"],
            )
        except CredentialsValidateFailedError as ex:
            raise ValueError(str(ex))

        return {"result": "success"}, 201


api.add_resource(
    CodelightModelProviderApi,
    "/tenants/<uuid:tenant_id>/model-providers",
)
