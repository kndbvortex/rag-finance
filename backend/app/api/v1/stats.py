from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import async_session

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("")
async def get_stats():
    async with async_session() as session:
        result = await session.execute(
            text(
                "SELECT "
                "(SELECT COUNT(*) FROM documents) AS documents, "
                "(SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL) AS chunks"
            )
        )
        row = result.one()
        return {"documents": row.documents, "chunks": row.chunks}
