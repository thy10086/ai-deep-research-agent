from uuid import UUID

import tiktoken
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk
from app.services.chunker import chunk_sections
from app.services.parser import parse_document
from app.services.embeddings import embedding_service
from app.services.storage import materialize_source

class DocumentNotFoundError(Exception):
    pass


class MissingSourceFileError(Exception):
    pass


tokenizer = tiktoken.get_encoding("cl100k_base")


async def process_document(
    session: AsyncSession,
    document_id: UUID,
) -> Document:
    document = await session.get(Document, document_id)

    if document is None:
        raise DocumentNotFoundError

    if document.source_uri is None:
        raise MissingSourceFileError

    document.status = "processing"
    await session.commit()

    try:
        async with materialize_source(document.source_uri) as source_path:
            if not source_path.is_file():
                raise MissingSourceFileError

            sections = await parse_document(
                source_path,
                document.content_type,
            )
            chunks = chunk_sections(sections)

        embeddings = await embedding_service.embed_texts(
            [chunk.content for chunk in chunks]
        )

        await session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id
            )
        )

        session.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk.content,
                    token_count=len(tokenizer.encode(chunk.content)),
                    embedding=embeddings[index],
                    attributes=chunk.metadata,
                )
                for index, chunk in enumerate(chunks)
            ]
        )

        document.status = "ready"
        await session.commit()
        await session.refresh(document)
        return document
    except Exception:
        await session.rollback()

        failed_document = await session.get(Document, document_id)
        if failed_document is not None:
            failed_document.status = "failed"
            await session.commit()

        raise
