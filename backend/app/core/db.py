from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import Category, User, UserCreate, UserRole

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


def init_db(session: Session) -> None:
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            role=UserRole.super_admin,
        )
        crud.create_user(session=session, user_create=user_in)

    default_categories = [
        {"name": "News", "slug": "news", "description": "School announcements, events, and campus happenings."},
        {"name": "Academics", "slug": "academics", "description": "Classroom milestones, honors, and academic competitions."},
        {"name": "Sports", "slug": "sports", "description": "Game recaps, athlete spotlights, and team standings."},
        {"name": "Events", "slug": "events", "description": "School programs, club activities, and community events."},
    ]
    for cat_data in default_categories:
        existing = session.exec(
            select(Category).where(Category.slug == cat_data["slug"])
        ).first()
        if not existing:
            category = Category(**cat_data)
            session.add(category)
    session.commit()
