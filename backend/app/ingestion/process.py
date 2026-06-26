import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Document, DocumentChunk
from app.db.session import async_session
from app.ingestion.chunker import chunk
from app.ingestion.parser import extract

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def _process_document(session: AsyncSession, doc: Document) -> int:
    path = Path(doc.file_path)
    if not path.exists():
        logger.warning("file not found, skipping: %s", path)
        return 0

    logger.info("parsing %s", path.name)
    text, has_tables = await asyncio.to_thread(extract, path)

    if not text.strip():
        logger.warning("no text extracted from %s", path.name)
        return 0

    chunks = chunk(text)
    logger.info("%d chunks from %s", len(chunks), path.name)

    for i, (content, token_count) in enumerate(chunks):
        session.add(
            DocumentChunk(
                document_id=doc.id,
                content=content,
                chunk_index=i,
                contient_tableaux=has_tables,
                token_count=token_count,
            )
        )

    await session.commit()
    return len(chunks)


async def process_all() -> None:
    async with async_session() as session:
        result = await session.execute(
            select(Document)
            .outerjoin(Document.chunks)
            .where(DocumentChunk.id.is_(None))
            .options(selectinload(Document.chunks))
        )
        docs = result.scalars().unique().all()

    logger.info("%d unprocessed documents", len(docs))
    total_chunks = 0

    for doc in docs:
        async with async_session() as session:
            n = await _process_document(session, doc)
            total_chunks += n

    logger.info("done — %d total chunks inserted", total_chunks)


if __name__ == "__main__":
    asyncio.run(process_all())
