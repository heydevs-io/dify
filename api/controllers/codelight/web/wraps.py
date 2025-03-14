from typing import Optional
from models.model import App, EndUser
from extensions.ext_database import db


def create_or_update_end_user_for_user_id(
    app_model: App,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    is_anonymous: bool = True,
    type: str = "browser",
) -> EndUser:
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
            EndUser.type == type,
            EndUser.is_anonymous == is_anonymous,
        )
        .first()
    )
    
    if end_user is not None:
        end_user.name = user_name
        db.session.commit()
        return end_user
    
    
    if end_user is None:
        end_user = EndUser(
            tenant_id=app_model.tenant_id,
            app_id=app_model.id,
            type=type,
            is_anonymous=is_anonymous,
            session_id=user_id,
            name=user_name,
        )
        db.session.add(end_user)
        db.session.commit()

    return end_user
