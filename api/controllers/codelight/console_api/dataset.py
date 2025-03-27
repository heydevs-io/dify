import services
from controllers.codelight import api
from controllers.console.wraps import setup_required
from controllers.console.wraps import account_initialization_required
from core.model_runtime.entities.model_entities import ModelType
from core.provider_manager import ProviderManager
from fields.dataset_fields import dataset_detail_fields, dataset_query_detail_fields
from flask import request
from flask_login import current_user
from flask_restful import Resource, marshal, marshal_with, reqparse
from libs.login import login_required
from models.dataset import Dataset, DatasetPermissionEnum
from services.dataset_service import DatasetPermissionService, DatasetService
from services.errors.dataset import DatasetNameDuplicateError
from werkzeug.exceptions import Forbidden, NotFound


def _validate_name(name):
    if not name or len(name) < 1 or len(name) > 40:
        raise ValueError("Name must be between 1 to 40 characters.")
    return name


def _validate_description_length(description):
    if len(description) > 400:
        raise ValueError("Description cannot exceed 400 characters.")
    return description


class CodelightDatasetListApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        print(123456)
        page = request.args.get("page", default=1, type=int)
        limit = request.args.get("limit", default=20, type=int)
        ids = request.args.getlist("ids")
        provider = request.args.get("provider", default="vendor")
        search = request.args.get("keyword", default=None, type=str)
        tag_ids = request.args.getlist("tag_ids")

        if ids:
            datasets, total = DatasetService.get_datasets_by_ids(ids, current_user.current_tenant_id)
        else:
            datasets, total = DatasetService.get_datasets(
                page, limit, provider, current_user.current_tenant_id, current_user, search, tag_ids
            )

        print("datasets", len(datasets))

        # check embedding setting
        provider_manager = ProviderManager()
        configurations = provider_manager.get_configurations(tenant_id=current_user.current_tenant_id)

        embedding_models = configurations.get_models(model_type=ModelType.TEXT_EMBEDDING, only_active=True)

        model_names = []
        for embedding_model in embedding_models:
            model_names.append(f"{embedding_model.model}:{embedding_model.provider.provider}")

        data = marshal(datasets, dataset_detail_fields)
        for item in data:
            if item["indexing_technique"] == "high_quality":
                item_model = f"{item['embedding_model']}:{item['embedding_model_provider']}"
                if item_model in model_names:
                    item["embedding_available"] = True
                else:
                    item["embedding_available"] = False
            else:
                item["embedding_available"] = True

            if item.get("permission") == "partial_members":
                part_users_list = DatasetPermissionService.get_dataset_partial_member_list(item["id"])
                item.update({"partial_member_list": part_users_list})
            else:
                item.update({"partial_member_list": []})

        response = {"data": data, "has_more": len(datasets) == limit, "limit": limit, "total": total, "page": page}
        return response, 200

    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "name",
            nullable=False,
            required=True,
            help="type is required. Name must be between 1 to 40 characters.",
            type=_validate_name,
        )
        parser.add_argument(
            "description",
            nullable=False,
            required=True,
            help="Description cannot exceed 400 characters.",
            type=_validate_description_length,
        )
        parser.add_argument(
            "indexing_technique",
            type=str,
            location="json",
            choices=Dataset.INDEXING_TECHNIQUE_LIST,
            nullable=True,
            help="Invalid indexing technique.",
        )
        args = parser.parse_args()

        # The role of the current user in the ta table must be admin, owner, or editor, or dataset_operator
        if not current_user.is_dataset_editor:
            raise Forbidden()

        try:
            dataset = DatasetService.create_empty_dataset(
                tenant_id=current_user.current_tenant_id,
                name=args["name"],
                description=args["description"],
                indexing_technique=args["indexing_technique"],
                account=current_user,
                permission=DatasetPermissionEnum.ALL_TEAM,
            )
        except services.errors.dataset.DatasetNameDuplicateError:
            raise DatasetNameDuplicateError()

        return marshal(dataset, dataset_detail_fields), 201


api.add_resource(CodelightDatasetListApi, "/datasets")
