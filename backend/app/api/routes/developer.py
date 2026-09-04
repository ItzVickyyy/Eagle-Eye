import platform
import sys
import time
from datetime import UTC, datetime
from typing import Any

import fastapi
from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import func, select, text

from app.api.deps import DeveloperUser, SessionDep
from app.core.audit import write_audit_log
from app.core.config import settings
from app.models import (
    Article,
    AuditLog,
    Category,
    ClubMember,
    Comment,
    ContactMessage,
    SiteSetting,
    Tag,
    User,
)

router = APIRouter(prefix="/developer", tags=["developer"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SystemHealthResponse(BaseModel):
    status: str
    database_status: str
    database_latency_ms: float
    server_time_utc: datetime
    environment: str
    python_version: str
    fastapi_version: str
    platform_system: str


class SystemDiagnosticsResponse(BaseModel):
    database_engine: str
    total_users: int
    total_articles: int
    total_categories: int
    total_tags: int
    total_comments: int
    total_contact_messages: int
    total_members: int
    system_settings_count: int
    server_time_utc: datetime


class FeatureFlags(BaseModel):
    maintenance_mode: bool
    public_comments_enabled: bool
    contact_form_enabled: bool
    allow_public_signup: bool


class FeatureFlagsUpdate(BaseModel):
    maintenance_mode: bool | None = None
    public_comments_enabled: bool | None = None
    contact_form_enabled: bool | None = None
    allow_public_signup: bool | None = None


class SystemLogEntry(BaseModel):
    id: str
    timestamp: datetime
    level: str
    component: str
    message: str
    # Optional enriched fields surfaced from the audit trail.
    event: str | None = None
    actor: str | None = None
    target: str | None = None
    success: bool | None = None


class SystemLogsResponse(BaseModel):
    data: list[SystemLogEntry]
    count: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/health", response_model=SystemHealthResponse)
def get_system_health(
    session: SessionDep,
    current_user: DeveloperUser,
) -> Any:
    """
    Get backend system health and database connectivity latency (Developer only).
    """
    start_time = time.perf_counter()
    db_status = "connected"
    try:
        session.exec(text("SELECT 1"))
    except Exception:
        db_status = "error"
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return SystemHealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database_status=db_status,
        database_latency_ms=latency_ms,
        server_time_utc=datetime.now(UTC),
        environment=settings.FASTAPI_ENV or "production",
        python_version=sys.version.split()[0],
        fastapi_version=fastapi.__version__,
        platform_system=platform.platform(),
    )


@router.get("/diagnostics", response_model=SystemDiagnosticsResponse)
def get_system_diagnostics(
    session: SessionDep,
    current_user: DeveloperUser,
) -> Any:
    """
    Get aggregated system diagnostics and entity metrics (Developer only).
    """
    engine_name = session.bind.dialect.name if session.bind else "unknown"

    total_users = session.exec(select(func.count()).select_from(User)).one()
    total_articles = session.exec(select(func.count()).select_from(Article)).one()
    total_categories = session.exec(select(func.count()).select_from(Category)).one()
    total_tags = session.exec(select(func.count()).select_from(Tag)).one()
    total_comments = session.exec(select(func.count()).select_from(Comment)).one()
    total_contact_messages = session.exec(
        select(func.count()).select_from(ContactMessage)
    ).one()
    total_members = session.exec(select(func.count()).select_from(ClubMember)).one()
    system_settings_count = session.exec(
        select(func.count()).select_from(SiteSetting)
    ).one()

    return SystemDiagnosticsResponse(
        database_engine=engine_name,
        total_users=total_users,
        total_articles=total_articles,
        total_categories=total_categories,
        total_tags=total_tags,
        total_comments=total_comments,
        total_contact_messages=total_contact_messages,
        total_members=total_members,
        system_settings_count=system_settings_count,
        server_time_utc=datetime.now(UTC),
    )


def _get_flag(session: SessionDep, key: str, default: bool) -> bool:
    setting = session.get(SiteSetting, key)
    if setting and setting.value is not None:
        return setting.value.lower() in ("true", "1", "yes")
    return default


def _set_flag(session: SessionDep, key: str, value: bool) -> None:
    setting = session.get(SiteSetting, key)
    val_str = "true" if value else "false"
    if setting:
        setting.value = val_str
    else:
        setting = SiteSetting(key=key, value=val_str)
    session.add(setting)


@router.get("/feature-flags", response_model=FeatureFlags)
def get_feature_flags(
    session: SessionDep,
    current_user: DeveloperUser,
) -> Any:
    """
    Retrieve application-level technical feature flags and maintenance state (Developer only).
    """
    return FeatureFlags(
        maintenance_mode=_get_flag(session, "dev_maintenance_mode", False),
        public_comments_enabled=_get_flag(session, "dev_public_comments_enabled", True),
        contact_form_enabled=_get_flag(session, "dev_contact_form_enabled", True),
        allow_public_signup=_get_flag(session, "dev_allow_public_signup", True),
    )


@router.patch("/feature-flags", response_model=FeatureFlags)
def update_feature_flags(
    session: SessionDep,
    flags_in: FeatureFlagsUpdate,
    current_user: DeveloperUser,
) -> Any:
    """
    Update application-level technical feature flags and maintenance state (Developer only).
    """
    if flags_in.maintenance_mode is not None:
        _set_flag(session, "dev_maintenance_mode", flags_in.maintenance_mode)
    if flags_in.public_comments_enabled is not None:
        _set_flag(session, "dev_public_comments_enabled", flags_in.public_comments_enabled)
    if flags_in.contact_form_enabled is not None:
        _set_flag(session, "dev_contact_form_enabled", flags_in.contact_form_enabled)
    if flags_in.allow_public_signup is not None:
        _set_flag(session, "dev_allow_public_signup", flags_in.allow_public_signup)

    session.commit()

    write_audit_log(
        session=session,
        event="developer.feature_flags_updated",
        component="developer",
        actor=current_user,
        success=True,
        message="Developer feature flags updated",
    )
    session.commit()

    return FeatureFlags(
        maintenance_mode=_get_flag(session, "dev_maintenance_mode", False),
        public_comments_enabled=_get_flag(session, "dev_public_comments_enabled", True),
        contact_form_enabled=_get_flag(session, "dev_contact_form_enabled", True),
        allow_public_signup=_get_flag(session, "dev_allow_public_signup", True),
    )


@router.get("/logs", response_model=SystemLogsResponse)
def get_system_logs(
    session: SessionDep,
    current_user: DeveloperUser,
) -> Any:
    """
    Retrieve recent audit/application event logs (Developer only).

    Returns real persisted events from the audit trail. An empty list is a
    valid state: this endpoint does not fabricate sample activity.
    """
    entries = session.exec(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(200)
    ).all()

    if entries:
        data = [
            SystemLogEntry(
                id=entry.id.hex,
                timestamp=entry.created_at,
                level=entry.severity,
                component=entry.component,
                message=entry.message,
                event=entry.event,
                actor=entry.actor_email or "system",
                target=(
                    f"{entry.target_type}:{entry.target_id}"
                    if entry.target_type
                    else None
                ),
                success=entry.success,
            )
            for entry in entries
        ]
    else:
        data = []

    return SystemLogsResponse(data=data, count=len(data))
