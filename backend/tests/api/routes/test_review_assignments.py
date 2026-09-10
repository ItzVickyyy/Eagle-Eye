import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    Article,
    ArticleStatus,
    ReviewAssignment,
    ReviewAssignmentStatus,
    User,
    UserCreate,
    UserRole,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_create_assignment_as_admin(
    client: TestClient, db: Session
) -> None:
    """Admin can assign a reviewer to a pending article."""
    # Create admin user
    admin_email = random_email()
    admin_password = random_lower_string()
    admin_in = UserCreate(email=admin_email, password=admin_password, role=UserRole.admin)
    from app import crud
    admin = crud.create_user(session=db, user_create=admin_in)
    admin_headers = authentication_token_from_email(client=client, email=admin_email, db=db)

    # Create contributor (article author)
    contributor_email = random_email()
    contributor_password = random_lower_string()
    contributor_in = UserCreate(email=contributor_email, password=contributor_password, role=UserRole.contributor)
    contributor = crud.create_user(session=db, user_create=contributor_in)

    # Create reviewer (admin role)
    reviewer_email = random_email()
    reviewer_password = random_lower_string()
    reviewer_in = UserCreate(email=reviewer_email, password=reviewer_password, role=UserRole.admin)
    reviewer = crud.create_user(session=db, user_create=reviewer_in)

    # Create a pending article
    article = Article(
        headline="Test Article for Assignment",
        slug="test-article-for-assignment",
        body="Test body content",
        author_id=contributor.id,
        status=ArticleStatus.pending,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    # Assign reviewer
    r = client.post(
        f"{settings.API_V1_STR}/review-assignments/",
        headers=admin_headers,
        json={
            "article_id": str(article.id),
            "reviewer_id": str(reviewer.id),
            "notes": "Please review this article",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["article_id"] == str(article.id)
    assert data["reviewer_id"] == str(reviewer.id)
    assert data["assigned_by"] == str(admin.id)
    assert data["status"] == "active"


def test_contributor_cannot_create_assignment(
    client: TestClient, db: Session
) -> None:
    """Contributors cannot create review assignments."""
    contributor_email = random_email()
    contributor_password = random_lower_string()
    contributor_in = UserCreate(email=contributor_email, password=contributor_password, role=UserRole.contributor)
    from app import crud
    contributor = crud.create_user(session=db, user_create=contributor_in)
    contributor_headers = authentication_token_from_email(client=client, email=contributor_email, db=db)

    # Create a pending article
    article = Article(
        headline="Test Article",
        slug="test-article-contributor-assign",
        body="Test body",
        author_id=contributor.id,
        status=ArticleStatus.pending,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    # Try to assign (should fail)
    r = client.post(
        f"{settings.API_V1_STR}/review-assignments/",
        headers=contributor_headers,
        json={
            "article_id": str(article.id),
            "reviewer_id": str(contributor.id),
        },
    )
    assert r.status_code in (401, 403)


def test_cannot_assign_self_as_reviewer(
    client: TestClient, db: Session
) -> None:
    """Admin cannot assign themselves as reviewer for their own article."""
    admin_email = random_email()
    admin_password = random_lower_string()
    admin_in = UserCreate(email=admin_email, password=admin_password, role=UserRole.admin)
    from app import crud
    admin = crud.create_user(session=db, user_create=admin_in)
    admin_headers = authentication_token_from_email(client=client, email=admin_email, db=db)

    # Create article by admin
    article = Article(
        headline="Admin's Article",
        slug="admin-article-self-assign",
        body="Test body",
        author_id=admin.id,
        status=ArticleStatus.pending,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    # Try to assign self (should fail)
    r = client.post(
        f"{settings.API_V1_STR}/review-assignments/",
        headers=admin_headers,
        json={
            "article_id": str(article.id),
            "reviewer_id": str(admin.id),
        },
    )
    assert r.status_code == 400
    assert "author" in r.json()["detail"].lower()


def test_cannot_assign_nonexistent_article(
    client: TestClient, db: Session
) -> None:
    """Cannot assign reviewer to nonexistent article."""
    admin_email = random_email()
    admin_password = random_lower_string()
    admin_in = UserCreate(email=admin_email, password=admin_password, role=UserRole.admin)
    from app import crud
    admin = crud.create_user(session=db, user_create=admin_in)
    admin_headers = authentication_token_from_email(client=client, email=admin_email, db=db)

    reviewer_email = random_email()
    reviewer_password = random_lower_string()
    reviewer_in = UserCreate(email=reviewer_email, password=reviewer_password, role=UserRole.admin)
    reviewer = crud.create_user(session=db, user_create=reviewer_in)

    r = client.post(
        f"{settings.API_V1_STR}/review-assignments/",
        headers=admin_headers,
        json={
            "article_id": str(uuid.uuid4()),
            "reviewer_id": str(reviewer.id),
        },
    )
    assert r.status_code == 404


def test_cannot_assign_duplicate_active(
    client: TestClient, db: Session
) -> None:
    """Cannot create duplicate active assignment."""
    admin_email = random_email()
    admin_password = random_lower_string()
    admin_in = UserCreate(email=admin_email, password=admin_password, role=UserRole.admin)
    from app import crud
    admin = crud.create_user(session=db, user_create=admin_in)
    admin_headers = authentication_token_from_email(client=client, email=admin_email, db=db)

    contributor_email = random_email()
    contributor_password = random_lower_string()
    contributor_in = UserCreate(email=contributor_email, password=contributor_password, role=UserRole.contributor)
    contributor = crud.create_user(session=db, user_create=contributor_in)

    reviewer_email = random_email()
    reviewer_password = random_lower_string()
    reviewer_in = UserCreate(email=reviewer_email, password=reviewer_password, role=UserRole.admin)
    reviewer = crud.create_user(session=db, user_create=reviewer_in)

    article = Article(
        headline="Duplicate Test Article",
        slug="duplicate-test-article",
        body="Test body",
        author_id=contributor.id,
        status=ArticleStatus.pending,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    # First assignment succeeds
    r1 = client.post(
        f"{settings.API_V1_STR}/review-assignments/",
        headers=admin_headers,
        json={
            "article_id": str(article.id),
            "reviewer_id": str(reviewer.id),
        },
    )
    assert r1.status_code == 200

    # Duplicate assignment fails
    r2 = client.post(
        f"{settings.API_V1_STR}/review-assignments/",
        headers=admin_headers,
        json={
            "article_id": str(article.id),
            "reviewer_id": str(reviewer.id),
        },
    )
    assert r2.status_code == 409


def test_list_assignments_for_article(
    client: TestClient, db: Session
) -> None:
    """List assignments for an article."""
    admin_email = random_email()
    admin_password = random_lower_string()
    admin_in = UserCreate(email=admin_email, password=admin_password, role=UserRole.admin)
    from app import crud
    admin = crud.create_user(session=db, user_create=admin_in)
    admin_headers = authentication_token_from_email(client=client, email=admin_email, db=db)

    contributor_email = random_email()
    contributor_password = random_lower_string()
    contributor_in = UserCreate(email=contributor_email, password=contributor_password, role=UserRole.contributor)
    contributor = crud.create_user(session=db, user_create=contributor_in)

    reviewer_email = random_email()
    reviewer_password = random_lower_string()
    reviewer_in = UserCreate(email=reviewer_email, password=reviewer_password, role=UserRole.admin)
    reviewer = crud.create_user(session=db, user_create=reviewer_in)

    article = Article(
        headline="List Test Article",
        slug="list-test-article",
        body="Test body",
        author_id=contributor.id,
        status=ArticleStatus.pending,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    # Create assignment
    client.post(
        f"{settings.API_V1_STR}/review-assignments/",
        headers=admin_headers,
        json={
            "article_id": str(article.id),
            "reviewer_id": str(reviewer.id),
        },
    )

    # List assignments
    r = client.get(
        f"{settings.API_V1_STR}/review-assignments/article/{article.id}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["data"][0]["reviewer_id"] == str(reviewer.id)


def test_remove_assignment(
    client: TestClient, db: Session
) -> None:
    """Admin can remove an assignment."""
    admin_email = random_email()
    admin_password = random_lower_string()
    admin_in = UserCreate(email=admin_email, password=admin_password, role=UserRole.admin)
    from app import crud
    admin = crud.create_user(session=db, user_create=admin_in)
    admin_headers = authentication_token_from_email(client=client, email=admin_email, db=db)

    contributor_email = random_email()
    contributor_password = random_lower_string()
    contributor_in = UserCreate(email=contributor_email, password=contributor_password, role=UserRole.contributor)
    contributor = crud.create_user(session=db, user_create=contributor_in)

    reviewer_email = random_email()
    reviewer_password = random_lower_string()
    reviewer_in = UserCreate(email=reviewer_email, password=reviewer_password, role=UserRole.admin)
    reviewer = crud.create_user(session=db, user_create=reviewer_in)

    article = Article(
        headline="Remove Test Article",
        slug="remove-test-article",
        body="Test body",
        author_id=contributor.id,
        status=ArticleStatus.pending,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    # Create assignment
    r_create = client.post(
        f"{settings.API_V1_STR}/review-assignments/",
        headers=admin_headers,
        json={
            "article_id": str(article.id),
            "reviewer_id": str(reviewer.id),
        },
    )
    assignment_id = r_create.json()["id"]

    # Remove assignment
    r = client.delete(
        f"{settings.API_V1_STR}/review-assignments/{assignment_id}",
        headers=admin_headers,
    )
    assert r.status_code == 200

    # Verify removed
    r_list = client.get(
        f"{settings.API_V1_STR}/review-assignments/article/{article.id}",
        headers=admin_headers,
    )
    assert r_list.json()["count"] == 0


def test_reviewer_can_see_my_assignments(
    client: TestClient, db: Session
) -> None:
    """Reviewer can see their own assignments."""
    admin_email = random_email()
    admin_password = random_lower_string()
    admin_in = UserCreate(email=admin_email, password=admin_password, role=UserRole.admin)
    from app import crud
    admin = crud.create_user(session=db, user_create=admin_in)
    admin_headers = authentication_token_from_email(client=client, email=admin_email, db=db)

    contributor_email = random_email()
    contributor_password = random_lower_string()
    contributor_in = UserCreate(email=contributor_email, password=contributor_password, role=UserRole.contributor)
    contributor = crud.create_user(session=db, user_create=contributor_in)

    reviewer_email = random_email()
    reviewer_password = random_lower_string()
    reviewer_in = UserCreate(email=reviewer_email, password=reviewer_password, role=UserRole.admin)
    reviewer = crud.create_user(session=db, user_create=reviewer_in)
    reviewer_headers = authentication_token_from_email(client=client, email=reviewer_email, db=db)

    article = Article(
        headline="My Assignments Article",
        slug="my-assignments-article",
        body="Test body",
        author_id=contributor.id,
        status=ArticleStatus.pending,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    # Create assignment
    client.post(
        f"{settings.API_V1_STR}/review-assignments/",
        headers=admin_headers,
        json={
            "article_id": str(article.id),
            "reviewer_id": str(reviewer.id),
        },
    )

    # Reviewer sees their assignment
    r = client.get(
        f"{settings.API_V1_STR}/review-assignments/my-assignments",
        headers=reviewer_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["data"][0]["article_id"] == str(article.id)
