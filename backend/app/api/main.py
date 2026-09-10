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
    review_assignments,
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
api_router.include_router(review_assignments.router)

# SECURITY: the /api/v1/private/* routes are dev-only helpers for bootstrapping
# users from the test suite and CLI scripts. They have NO authentication. They
# must NEVER be reachable in any non-development environment.
#
# `settings.FASTAPI_ENV` is typed as `Literal["development"] | None` in
# app.core.config, so any other value is rejected at startup. Production
# defaults to `None` (or any value other than "development"), and this
# conditional is the only line of defense. Do not broaden it without also
# adding a defense-in-depth check in the route itself.
if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)  # pragma: no cover - dev-only router
