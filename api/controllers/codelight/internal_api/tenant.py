import uuid
from flask_restful import Resource, reqparse
from flask import current_app

from controllers.console.wraps import setup_required
from controllers.inner_api.wraps import inner_api_only
from events.tenant_event import tenant_was_created
from models.account import Account
from services.account_service import TenantService
from controllers.codelight import api
from extensions.ext_database import db


class CodelightTenantApi(Resource):
    @setup_required
    @inner_api_only
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str, required=True, location="json")
        parser.add_argument("owner_email", type=str, required=True, location="json")
        args = parser.parse_args()

        account = db.session.query(Account).filter_by(email=args["owner_email"]).first()
        if account is None:
            return {"message": "owner account not found."}, 404

        tenant = TenantService.create_tenant(args["name"])
        TenantService.create_tenant_member(tenant, account, role="owner")

        tenant_was_created.send(tenant)

        current_app.logger.info(f"Tenant created: {tenant.id} - {tenant.name}")

        return {"message": "Tenant created successfully.", "tenant_id": tenant.id}, 201


class CodelightTenantMemberApi(Resource):
    @setup_required
    @inner_api_only
    def post(self, tenant_id: uuid.UUID):
        parser = reqparse.RequestParser()
        parser.add_argument("account_id", type=str, required=True, location="json")
        parser.add_argument("role", type=str, required=False, default="normal", location="json")
        args = parser.parse_args()

        try:
            tenant_account_join = TenantService.add_member_to_tenant(
                account_id=args["account_id"],
                tenant_id=str(tenant_id),
                role=args["role"],
            )
            current_app.logger.info(
                f"Member added to tenant: {tenant_account_join.tenant_id} - {tenant_account_join.account_id}"
            )
            return {"message": "Member added to tenant successfully."}, 201
        except ValueError as e:
            return {"message": str(e)}, 404
        except Exception as e:
            current_app.logger.error(f"Error adding member to tenant: {str(e)}")
            return {"message": "An error occurred while adding member to tenant."}, 500


api.add_resource(CodelightTenantApi, "/tenants")
api.add_resource(CodelightTenantMemberApi, "/tenants/<uuid:tenant_id>/members")
