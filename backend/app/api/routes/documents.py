from typing import Annotated
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.schemas.document import DocumentResponse
from pathlib import Path

from app.services.storage import (
    EmptyFileError,
    FileTooLargeError,
    save_upload,
)

from app.services.processor import (
    DocumentNotFoundError,
    MissingSourceFileError,
    process_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024


CONTENT_TYPE_SUFFIXES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
}


@router.get(
    "",
    response_model=list[DocumentResponse],
)
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[Document]:
    result = await session.scalars(
        select(Document).order_by(Document.created_at.desc())
    )
    return list(result)



@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A filename is required.",
        )

    if file.content_type not in CONTENT_TYPE_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, plain text, and Markdown files are supported.",
        )

    try:
        stored_upload = await save_upload(
            file=file,
            upload_dir=settings.upload_dir,
            suffix=CONTENT_TYPE_SUFFIXES[file.content_type],
            max_file_size=MAX_FILE_SIZE,
            chunk_size=READ_CHUNK_SIZE,
        )
    except FileTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="The file exceeds the 10 MB limit.",
        ) from error
    except EmptyFileError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        ) from error

    existing_document = await session.scalar(
        select(Document).where(Document.checksum == stored_upload.checksum)
    )
    if existing_document is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document has already been uploaded.",
        )

    document = Document(
        filename=file.filename,
        content_type=file.content_type,
        checksum=stored_upload.checksum,
        source_uri=stored_upload.path.as_posix(),
        status="pending",
    )
    session.add(document)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document has already been uploaded.",
        ) from error

    await session.refresh(document)
    return document


@router.post(
    "/{document_id}/process",
    response_model=DocumentResponse,
)
async def process_uploaded_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    try:
        return await process_document(session, document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from error
    except MissingSourceFileError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The document source file is unavailable.",
        ) from error


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    document = await session.get(Document, document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    source_path = (
        Path(document.source_uri)
        if document.source_uri
        else None
    )

    await session.delete(document)
    await session.commit()

    if source_path is not None:
        source_path.unlink(missing_ok=True)

    return Response(status_code=status.HTTP_204_NO_CONTENT)