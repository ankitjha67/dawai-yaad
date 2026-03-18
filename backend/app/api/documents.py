"""Documents API — file upload, list, download, PDF report generation."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document, DocType
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentOut
from app.services.family import check_edit_access, check_view_access
from app.services.report import generate_adherence_report
from app.services.storage import delete_file, get_presigned_url, upload_file
from app.utils.auth import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents & Reports"])


# ── Upload ───────────────────────────────────────────────────

@router.post("", response_model=DocumentOut, status_code=201, summary="Upload document")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    type: str = Form("other"),
    notes: Optional[str] = Form(None),
    report_date: Optional[date] = Form(None),
    for_user_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document (blood report, prescription, X-ray, etc.)

    Supports upload for self or for a family member/patient (with permission).
    """
    target_id = for_user_id or current_user.id
    if target_id != current_user.id:
        await check_edit_access(current_user, target_id, db)

    # Read file
    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    # Upload to MinIO
    object_name, file_size = upload_file(
        file_data=file_data,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        folder=f"users/{target_id}",
    )

    # Create DB record
    doc = Document(
        user_id=target_id,
        type=DocType(type) if type in DocType.__members__ else DocType.other,
        title=title or file.filename or "Untitled",
        file_url=object_name,
        file_size=file_size,
        uploaded_by=current_user.id,
        notes=notes,
        report_date=report_date,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    return DocumentOut(
        id=doc.id,
        user_id=doc.user_id,
        type=doc.type.value,
        title=doc.title,
        file_url=get_presigned_url(doc.file_url),
        file_size=doc.file_size,
        uploaded_by=doc.uploaded_by,
        uploaded_by_name=current_user.name,
        notes=doc.notes,
        report_date=doc.report_date,
        created_at=doc.created_at,
    )


# ── List / Get ───────────────────────────────────────────────

@router.get("", response_model=List[DocumentOut], summary="List documents")
async def list_documents(
    user_id: Optional[UUID] = None,
    type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents for a user. Defaults to own documents."""
    target_id = user_id or current_user.id
    if target_id != current_user.id:
        await check_view_access(current_user, target_id, db)

    query = select(Document).where(Document.user_id == target_id)
    if type:
        query = query.where(Document.type == type)
    query = query.order_by(Document.created_at.desc()).limit(limit)

    result = await db.execute(query)
    docs = result.scalars().all()

    out = []
    for doc in docs:
        uploader_result = await db.execute(select(User).where(User.id == doc.uploaded_by))
        uploader = uploader_result.scalar_one_or_none()

        out.append(DocumentOut(
            id=doc.id,
            user_id=doc.user_id,
            type=doc.type.value,
            title=doc.title,
            file_url=get_presigned_url(doc.file_url),
            file_size=doc.file_size,
            uploaded_by=doc.uploaded_by,
            uploaded_by_name=uploader.name if uploader else None,
            notes=doc.notes,
            report_date=doc.report_date,
            created_at=doc.created_at,
        ))
    return out


@router.get("/{doc_id}", response_model=DocumentOut, summary="Get document details")
async def get_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single document with presigned download URL."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await check_view_access(current_user, doc.user_id, db)

    uploader_result = await db.execute(select(User).where(User.id == doc.uploaded_by))
    uploader = uploader_result.scalar_one_or_none()

    return DocumentOut(
        id=doc.id,
        user_id=doc.user_id,
        type=doc.type.value,
        title=doc.title,
        file_url=get_presigned_url(doc.file_url),
        file_size=doc.file_size,
        uploaded_by=doc.uploaded_by,
        uploaded_by_name=uploader.name if uploader else None,
        notes=doc.notes,
        report_date=doc.report_date,
        created_at=doc.created_at,
    )


@router.delete("/{doc_id}", summary="Delete document")
async def delete_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document. Must be the uploader or have edit access."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await check_edit_access(current_user, doc.user_id, db)

    # Delete from storage
    delete_file(doc.file_url)

    # Delete DB record
    await db.delete(doc)
    return {"message": "Document deleted"}


# ── PDF Reports ──────────────────────────────────────────────

@router.get("/report/adherence", summary="Generate adherence report (PDF)")
async def adherence_report(
    user_id: Optional[UUID] = None,
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a medication adherence report as downloadable PDF.

    Includes: medication list, taken/missed/skipped counts, adherence %,
    recent health measurements.
    """
    target_id = user_id or current_user.id
    if target_id != current_user.id:
        await check_view_access(current_user, target_id, db)

    # Get user name
    user_result = await db.execute(select(User).where(User.id == target_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    pdf_bytes, filename = await generate_adherence_report(
        db=db,
        user_id=target_id,
        user_name=target_user.name,
        days=days,
    )

    # Determine content type
    content_type = "application/pdf" if pdf_bytes[:4] == b"%PDF" else "text/html"

    return Response(
        content=pdf_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
