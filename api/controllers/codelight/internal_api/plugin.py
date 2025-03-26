"""
Codelight Chat API Controller

This module is a modified version of the original plugin.py file from the console controllers.
Original source: api/controllers/console/workspace/plugin.py

Key modifications:
- Customized for Codelight application
- Removed login_required decorator
- Passed tenant_id as a parameter to the post method

It provides endpoints for processing chat messages with support for different app modes
and streaming responses.
"""

from flask_restful import Resource, reqparse  # type: ignore

from controllers.codelight import api
from controllers.console.workspace import plugin_permission_required
from controllers.console.wraps import account_initialization_required, setup_required
from core.model_runtime.utils.encoders import jsonable_encoder
from core.plugin.manager.exc import PluginDaemonClientSideError

from services.plugin.plugin_service import PluginService


class PluginInstallFromMarketplaceApi(Resource):
    @setup_required
    @account_initialization_required
    @plugin_permission_required(install_required=True)
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("tenant_id", type=str, required=True, location="json")
        parser.add_argument("plugin_unique_identifiers", type=list, required=True, location="json")
        args = parser.parse_args()

        # check if all plugin_unique_identifiers are valid string
        for plugin_unique_identifier in args["plugin_unique_identifiers"]:
            if not isinstance(plugin_unique_identifier, str):
                raise ValueError("Invalid plugin unique identifier")

        try:
            response = PluginService.install_from_marketplace_pkg(args["tenant_id"], args["plugin_unique_identifiers"])
        except PluginDaemonClientSideError as e:
            raise ValueError(e)

        return jsonable_encoder(response)


api.add_resource(PluginInstallFromMarketplaceApi, "/plugin/install/marketplace")