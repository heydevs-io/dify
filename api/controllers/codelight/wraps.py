from collections.abc import Callable
from typing import Optional, Union
from enum import Enum
from functools import wraps
from typing import Optional

from flask import request
from pydantic import BaseModel
from werkzeug.exceptions import Forbidden, Unauthorized

from controllers.console.app.error import AppNotFoundError
from extensions.ext_database import db
from models.account import Tenant, TenantStatus
from models.model import App, AppMode, EndUser


class WhereisUserArg(Enum):
    """
    Enum for whereis_user_arg.
    """

    QUERY = "query"
    JSON = "json"
    FORM = "form"


class FetchUserArg(BaseModel):
    fetch_from: WhereisUserArg
    required: bool = False


def create_or_update_end_user_for_user_id(app_model: App, user_id: Optional[str] = None) -> EndUser:
    """
    Create or update session terminal based on user ID.
    """
    if not user_id:
        user_id = "DEFAULT-USER"

    end_user = (
        db.session.query(EndUser)
        .filter(
            EndUser.tenant_id == app_model.tenant_id,
            EndUser.app_id == app_model.id,
            EndUser.session_id == user_id,
            EndUser.type == "service_api",
        )
        .first()
    )

    if end_user is None:
        end_user = EndUser(
            tenant_id=app_model.tenant_id,
            app_id=app_model.id,
            type="service_api",
            is_anonymous=True if user_id == "DEFAULT-USER" else False,
            session_id=user_id,
        )
        db.session.add(end_user)
        db.session.commit()

    return end_user


def validate_app_id(view: Optional[Callable] = None, *, fetch_user_arg: Optional[FetchUserArg] = None):
    def decorator(view_func):
        @wraps(view_func)
        def decorated_view(*args, **kwargs):
            app_id = request.headers.get("X-App-Id")
            if not app_id:
                raise Unauthorized("X-App-Id header is missing.")

            app_model = db.session.query(App).filter(App.id == app_id).first()
            if not app_model:
                raise Forbidden("The app no longer exists.")

            if app_model.status != "normal":
                raise Forbidden("The app's status is abnormal.")

            if not app_model.enable_api:
                raise Forbidden("The app's API service has been disabled.")

            tenant = db.session.query(Tenant).filter(Tenant.id == app_model.tenant_id).first()
            if tenant.status == TenantStatus.ARCHIVE:
                raise Forbidden("The workspace's status is archived.")

            kwargs["app_model"] = app_model

            if fetch_user_arg:
                if fetch_user_arg.fetch_from == WhereisUserArg.QUERY:
                    user_id = request.args.get("user")
                elif fetch_user_arg.fetch_from == WhereisUserArg.JSON:
                    user_id = request.get_json().get("user")
                elif fetch_user_arg.fetch_from == WhereisUserArg.FORM:
                    user_id = request.form.get("user")
                else:
                    # use default-user
                    user_id = None

                if not user_id and fetch_user_arg.required:
                    raise ValueError("Arg user must be provided.")

                if user_id:
                    user_id = str(user_id)

                kwargs["end_user"] = create_or_update_end_user_for_user_id(app_model, user_id)

            return view_func(*args, **kwargs)

        return decorated_view

    if view is None:
        return decorator
    else:
        return decorator(view)


def get_app_model_with_tenant_id(view: Optional[Callable] = None, *, mode: Union[AppMode, list[AppMode]] = None):
    def decorator(view_func):
        @wraps(view_func)
        def decorated_view(*args, **kwargs):
            if not kwargs.get("app_id"):
                raise ValueError("missing app_id in path parameters")

            app_id = kwargs.get("app_id")
            app_id = str(app_id)

            del kwargs["app_id"]

            if not kwargs.get("tenant_id"):
                raise ValueError("missing tenant_id in path parameters")

            tenant_id = kwargs.get("tenant_id")
            tenant_id = str(tenant_id)

            del kwargs["tenant_id"]

            app_model = (
                db.session.query(App)
                .filter(App.id == app_id, App.tenant_id == tenant_id, App.status == "normal")
                .first()
            )

            if not app_model:
                raise AppNotFoundError()

            app_mode = AppMode.value_of(app_model.mode)
            if app_mode == AppMode.CHANNEL:
                raise AppNotFoundError()

            if mode is not None:
                if isinstance(mode, list):
                    modes = mode
                else:
                    modes = [mode]

                if app_mode not in modes:
                    mode_values = {m.value for m in modes}
                    raise AppNotFoundError(f"App mode is not in the supported list: {mode_values}")

            kwargs["app_model"] = app_model

            return view_func(*args, **kwargs)

        return decorated_view

    if view is None:
        return decorator
    else:
        return decorator(view)
