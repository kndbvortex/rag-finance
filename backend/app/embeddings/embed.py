import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentChunk
from app.db.session import async_session
from app.embeddings.encoder import encode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 64


async def _fetch_batch(session: AsyncSession, offset: int) -> list[DocumentChunk]:
    result = await session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.embedding.is_(None))
        .order_by(DocumentChunk.id)
        .limit(BATCH_SIZE)
        .offset(offset)
    )
    return result.scalars().all()


async def embed_all() -> None:
    async with async_session() as session:
        total = await session.scalar(
            select(DocumentChunk.id)
            .where(DocumentChunk.embedding.is_(None))
            .with_only_columns(DocumentChunk.id)
        )

    # count unembedded chunks
    async with async_session() as session:
        from sqlalchemy import func
        count = await session.scalar(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.embedding.is_(None))
        )

    logger.info("%d chunks to embed", count)

    offset = 0
    embedded = 0

    while True:
        async with async_session() as session:
            batch = await _fetch_batch(session, 0)  # always offset 0 — processed rows drop out
            if not batch:
                break

            ids = [c.id for c in batch]
            texts = [c.content for c in batch]

        vectors = await asyncio.to_thread(encode, texts)

        async with async_session() as session:
            for chunk_id, vector in zip(ids, vectors):
                await session.execute(
                    update(DocumentChunk)
                    .where(DocumentChunk.id == chunk_id)
                    .values(embedding=vector)
                )
            await session.commit()

        embedded += len(batch)
        logger.info("embedded %d / %d", embedded, count)

    logger.info("done")


if __name__ == "__main__":
    asyncio.run(embed_all())
