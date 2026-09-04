import os
import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep, is_admin_or_above
from app.core.audit import write_audit_log
from app.core.config import settings
from app.core.storage import get_storage
from app.models import (
    Media,
    MediaCreate,
    MediaPublic,
    MediasPublic,
    Message,
)

router = APIRouter(prefix="/media", tags=["media"])

storage = get_storage(settings.MEDIA_STORAGE_BACKEND, settings.MEDIA_STORAGE_LOCAL_DIR)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB

ALLOWED_MIME_TYPES: dict[str, list[str]] = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "image/gif": [".gif"],
    "video/mp4": [".mp4"],
    "video/webm": [".webm"],
}


@router.get("/", response_model=MediasPublic)
def read_media_items(
    session: SessionDep,
    _current_user: CurrentUser,
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
    Upload an image or video file with strict MIME and extension validation.
    """
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Invalid file type")

    content_type = file.content_type.lower()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="File type not supported. Use JPG, PNG, WEBP, GIF, or MP4.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File size exceeds maximum allowed limit of 15MB.",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    # Validate extension against allowed extensions for this MIME type
    raw_ext = os.path.splitext(file.filename or "")[1].lower()
    valid_extensions = ALLOWED_MIME_TYPES[content_type]
    ext = raw_ext if raw_ext in valid_extensions else valid_extensions[0]

    unique_filename = f"{uuid.uuid4().hex}{ext}"

    # The storage key is server-generated. The active backend keeps physical
    # persistence and URL generation behind this security boundary.
    file_url = storage.save(unique_filename, content)

    file_type = "image" if content_type.startswith("image") else "video"

    media = Media(
        file_url=file_url,
        file_type=file_type,
        uploaded_by=current_user.id,
    )
    session.add(media)
    session.commit()
    session.refresh(media)
    write_audit_log(
        session=session,
        event="media.uploaded",
        component="media",
        actor=current_user,
        target_type="media",
        target_id=str(media.id),
        success=True,
        message=f"Media uploaded (type={file_type})",
    )
    session.commit()
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
    storage.delete(media.file_url)
    write_audit_log(
        session=session,
        event="media.deleted",
        component="media",
        actor=current_user,
        target_type="media",
        target_id=str(media.id),
        success=True,
        message="Media deleted",
    )
    session.delete(media)
    session.commit()
    return Message(message="Media deleted successfully")
