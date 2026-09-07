from datetime import UTC, datetime

from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import (
    Article,
    ArticleStatus,
    ArticleTag,
    Category,
    ClubMember,
    SiteSetting,
    Tag,
    User,
    UserCreate,
    UserRole,
)

db_url = str(settings.DATABASE_URL)
if db_url.startswith("sqlite"):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True)


def init_db(session: Session) -> None:
    # 1. Superuser
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            role=UserRole.super_admin,
            full_name="Eagle Eye Adviser",
            department="Editorial",
            position_title="Club Adviser",
        )
        user = crud.create_user(session=session, user_create=user_in)

    # 2. Categories
    default_categories = [
        {"name": "News", "slug": "news", "description": "School announcements, campus happenings, and administrative updates."},
        {"name": "Academics", "slug": "academics", "description": "Classroom achievements, honors, science fairs, and academic competitions."},
        {"name": "Sports", "slug": "sports", "description": "Game recaps, athlete highlights, tournaments, and intramurals."},
        {"name": "Events", "slug": "events", "description": "School festivals, club activities, celebrations, and cultural presentations."},
    ]
    created_categories: dict[str, Category] = {}
    for cat_data in default_categories:
        existing = session.exec(
            select(Category).where(Category.slug == cat_data["slug"])
        ).first()
        if not existing:
            cat_obj = Category(**cat_data)
            session.add(cat_obj)
            session.flush()
            session.refresh(cat_obj)
            created_categories[cat_data["slug"]] = cat_obj
        else:
            created_categories[cat_data["slug"]] = existing

    # 3. Tags
    sample_tags = ["Campus", "CDLB", "Intramurals", "Editorial", "Student Life", "Achievement"]
    for t_name in sample_tags:
        if not session.exec(select(Tag).where(Tag.name == t_name)).first():
            session.add(Tag(name=t_name))

    # 4. Site Settings
    default_settings = [
        ("site_name", "Eagle Eye"),
        ("site_tagline", "Official Publication of CDLB Media Club"),
        ("school_name", "Colegio de Los Baños"),
        ("contact_email", "mediaclub@cdlb.edu.ph"),
        ("facebook_url", "https://facebook.com/cdlbmediaclub"),
    ]
    for key, val in default_settings:
        if not session.get(SiteSetting, key):
            session.add(SiteSetting(key=key, value=val))

    # 5. Club Members
    existing_members = session.exec(select(ClubMember)).first()
    if not existing_members:
        members_data = [
            ClubMember(
                first_name="Maria",
                last_name="Santos",
                position="Adviser",
                position_title="Lead Club Adviser",
                department="Editorial",
                is_officer=True,
                sort_order=1,
                photo_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&auto=format&fit=crop&q=80",
            ),
            ClubMember(
                first_name="Carlos",
                last_name="Reyes",
                position="Editor-in-Chief",
                position_title="Editor-in-Chief",
                department="Editorial",
                is_officer=True,
                sort_order=2,
                photo_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&auto=format&fit=crop&q=80",
            ),
            ClubMember(
                first_name="Angela",
                last_name="Cruz",
                position="Associate Editor",
                position_title="Associate Editor",
                department="Editorial",
                is_officer=True,
                sort_order=3,
                photo_url="https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&auto=format&fit=crop&q=80",
            ),
            ClubMember(
                first_name="Joshua",
                last_name="Dumagco",
                position="Head of Multimedia",
                position_title="Multimedia Lead",
                department="Multimedia",
                is_officer=True,
                sort_order=4,
                photo_url="https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&auto=format&fit=crop&q=80",
            ),
        ]
        for m in members_data:
            session.add(m)

    # 6. Sample Articles
    existing_articles = session.exec(select(Article)).first()
    if not existing_articles and user:
        now = datetime.now(UTC)
        news_cat = created_categories.get("news")
        sports_cat = created_categories.get("sports")
        acads_cat = created_categories.get("academics")
        events_cat = created_categories.get("events")

        sample_articles = [
            Article(
                headline="CDLB Welcomes Academic Year with Expanded Campus Facilities",
                slug="cdlb-welcomes-academic-year-expanded-facilities",
                excerpt="Colegio de Los Baños opens newly refurbished science laboratories and multimedia studios for senior high school students.",
                body="<p>Colegio de Los Baños opened its doors to students this semester with newly upgraded science laboratories, state-of-the-art multimedia facilities, and modernized classrooms.</p><p>The initiative aims to provide students with hands-on technical training, particularly for HUMSS, STEM, and ABM strands.</p>",
                cover_image_url="https://images.unsplash.com/photo-1562774053-701939374585?w=800&auto=format&fit=crop&q=80",
                author_id=user.id,
                category_id=news_cat.id if news_cat else None,
                status=ArticleStatus.published,
                date_published=now,
                views_count=42,
            ),
            Article(
                headline="Eagle Soars: CDLB Basketball Team Secures Division Championship",
                slug="eagle-soars-cdlb-basketball-division-championship",
                excerpt="In a thrilling fourth-quarter comeback, the CDLB Eagles clinched victory at the Laguna Interscholastic Athletic Meet.",
                body="<p>The CDLB Eagles displayed exceptional grit and teamwork during the championship game against regional contenders.</p><p>Team captain Marco Del Rosario led the offense with 28 points, sealing the win with a decisive buzzer-beater.</p>",
                cover_image_url="https://images.unsplash.com/photo-1546519638-68e109498ffc?w=800&auto=format&fit=crop&q=80",
                author_id=user.id,
                category_id=sports_cat.id if sports_cat else None,
                status=ArticleStatus.published,
                date_published=now,
                views_count=108,
            ),
            Article(
                headline="Students Excel at Regional Science & Journalism Conclave",
                slug="students-excel-regional-science-journalism-conclave",
                excerpt="CDLB delegates brought home top honors in investigatory project presentations and editorial writing.",
                body="<p>CDLB students demonstrated academic rigor and creative journalism skills at the annual Regional Interschool Conclave.</p><p>Special recognition was awarded to the Media Club editorial staff for outstanding feature reporting.</p>",
                cover_image_url="https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?w=800&auto=format&fit=crop&q=80",
                author_id=user.id,
                category_id=acads_cat.id if acads_cat else None,
                status=ArticleStatus.published,
                date_published=now,
                views_count=77,
            ),
            Article(
                headline="Annual Cultural Festival Showcases Student Talent and Heritage",
                slug="annual-cultural-festival-showcases-student-talent",
                excerpt="Performances, art exhibitions, and music highlighted this year's vibrant CDLB Foundation Week festivities.",
                body="<p>Foundation Week concluded with breathtaking dance routines, live acoustic sets, and student-curated art displays celebrating Filipino cultural heritage.</p>",
                cover_image_url="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800&auto=format&fit=crop&q=80",
                author_id=user.id,
                category_id=events_cat.id if events_cat else None,
                status=ArticleStatus.published,
                date_published=now,
                views_count=65,
            ),
        ]
        for a in sample_articles:
            session.add(a)

        # D3 remediation: attach a few sample tags to the seeded articles so
        # the public list/detail responses show non-empty `tags` arrays on
        # first boot. Only attaches tags to articles that don't already have
        # any (idempotent re-runs of init_db).
        session.flush()
        if not session.exec(select(ArticleTag)).first():
            tag_lookup = {
                t.name: t
                for t in session.exec(select(Tag)).all()
                if t.id is not None
            }
            article_tag_map: list[tuple[Article, list[str]]] = [
                (sample_articles[0], ["Campus", "Editorial"]),
                (sample_articles[1], ["Intramurals", "Achievement"]),
                (sample_articles[2], ["CDLB", "Achievement"]),
                (sample_articles[3], ["Student Life", "CDLB"]),
            ]
            for article, tag_names in article_tag_map:
                for name in tag_names:
                    tag = tag_lookup.get(name)
                    if tag is not None:
                        session.add(ArticleTag(article_id=article.id, tag_id=tag.id))

    session.commit()
