from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import AdminUser, SessionDep, SuperAdminUser
from app.models import (
    CategoriesPublic,
    Category,
    CategoryCreate,
    CategoryPublic,
    CategoryUpdate,
    Message,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=CategoriesPublic)
def read_categories(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    List all categories (public).
    """
    statement = select(Category).order_by(col(Category.name).asc())
    count = session.exec(select(func.count()).select_from(Category)).one()
    categories = session.exec(statement.offset(skip).limit(limit)).all()
    categories_public = [CategoryPublic.model_validate(c) for c in categories]
    return CategoriesPublic(data=categories_public, count=count)


@router.get("/{id_or_slug}", response_model=CategoryPublic)
def read_category(id_or_slug: str, session: SessionDep) -> Any:
    """
    Get category by ID or slug.
    """
    if id_or_slug.isdigit():
        category = session.get(Category, int(id_or_slug))
    else:
        category = session.exec(
            select(Category).where(Category.slug == id_or_slug)
        ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/", response_model=CategoryPublic)
def create_category(
    *,
    session: SessionDep,
    category_in: CategoryCreate,
    _current_user: AdminUser,
) -> Any:
    """
    Create category (Admin / Super Admin).
    """
    existing = session.exec(
        select(Category).where(Category.slug == category_in.slug)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this slug already exists")

    category = Category.model_validate(category_in)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.patch("/{id}", response_model=CategoryPublic)
def update_category(
    *,
    session: SessionDep,
    id: int,
    category_in: CategoryUpdate,
    _current_user: AdminUser,
) -> Any:
    """
    Update category (Admin / Super Admin).
    """
    category = session.get(Category, id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = category_in.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"]:
        existing = session.exec(
            select(Category).where(
                Category.slug == update_data["slug"], Category.id != id
            )
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Category slug already in use")

    category.sqlmodel_update(update_data)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.delete("/{id}", response_model=Message)
def delete_category(
    *,
    session: SessionDep,
    id: int,
    _current_user: SuperAdminUser,
) -> Message:
    """
    Delete category (Super Admin).
    """
    category = session.get(Category, id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    session.delete(category)
    session.commit()
    return Message(message="Category deleted successfully")
