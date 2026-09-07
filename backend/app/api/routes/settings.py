from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, SuperAdminUser
from app.core.audit import write_audit_log
from app.models import (
    Message,
    SiteSetting,
    SiteSettingCreate,
    SiteSettingPublic,
    SiteSettingsPublic,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=SiteSettingsPublic)
def get_site_settings(session: SessionDep) -> Any:
    """
    Get all site settings (public).
    """
    settings = session.exec(select(SiteSetting)).all()
    public_settings = [SiteSettingPublic.model_validate(s) for s in settings]
    return SiteSettingsPublic(data=public_settings, count=len(public_settings))


@router.get("/{key}", response_model=SiteSettingPublic)
def get_site_setting(key: str, session: SessionDep) -> Any:
    """
    Get single setting by key.
    """
    setting = session.get(SiteSetting, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.post("/", response_model=SiteSettingPublic)
def set_site_setting(
    *,
    session: SessionDep,
    setting_in: SiteSettingCreate,
    _current_user: SuperAdminUser,
) -> Any:
    """
    Set or update a site setting (Super Admin).
    """
    setting = session.get(SiteSetting, setting_in.key)
    if setting:
        setting.value = setting_in.value
    else:
        setting = SiteSetting(key=setting_in.key, value=setting_in.value)
    session.add(setting)
    session.commit()
    session.refresh(setting)
    return setting


@router.delete("/{key}", response_model=Message)
def delete_site_setting(
    *,
    session: SessionDep,
    key: str,
    current_user: SuperAdminUser,
) -> Message:
    """
    Delete a site setting (Super Admin).
    """
    setting = session.get(SiteSetting, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    write_audit_log(
        session=session,
        event="site_setting.deleted",
        component="site_setting",
        actor=current_user,
        target_type="site_setting",
        target_id=setting.key,
        success=True,
        message=f"Site setting deleted ({setting.key})",
    )
    session.delete(setting)
    session.commit()
    return Message(message="Setting deleted successfully")
