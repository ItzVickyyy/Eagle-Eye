import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import func as sa_func
from sqlmodel import col, func, select

from app.api.deps import (
    AdminUser,
    CurrentUser,
    OptionalCurrentUser,
    SessionDep,
    is_admin_or_above,
)
from app.core.audit import write_audit_log
from app.core.sanitizer import sanitize_html
from app.models import (
    Article,
    ArticleCreate,
    ArticleDetailPublic,
    ArticlePublic,
    ArticlesPublic,
    ArticleStatus,
    ArticleTag,
    ArticleUpdate,
    Category,
    Message,
    Tag,
    TagPublic,
    User,
)

router = APIRouter(prefix="/articles", tags=["articles"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "article"


def _fts_document() -> Any:
    """The searchable document for an article.

    This expression is textually identical to the functional index created in
    migration ``3e4f5a6b7c8d`` (``to_tsvector`` over headline + excerpt + a
    tag-stripped body), so PostgreSQL can use the ``GIN`` index for lookups.
    HTML markup is removed at search/index time only; the write-time
    sanitization pipeline is untouched.

    Uses the ``||`` operator (IMMUTABLE) rather than ``concat_ws`` (STABLE) so
    the same expression is valid as both an index expression and a runtime
    filter expression. The space separator is rendered as a typed SQL literal
    so PostgreSQL constant-folds it identically to the migration's literal
    ``' '`` and the planner matches the functional GIN index.
    """
    from sqlalchemy import String, literal_column

    space: Any = literal_column("' '", String)
    return sa_func.regexp_replace(
        sa_func.coalesce(Article.headline, "")
        .op("||")(space)
        .op("||")(sa_func.coalesce(Article.excerpt, ""))
        .op("||")(space)
        .op("||")(sa_func.coalesce(Article.body, "")),
        "<[^>]+>",
        "",
        "g",
    )


_FTS_OPERATOR = "@@"


def _apply_search_filter(
    statement: Any, search: str, dialect_name: str
) -> tuple[Any, Any | None, bool]:
    """Filter ``statement`` to articles matching ``search``.

    Returns ``(statement, rank_expr, is_fts)``. On PostgreSQL this uses
    full-text search (``to_tsvector`` / ``websearch_to_tsquery``) backed by the
    functional ``GIN`` index and yields a ``ts_rank`` expression for relevance
    ordering. On any other dialect (e.g. SQLite in tests) it falls back to the
    legacy ``ILIKE`` substring match so behavior and the public contract are
    preserved.
    """
    q = search.strip()
    if not q:
        return statement, None, False

    if dialect_name == "postgresql":
        document = _fts_document()
        query = sa_func.websearch_to_tsquery("english", q)
        statement = statement.where(
            sa_func.to_tsvector("english", document).op(_FTS_OPERATOR)(query)
        )
        rank = sa_func.ts_rank(sa_func.to_tsvector("english", document), query)
        return statement, rank, True

    pattern = f"%{q}%"
    statement = statement.where(
        (Article.headline.ilike(pattern))  # type: ignore[attr-defined]
        | (Article.excerpt.ilike(pattern))  # type: ignore[union-attr]
        | (Article.body.ilike(pattern))  # type: ignore[union-attr]
    )
    return statement, None, False


@router.get("/", response_model=ArticlesPublic)
def read_articles(
    session: SessionDep,
    current_user: OptionalCurrentUser = None,
    skip: int = 0,
    limit: int = 20,
    category_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    author_id: uuid.UUID | None = None,
    status: ArticleStatus | None = None,
    search: str | None = None,
    mine_only: bool = False,
) -> Any:
    """
    Retrieve articles with optional filtering by status, category, tag, author, or search keyword.
    Guests and regular readers only see published articles.
    Authenticated contributors can see their own drafts/pending, and Admins can see all.
    """
    statement = select(Article)

    # Permissions filtering
    if not current_user:
        # Unauthenticated: published only
        statement = statement.where(Article.status == ArticleStatus.published)
    elif mine_only:
        statement = statement.where(Article.author_id == current_user.id)
        if status:
            statement = statement.where(Article.status == status)
    elif not is_admin_or_above(current_user):
        # Contributor can view published OR their own articles
        if status and status != ArticleStatus.published:
            statement = statement.where(
                Article.author_id == current_user.id,
                Article.status == status,
            )
        else:
            statement = statement.where(
                (Article.status == ArticleStatus.published)
                | (Article.author_id == current_user.id)
            )
    else:
        # Admin / Super Admin
        if status:
            statement = statement.where(Article.status == status)

    if category_slug:
        cat = session.exec(select(Category).where(Category.slug == category_slug)).first()
        if cat:
            statement = statement.where(Article.category_id == cat.id)
        else:
            return ArticlesPublic(data=[], count=0)

    if category_id:
        statement = statement.where(Article.category_id == category_id)

    if author_id:
        statement = statement.where(Article.author_id == author_id)

    if tag_id:
        statement = (
            statement.join(ArticleTag, Article.id == ArticleTag.article_id)  # type: ignore[arg-type]
            .where(ArticleTag.tag_id == tag_id)
        )

    search_rank = None
    if search:
        dialect_name = str(session.get_bind().dialect.name)
        statement, search_rank, _ = _apply_search_filter(
            statement, search, dialect_name
        )

    # Count query
    count_statement = select(func.count()).select_from(statement.subquery())
    count = session.exec(count_statement).one()

    # Sort by relevance when a full-text search is active, otherwise by recency.
    order = []
    if search_rank is not None:
        order.append(search_rank.desc())
    order.extend(
        [
            col(Article.date_published).desc().nullslast(),
            col(Article.created_at).desc(),
        ]
    )
    # O5: cap client-controlled limit to a server-defined maximum (200) so
    # a single request cannot page through the entire table.
    safe_limit = max(1, min(int(limit), 200))
    statement = statement.order_by(*order).offset(skip).limit(safe_limit)

    articles = session.exec(statement).all()
    articles_public = [ArticlePublic.model_validate(art) for art in articles]
    return ArticlesPublic(data=articles_public, count=count)


@router.get("/review-queue", response_model=ArticlesPublic)
def get_review_queue(
    session: SessionDep,
    _current_user: AdminUser,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    Get articles pending review for Admins/Super Admins.
    """
    statement = (
        select(Article)
        .where(Article.status == ArticleStatus.pending)
        .order_by(col(Article.created_at).asc())
    )
    count_statement = select(func.count()).select_from(statement.subquery())
    count = session.exec(count_statement).one()

    # O5: cap client-controlled limit to a server-defined maximum (200).
    safe_limit = max(1, min(int(limit), 200))
    articles = session.exec(statement.offset(skip).limit(safe_limit)).all()
    articles_public = [ArticlePublic.model_validate(art) for art in articles]
    return ArticlesPublic(data=articles_public, count=count)


def _can_view_unpublished_article(article: Article, current_user: User | None) -> bool:
    """Whether ``current_user`` is allowed to read a non-published article.

    The codebase has no reviewer-assignment model, so the only supported
    reader of an unpublished article is its author. Anyone else — including
    unrelated admins, super-admins, and developers — is treated as
    unauthorized.

    Callers must raise ``HTTPException(404)`` when this returns ``False`` so
    the article's existence is not disclosed.
    """
    if current_user is None:
        return False
    return article.author_id == current_user.id


@router.get("/slug/{slug}", response_model=ArticleDetailPublic)
def get_article_by_slug(
    slug: str,
    session: SessionDep,
    current_user: OptionalCurrentUser = None,
) -> Any:
    """
    Get single article by slug. Increments views_count if published.
    """
    statement = select(Article).where(Article.slug == slug)
    article = session.exec(statement).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Visibility check: non-published articles are author-only.
    if article.status != ArticleStatus.published:
        if not _can_view_unpublished_article(article, current_user):
            raise HTTPException(status_code=404, detail="Article not found")
    else:
        # Increment views
        article.views_count += 1
        session.add(article)
        session.commit()
        session.refresh(article)

    # Build detailed response
    author = session.get(User, article.author_id)
    category = session.get(Category, article.category_id) if article.category_id else None
    tags_query = (
        select(Tag)
        .join(ArticleTag, Tag.id == ArticleTag.tag_id)  # type: ignore[arg-type]
        .where(ArticleTag.article_id == article.id)
    )
    tags = session.exec(tags_query).all()

    detail = ArticleDetailPublic.model_validate(article)
    detail.author = author  # type: ignore[assignment]
    detail.category = category  # type: ignore[assignment]
    detail.tags = [TagPublic.model_validate(t) for t in tags]
    return detail


@router.get("/{id}", response_model=ArticleDetailPublic)
def get_article_by_id(
    id: uuid.UUID,
    session: SessionDep,
    current_user: OptionalCurrentUser = None,
) -> Any:
    """
    Get article by ID.
    """
    article = session.get(Article, id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Visibility check: non-published articles are author-only.
    if article.status != ArticleStatus.published:
        if not _can_view_unpublished_article(article, current_user):
            raise HTTPException(status_code=404, detail="Article not found")

    author = session.get(User, article.author_id)
    category = session.get(Category, article.category_id) if article.category_id else None
    tags_query = (
        select(Tag)
        .join(ArticleTag, Tag.id == ArticleTag.tag_id)  # type: ignore[arg-type]
        .where(ArticleTag.article_id == article.id)
    )
    tags = session.exec(tags_query).all()

    detail = ArticleDetailPublic.model_validate(article)
    detail.author = author  # type: ignore[assignment]
    detail.category = category  # type: ignore[assignment]
    detail.tags = [TagPublic.model_validate(t) for t in tags]
    return detail


@router.post("/", response_model=ArticlePublic)
def create_article(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    article_in: ArticleCreate,
) -> Any:
    """
    Create a new article.
    Contributors can save as draft or submit as pending review.
    Admins / Super Admins can publish directly.
    """
    # Generate unique slug if not provided or collision
    base_slug = slugify(article_in.slug or article_in.headline)
    slug = base_slug
    counter = 1
    while session.exec(select(Article).where(Article.slug == slug)).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Check status permissions
    desired_status = article_in.status
    if not is_admin_or_above(current_user) and desired_status in (
        ArticleStatus.published,
        ArticleStatus.archived,
    ):
        # Contributors cannot directly publish; force pending review
        desired_status = ArticleStatus.pending

    if article_in.category_id is not None:
        cat = session.get(Category, article_in.category_id)
        if not cat:
            raise HTTPException(
                status_code=400,
                detail=f"Category with id {article_in.category_id} does not exist",
            )

    now = datetime.now(UTC)
    date_published = now if desired_status == ArticleStatus.published else None

    article = Article(
        headline=article_in.headline,
        slug=slug,
        excerpt=article_in.excerpt,
        cover_image_url=article_in.cover_image_url,
        body=sanitize_html(article_in.body),
        category_id=article_in.category_id,
        author_id=current_user.id,
        status=desired_status,
        date_published=date_published,
        created_at=now,
        updated_at=now,
    )
    session.add(article)
    session.commit()
    session.refresh(article)

    # Attach tags
    if article_in.tag_ids:
        unique_tag_ids = list(dict.fromkeys(article_in.tag_ids))
        for tid in unique_tag_ids:
            tag = session.get(Tag, tid)
            if not tag:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tag with id {tid} does not exist",
                )
            session.add(ArticleTag(article_id=article.id, tag_id=tid))
        session.commit()

    write_audit_log(
        session=session,
        event="article.created",
        component="article",
        actor=current_user,
        target_type="article",
        target_id=str(article.id),
        success=True,
        message=f"Article created (status={desired_status.value})",
    )
    session.commit()
    return article


@router.patch("/{id}", response_model=ArticlePublic)
def update_article(
    *,
    session: SessionDep,
    id: uuid.UUID,
    article_in: ArticleUpdate,
    current_user: CurrentUser,
) -> Any:
    """
    Update article.
    Authors can update their own drafts/pending.
    Admins/Super Admins can update any article and publish/archive/approve/reject.
    """
    article = session.get(Article, id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    is_admin = is_admin_or_above(current_user)
    if not is_admin and article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this article")

    # If contributor is editing a published article, they can't change it directly to published
    update_dict = article_in.model_dump(exclude_unset=True)

    if "body" in update_dict and update_dict["body"] is not None:
        update_dict["body"] = sanitize_html(update_dict["body"])

    if "status" in update_dict:
        new_status = update_dict["status"]
        if not is_admin and new_status in (ArticleStatus.published, ArticleStatus.archived):
            update_dict["status"] = ArticleStatus.pending
        new_status = update_dict["status"]

        if new_status == ArticleStatus.published and not article.date_published:
            article.date_published = datetime.now(UTC)

    if "slug" in update_dict and update_dict["slug"]:
        new_slug = slugify(update_dict["slug"])
        if new_slug != article.slug:
            existing = session.exec(select(Article).where(Article.slug == new_slug)).first()
            if existing and existing.id != article.id:
                raise HTTPException(status_code=409, detail="Slug already in use")
            update_dict["slug"] = new_slug

    if "category_id" in update_dict and update_dict["category_id"] is not None:
        cat = session.get(Category, update_dict["category_id"])
        if not cat:
            raise HTTPException(
                status_code=400,
                detail=f"Category with id {update_dict['category_id']} does not exist",
            )

    tag_ids = update_dict.pop("tag_ids", None)
    if tag_ids is not None:
        unique_tag_ids = list(dict.fromkeys(tag_ids))
        for tid in unique_tag_ids:
            tag = session.get(Tag, tid)
            if not tag:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tag with id {tid} does not exist",
                )
        # replace existing tags
        session.exec(
            ArticleTag.__table__.delete().where(ArticleTag.article_id == article.id)  # type: ignore
        )
        for tid in unique_tag_ids:
            session.add(ArticleTag(article_id=article.id, tag_id=tid))

    prev_status = article.status.value
    article.updated_at = datetime.now(UTC)
    article.sqlmodel_update(update_dict)
    session.add(article)
    session.commit()
    session.refresh(article)

    if "status" in update_dict and update_dict["status"].value != prev_status:
        write_audit_log(
            session=session,
            event="article.status_changed",
            component="article",
            actor=current_user,
            target_type="article",
            target_id=str(article.id),
            success=True,
            message=f"Article status changed to {update_dict['status'].value}",
        )
        session.commit()
    return article


@router.delete("/{id}", response_model=Message)
def delete_article(
    *,
    session: SessionDep,
    id: uuid.UUID,
    current_user: CurrentUser,
) -> Message:
    """
    Delete article.
    Author can delete if draft. Admin/Super Admin can delete any article.
    """
    article = session.get(Article, id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if not is_admin_or_above(current_user):
        if article.author_id != current_user.id or article.status != ArticleStatus.draft:
            raise HTTPException(
                status_code=403,
                detail="Contributors can only delete their own unpublished drafts",
            )

    write_audit_log(
        session=session,
        event="article.deleted",
        component="article",
        actor=current_user,
        target_type="article",
        target_id=str(article.id),
        success=True,
        message=f"Article deleted ({article.headline})",
    )
    session.delete(article)
    session.commit()
    return Message(message="Article deleted successfully")
