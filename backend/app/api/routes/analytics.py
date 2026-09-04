from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import col, func, select

from app.api.deps import AdminUser, SessionDep
from app.models import Article, ArticlePublic, ArticleStatus, Comment, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


class AnalyticsOverview(BaseModel):
    total_articles: int
    published_articles: int
    pending_articles: int
    draft_articles: int
    total_views: int
    total_users: int
    total_comments: int
    top_articles: list[ArticlePublic]


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    session: SessionDep,
    _current_user: AdminUser,
) -> Any:
    """
    Get high-level site publication and traffic analytics for Admin/Super Admin.
    """
    total_articles = session.exec(select(func.count()).select_from(Article)).one()
    published_articles = session.exec(
        select(func.count()).select_from(Article).where(Article.status == ArticleStatus.published)
    ).one()
    pending_articles = session.exec(
        select(func.count()).select_from(Article).where(Article.status == ArticleStatus.pending)
    ).one()
    draft_articles = session.exec(
        select(func.count()).select_from(Article).where(Article.status == ArticleStatus.draft)
    ).one()

    total_views = session.exec(select(func.coalesce(func.sum(Article.views_count), 0))).one()
    total_users = session.exec(select(func.count()).select_from(User)).one()
    total_comments = session.exec(select(func.count()).select_from(Comment)).one()

    top_articles_db = session.exec(
        select(Article)
        .where(Article.status == ArticleStatus.published)
        .order_by(col(Article.views_count).desc())
        .limit(5)
    ).all()
    top_articles = [ArticlePublic.model_validate(a) for a in top_articles_db]

    return AnalyticsOverview(
        total_articles=total_articles,
        published_articles=published_articles,
        pending_articles=pending_articles,
        draft_articles=draft_articles,
        total_views=total_views,
        total_users=total_users,
        total_comments=total_comments,
        top_articles=top_articles,
    )
