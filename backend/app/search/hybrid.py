import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.encoder import encode_query

logger = logging.getLogger(__name__)

RRF_K = 60
VECTOR_CANDIDATES = 50
BM25_CANDIDATES = 50


@dataclass
class SearchResult:
    chunk_id: int
    content: str
    score: float
    source_institution: str
    type_document: str
    annee_fiscale: int | None
    url_origine: str
    url_hash: str
    contient_tableaux: bool
    page_start: int | None
    page_end: int | None


async def _vector_search(session: AsyncSession, vector: list[float], k: int) -> list[tuple[int, int]]:
    vec_str = "[" + ",".join(map(str, vector)) + "]"
    result = await session.execute(
        text("""
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:vec AS vector)) AS rank
            FROM document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :k
        """),
        {"vec": vec_str, "k": k},
    )
    return [(row.id, row.rank) for row in result]


async def _bm25_search(session: AsyncSession, query: str, k: int) -> list[tuple[int, int]]:
    result = await session.execute(
        text("""
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY ts_rank_cd(content_tsv, q) DESC) AS rank
            FROM document_chunks,
                 websearch_to_tsquery('french', :query) q
            WHERE content_tsv @@ q
            ORDER BY ts_rank_cd(content_tsv, q) DESC
            LIMIT :k
        """),
        {"query": query, "k": k},
    )
    return [(row.id, row.rank) for row in result]


def _rrf(
    vector_results: list[tuple[int, int]],
    bm25_results: list[tuple[int, int]],
) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for chunk_id, rank in vector_results:
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    for chunk_id, rank in bm25_results:
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


async def _fetch(session: AsyncSession, chunk_ids: list[int]) -> list[SearchResult]:
    result = await session.execute(
        text("""
            SELECT dc.id, dc.content, dc.contient_tableaux, dc.page_start, dc.page_end,
                   d.source_institution, d.type_document, d.annee_fiscale, d.url, d.url_hash
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.id = ANY(:ids)
        """),
        {"ids": chunk_ids},
    )
    rows = {row.id: row for row in result}
    return [
        SearchResult(
            chunk_id=row.id,
            content=row.content,
            score=0.0,
            source_institution=row.source_institution,
            type_document=row.type_document,
            annee_fiscale=row.annee_fiscale,
            url_origine=row.url,
            url_hash=row.url_hash,
            contient_tableaux=row.contient_tableaux,
            page_start=row.page_start,
            page_end=row.page_end,
        )
        for cid in chunk_ids
        if (row := rows.get(cid))
    ]


async def hybrid_search(session: AsyncSession, query: str, top_k: int = 20) -> list[SearchResult]:
    query_vector = await asyncio.to_thread(encode_query, query)

    vector_results = await _vector_search(session, query_vector, VECTOR_CANDIDATES)
    bm25_results = await _bm25_search(session, query, BM25_CANDIDATES)

    logger.info("vector hits: %d  bm25 hits: %d", len(vector_results), len(bm25_results))

    fused = _rrf(vector_results, bm25_results)[:top_k]
    chunk_ids = [cid for cid, _ in fused]
    rrf_scores = {cid: score for cid, score in fused}

    results = await _fetch(session, chunk_ids)
    for r in results:
        r.score = rrf_scores.get(r.chunk_id, 0.0)

    results.sort(key=lambda r: r.score, reverse=True)
    return results
