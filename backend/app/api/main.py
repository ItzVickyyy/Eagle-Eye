from fastapi import APIRouter

from app.api.routes import (
    analytics,
    articles,
    categories,
    club_members,
    comments,
    contact,
    developer,
    login,
    media,
    private,
    tags,
    users,
    utils,
)
from app.api.routes import (
    settings as site_settings,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(articles.router)
api_router.include_router(categories.router)
api_router.include_router(tags.router)
api_router.include_router(comments.router)
api_router.include_router(club_members.router)
api_router.include_router(contact.router)
api_router.include_router(developer.router)
api_router.include_router(site_settings.router)
api_router.include_router(media.router)
api_router.include_router(analytics.router)
api_router.include_router(utils.router)

if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
