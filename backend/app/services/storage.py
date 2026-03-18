"""MinIO storage service — S3-compatible file upload/download/presigned URLs.

Gracefully degrades when MinIO is not reachable (dev mode):
returns mock URLs for testing.
"""

import io
import logging
from typing import Optional
from uuid import uuid4

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_minio_client = None
_minio_available = False


def _init_minio() -> bool:
    """Lazy-initialize MinIO client. Returns True on success."""
    global _minio_client, _minio_available

    if _minio_client is not None:
        return _minio_available

    try:
        from minio import Minio

        _minio_client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_user,
            secret_key=settings.minio_pass,
            secure=settings.minio_secure,
        )

        # Ensure bucket exists
        if not _minio_client.bucket_exists(settings.minio_bucket):
            _minio_client.make_bucket(settings.minio_bucket)
            logger.info(f"Created MinIO bucket: {settings.minio_bucket}")

        _minio_available = True
        logger.info("MinIO storage initialized successfully")
        return True

    except Exception as e:
        logger.warning(f"MinIO initialization failed: {e}. Using mock URLs.")
        _minio_client = False  # Mark as attempted
        _minio_available = False
        return False


def upload_file(
    file_data: bytes,
    filename: str,
    content_type: str = "application/octet-stream",
    folder: str = "documents",
) -> tuple[str, int]:
    """Upload a file to MinIO.

    Args:
        file_data: Raw file bytes.
        filename: Original filename.
        content_type: MIME type.
        folder: Storage folder prefix.

    Returns:
        Tuple of (object_name, file_size).
    """
    # Generate unique object name
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    object_name = f"{folder}/{uuid4().hex}.{ext}"
    file_size = len(file_data)

    _init_minio()

    if not _minio_available:
        logger.info(f"[DEV UPLOAD] {object_name} ({file_size} bytes)")
        return object_name, file_size

    try:
        from minio import Minio

        _minio_client.put_object(
            bucket_name=settings.minio_bucket,
            object_name=object_name,
            data=io.BytesIO(file_data),
            length=file_size,
            content_type=content_type,
        )
        logger.info(f"Uploaded {object_name} ({file_size} bytes)")
        return object_name, file_size

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise


def get_presigned_url(object_name: str, expires_hours: int = 24) -> str:
    """Get a presigned download URL for an object.

    Args:
        object_name: Object path in MinIO.
        expires_hours: URL validity in hours.

    Returns:
        Presigned URL string.
    """
    _init_minio()

    if not _minio_available:
        scheme = "https" if settings.minio_secure else "http"
        return f"{scheme}://{settings.minio_endpoint}/{settings.minio_bucket}/{object_name}"

    try:
        from datetime import timedelta

        url = _minio_client.presigned_get_object(
            bucket_name=settings.minio_bucket,
            object_name=object_name,
            expires=timedelta(hours=expires_hours),
        )
        return url

    except Exception as e:
        logger.error(f"Presigned URL failed: {e}")
        scheme = "https" if settings.minio_secure else "http"
        return f"{scheme}://{settings.minio_endpoint}/{settings.minio_bucket}/{object_name}"


def delete_file(object_name: str) -> bool:
    """Delete a file from MinIO."""
    _init_minio()

    if not _minio_available:
        logger.info(f"[DEV DELETE] {object_name}")
        return True

    try:
        _minio_client.remove_object(settings.minio_bucket, object_name)
        return True
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return False
