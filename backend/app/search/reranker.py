import logging

from sentence_transformers import CrossEncoder

from app.config import settings
from app.search.hybrid import SearchResult

logger = logging.getLogger(__name__)

_model: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _model
    if _model is None:
        logger.info("loading reranker %s", settings.reranker_model)
        _model = CrossEncoder(settings.reranker_model)
    return _model


def rerank(query: str, results: list[SearchResult], top_k: int = 5) -> list[SearchResult]:
    if not results:
        return []

    reranker = get_reranker()
    pairs = [(query, r.content) for r in results]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(results, scores.tolist()), key=lambda x: x[1], reverse=True)

    reranked = []
    for result, score in ranked[:top_k]:
        result.score = score
        reranked.append(result)

    return reranked
