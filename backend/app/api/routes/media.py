import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlmodel import col, func, select

from app.api.deps import AdminUser, CurrentUser, SessionDep, is_admin_or_above
from app.models import (
    Media,
    MediaCreate,
    MediaPublic,
    MediasPublic,
    Message,
)

router = APIRouter(prefix="/media", tags=["media"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_model=MediasPublic)
def read_media_items(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    List uploaded media files.
    """
    statement = select(Media).order_by(col(Media.created_at).desc())
    count = session.exec(select(func.count()).select_from(Media)).one()
    media_list = session.exec(statement.offset(skip).limit(limit)).all()
    media_public = [MediaPublic.model_validate(m) for m in media_list]
    return MediasPublic(data=media_public, count=count)


@router.post("/register", response_model=MediaPublic)
def register_media(
    *,
    session: SessionDep,
    media_in: MediaCreate,
    current_user: CurrentUser,
) -> Any:
    """
    Register a media entry (e.g. from cloud storage URL like Cloudinary or Supabase).
    """
    media = Media(
        file_url=media_in.file_url,
        file_type=media_in.file_type,
        article_id=media_in.article_id,
        uploaded_by=current_user.id,
    )
    session.add(media)
    session.commit()
    session.refresh(media)
    return media


@router.post("/upload", response_model=MediaPublic)
async def upload_file(
    *,
    session: SessionDep,
    file: UploadFile = File(...),
    current_user: CurrentUser,
) -> Any:
    """
    Upload an image or video file.
    """
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Invalid file type")

    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4", "video/webm"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not supported. Use JPG, PNG, WEBP, GIF, or MP4.")

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    unique_filename = f"{uuid.uuid4()}{ext}"
    target_path = UPLOAD_DIR / unique_filename

    content = await file.read()
    target_path.write_bytes(content)

    file_url = f"/uploads/{unique_filename}"
    file_type = "image" if file.content_type.startswith("image") else "video"

    media = Media(
        file_url=file_url,
        file_type=file_type,
        uploaded_by=current_user.id,
    )
    session.add(media)
    session.commit()
    session.refresh(media)
    return media


@router.delete("/{id}", response_model=Message)
def delete_media(
    *,
    session: SessionDep,
    id: uuid.UUID,
    current_user: CurrentUser,
) -> Message:
    """
    Delete media record.
    Uploader can delete their own media. Admin / Super Admin can delete any media.
    """
    media = session.get(Media, id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    if not is_admin_or_above(current_user) and media.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this media item",
        )
    session.delete(media)
    session.commit()
    return Message(message="Media deleted successfully")
