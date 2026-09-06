import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import EmailStr
from sqlalchemy import Column, DateTime, Integer, Text
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class UserRole(StrEnum):
    super_admin = "super_admin"
    admin = "admin"
    contributor = "contributor"


class ArticleStatus(StrEnum):
    draft = "draft"
    pending = "pending"
    published = "published"
    archived = "archived"


class CommentStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    spam = "spam"


class ContactMessageStatus(StrEnum):
    new = "new"
    read = "read"


# ---------------------------------------------------------------------------
# User Models
# ---------------------------------------------------------------------------


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    is_developer: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.contributor)
    department: str | None = Field(default=None, max_length=255)
    position_title: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    captcha_token: str | None = Field(default=None, max_length=4096)


class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_developer: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    department: str | None = Field(default=None, max_length=255)
    position_title: str | None = Field(default=None, max_length=255)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    position_title: str | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    token_version: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    articles: list[Article] = Relationship(
        back_populates="author", cascade_delete=True
    )
    media: list[Media] = Relationship(
        back_populates="uploaded_by_user", cascade_delete=True
    )


class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ---------------------------------------------------------------------------
# Category Models
# ---------------------------------------------------------------------------


class CategoryBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, unique=True, index=True)
    description: str | None = Field(default=None, max_length=500)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class Category(CategoryBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    articles: list[Article] = Relationship(back_populates="category")


class CategoryPublic(CategoryBase):
    id: int


class CategoriesPublic(SQLModel):
    data: list[CategoryPublic]
    count: int


# ---------------------------------------------------------------------------
# ArticleTag Junction Model
# ---------------------------------------------------------------------------


class ArticleTag(SQLModel, table=True):
    article_id: uuid.UUID = Field(
        foreign_key="article.id", primary_key=True, ondelete="CASCADE"
    )
    tag_id: int = Field(
        foreign_key="tag.id", primary_key=True, ondelete="CASCADE"
    )


# ---------------------------------------------------------------------------
# Tag Models
# ---------------------------------------------------------------------------


class TagBase(SQLModel):
    name: str = Field(min_length=1, max_length=100, unique=True, index=True)


class TagCreate(TagBase):
    pass


class TagUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class Tag(TagBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    articles: list[Article] = Relationship(
        back_populates="tags", link_model=ArticleTag
    )


class TagPublic(TagBase):
    id: int


class TagsPublic(SQLModel):
    data: list[TagPublic]
    count: int


# ---------------------------------------------------------------------------
# Article Models
# ---------------------------------------------------------------------------


class ArticleBase(SQLModel):
    headline: str = Field(min_length=1, max_length=500)
    slug: str = Field(min_length=1, max_length=550, unique=True, index=True)
    excerpt: str | None = Field(default=None, max_length=1000)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    status: ArticleStatus = Field(default=ArticleStatus.draft)
    views_count: int = Field(default=0)


class ArticleCreate(SQLModel):
    headline: str = Field(min_length=1, max_length=500)
    slug: str = Field(max_length=550)
    excerpt: str | None = Field(default=None, max_length=1000)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    body: str | None = None
    category_id: int | None = None
    status: ArticleStatus = Field(default=ArticleStatus.draft)
    tag_ids: list[int] = Field(default_factory=list)


class ArticleUpdate(SQLModel):
    headline: str | None = Field(default=None, min_length=1, max_length=500)
    slug: str | None = Field(default=None, min_length=1, max_length=550)
    excerpt: str | None = Field(default=None, max_length=1000)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    body: str | None = None
    category_id: int | None = None
    status: ArticleStatus | None = None
    tag_ids: list[int] | None = None


class Article(ArticleBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    body: str | None = Field(default=None, sa_type=Text)
    author_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    category_id: int | None = Field(
        default=None, foreign_key="category.id", ondelete="SET NULL"
    )
    date_published: datetime | None = Field(  # type: ignore[call-overload]
        default=None, sa_type=DateTime(timezone=True)
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    author: User | None = Relationship(back_populates="articles")
    category: Category | None = Relationship(back_populates="articles")
    tags: list[Tag] = Relationship(
        back_populates="articles", link_model=ArticleTag
    )
    media: list[Media] = Relationship(
        back_populates="article", cascade_delete=True
    )
    comments: list[Comment] = Relationship(
        back_populates="article", cascade_delete=True
    )


class ArticlePublic(ArticleBase):
    id: uuid.UUID
    body: str | None = None
    author_id: uuid.UUID
    category_id: int | None = None
    date_published: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ArticleDetailPublic(ArticlePublic):
    author: UserPublic | None = None
    category: CategoryPublic | None = None
    tags: list[TagPublic] = Field(default_factory=list)


class ArticlesPublic(SQLModel):
    data: list[ArticlePublic]
    count: int


# ---------------------------------------------------------------------------
# Media Models
# ---------------------------------------------------------------------------


class MediaBase(SQLModel):
    file_url: str = Field(max_length=2048)
    file_type: str = Field(max_length=50)


class MediaCreate(MediaBase):
    article_id: uuid.UUID | None = None


class Media(MediaBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    article_id: uuid.UUID | None = Field(
        default=None, foreign_key="article.id", ondelete="SET NULL"
    )
    uploaded_by: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    article: Article | None = Relationship(back_populates="media")
    uploaded_by_user: User | None = Relationship(back_populates="media")


class MediaPublic(MediaBase):
    id: uuid.UUID
    article_id: uuid.UUID | None = None
    uploaded_by: uuid.UUID
    created_at: datetime | None = None


class MediasPublic(SQLModel):
    data: list[MediaPublic]
    count: int


# ---------------------------------------------------------------------------
# Comment Models
# ---------------------------------------------------------------------------


class CommentBase(SQLModel):
    guest_name: str = Field(min_length=1, max_length=150)
    guest_email: EmailStr = Field(max_length=255)
    body: str = Field(min_length=1, max_length=5000, sa_type=Text)


class CommentCreate(CommentBase):
    article_id: uuid.UUID


class CommentUpdate(SQLModel):
    status: CommentStatus


class Comment(CommentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    article_id: uuid.UUID = Field(foreign_key="article.id", ondelete="CASCADE")
    status: CommentStatus = Field(default=CommentStatus.pending)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    article: Article | None = Relationship(back_populates="comments")


class CommentPublic(CommentBase):
    id: int
    article_id: uuid.UUID
    status: CommentStatus
    created_at: datetime | None = None
    article_headline: str | None = None
    article_slug: str | None = None


class CommentsPublic(SQLModel):
    data: list[CommentPublic]
    count: int


# ---------------------------------------------------------------------------
# ClubMember Models
# ---------------------------------------------------------------------------


class ClubMemberBase(SQLModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    position: str | None = Field(default=None, max_length=100)
    position_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=100)
    photo_url: str | None = Field(default=None, max_length=2048)
    is_officer: bool = Field(default=False)
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)


class ClubMemberCreate(ClubMemberBase):
    pass


class ClubMemberUpdate(SQLModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    position: str | None = Field(default=None, max_length=100)
    position_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=100)
    photo_url: str | None = Field(default=None, max_length=2048)
    is_officer: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ClubMember(ClubMemberBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ClubMemberPublic(ClubMemberBase):
    id: int
    created_at: datetime | None = None


class ClubMembersPublic(SQLModel):
    data: list[ClubMemberPublic]
    count: int


# ---------------------------------------------------------------------------
# ContactMessage Models
# ---------------------------------------------------------------------------


class ContactMessageCreate(SQLModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr = Field(max_length=255)
    subject: str | None = Field(default=None, max_length=500)
    message: str = Field(min_length=1, max_length=10000)
    captcha_token: str | None = Field(default=None, max_length=4096)


class ContactMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    email: str = Field(max_length=255)
    subject: str | None = Field(default=None, max_length=500)
    message: str = Field(sa_type=Text)
    status: ContactMessageStatus = Field(default=ContactMessageStatus.new)
    sent_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ContactMessagePublic(SQLModel):
    id: int
    name: str
    email: str
    subject: str | None = None
    message: str
    status: ContactMessageStatus
    sent_at: datetime | None = None


class ContactMessagesPublic(SQLModel):
    data: list[ContactMessagePublic]
    count: int


# ---------------------------------------------------------------------------
# SiteSetting Models
# ---------------------------------------------------------------------------


class SiteSettingBase(SQLModel):
    key: str = Field(max_length=100, primary_key=True)
    value: str | None = Field(default=None, sa_type=Text)


class SiteSettingCreate(SiteSettingBase):
    pass


class SiteSetting(SiteSettingBase, table=True):
    pass


class SiteSettingPublic(SiteSettingBase):
    pass


class SiteSettingsPublic(SQLModel):
    data: list[SiteSettingPublic]
    count: int


# ---------------------------------------------------------------------------
# Shared / Auth Models
# ---------------------------------------------------------------------------


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None
    jti: str | None = None
    tv: int | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
    captcha_token: str | None = Field(default=None, max_length=4096)


class PasswordRecoveryRequest(SQLModel):
    captcha_token: str | None = Field(default=None, max_length=4096)


# ---------------------------------------------------------------------------
# Developer Audit Log (persistent audit/event trail)
# ---------------------------------------------------------------------------


class AuditLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
    # Stable event/action name, e.g. "user.role_changed".
    event: str = Field(max_length=100, index=True)
    # INFO / WARN / ERROR severity.
    severity: str = Field(default="INFO", max_length=10)
    # Classification namespace, e.g. "auth", "user", "article", "media",
    # "developer", "system". Mirrors the Developer UI "component" column.
    component: str = Field(default="system", max_length=50)
    actor_user_id: uuid.UUID | None = None
    actor_email: str | None = Field(default=None, max_length=255)
    actor_role: str | None = Field(default=None, max_length=50)
    actor_is_developer: bool = False
    # Target entity type + safe id when relevant.
    target_type: str | None = Field(default=None, max_length=50)
    target_id: str | None = Field(default=None, max_length=64)
    success: bool = True
    # Public, redacted human-readable summary. Never contains secrets.
    message: str = Field(max_length=2048)


# ---------------------------------------------------------------------------
# Token Revocation (JWT logout / per-jti denylist)
# ---------------------------------------------------------------------------


class TokenRevocation(SQLModel, table=True):
    """Per-jti denylist for access tokens.

    Rows are written on ``POST /auth/logout`` and pruned on application
    startup. The hot path is filtered by ``expires_at > now()`` so the table
    only contains entries that are still authoritative.

    Revocation is layered:

    1. Per-user ``token_version`` (``User.token_version``) invalidates ALL
       sessions for a user in a single write, used on password change and
       password reset.
    2. Per-jti rows in this table invalidate a specific session, used on
       explicit logout.
    """

    jti: str = Field(primary_key=True, max_length=64)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    revoked_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    # When the underlying JWT expires. Hot path filters out rows where
    # ``expires_at <= now()``; ``prune_revocations`` removes them on startup.
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
    reason: str = Field(default="logout", max_length=50)
