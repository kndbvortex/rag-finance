import asyncio
import json
import threading
import time
from collections.abc import AsyncGenerator

import httpx

from app.config import settings
from app.db.session import async_session
from app.observability import _NoopLangfuse, _NoopSpan, get_langfuse
from app.rag.prompt import SYSTEM_PROMPT, build_user_message
from app.search.hybrid import SearchResult, hybrid_search
from app.search.reranker import rerank

if settings.llm_provider == "local":
    from app.rag.local_llm import stream_local

_PROVIDER_URLS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "cerebras": "https://api.cerebras.ai/v1/chat/completions",
}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _stream_local_async(system: str, user: str) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _run():
        try:
            for token in stream_local(system, user):
                loop.call_soon_threadsafe(queue.put_nowait, token)
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=_run, daemon=True).start()
    while True:
        item = await queue.get()
        if item is None:
            break
        if isinstance(item, Exception):
            raise item
        yield item


async def _stream_cloud(system: str, user: str) -> AsyncGenerator[str, None]:
    provider = settings.llm_provider
    url = _PROVIDER_URLS[provider]
    api_key = settings.cerebras_api_key if provider == "cerebras" else settings.groq_api_key
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "max_tokens": settings.llm_max_tokens,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code >= 400:
                body = await response.aread()
                raise RuntimeError(f"{provider} {response.status_code}: {body.decode()}")
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                chunk = json.loads(line[6:])
                token = chunk["choices"][0]["delta"].get("content", "")
                if token:
                    yield token


async def rag_stream(question: str) -> AsyncGenerator[str, None]:
    try:
        lf = get_langfuse()
        trace = lf.start_observation(name="rag", as_type="chain", input={"question": question})
    except Exception:
        lf = _NoopLangfuse()
        trace = _NoopSpan()

    # — hybrid search —
    t0 = time.perf_counter()
    async with async_session() as session:
        candidates = await hybrid_search(session, question, top_k=20)
    search_latency = time.perf_counter() - t0

    try:
        search_span = trace.start_observation(name="hybrid_search", as_type="retriever")
        search_span.update(
            input={"question": question},
            output={"hits": len(candidates)},
            metadata={"latency_s": round(search_latency, 3)},
        )
        search_span.end()
    except Exception:
        pass

    # — reranking —
    t0 = time.perf_counter()
    sources: list[SearchResult] = await asyncio.to_thread(rerank, question, candidates, 5)
    rerank_latency = time.perf_counter() - t0

    try:
        rerank_span = trace.start_observation(name="reranker", as_type="span")
        rerank_span.update(
            input={"candidates": len(candidates)},
            output={"selected": len(sources)},
            metadata={"latency_s": round(rerank_latency, 3)},
        )
        rerank_span.end()
    except Exception:
        pass

    if not sources:
        answer = "Je ne trouve pas cette information dans les documents disponibles."
        try:
            trace.set_trace_io(output={"answer": answer, "sources": 0})
            trace.end()
            lf.flush()
        except Exception:
            pass
        yield _sse({"type": "token", "content": answer})
        yield _sse({"type": "done", "sources": []})
        return

    user_message = build_user_message(question, sources)

    # — LLM generation —
    try:
        generation = trace.start_observation(
            name="llm",
            as_type="generation",
            model=settings.llm_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception:
        generation = _NoopSpan()

    t0 = time.perf_counter()
    full_answer: list[str] = []

    try:
        stream = (
            _stream_local_async(SYSTEM_PROMPT, user_message)
            if settings.llm_provider == "local"
            else _stream_cloud(SYSTEM_PROMPT, user_message)
        )
        async for token in stream:
            full_answer.append(token)
            yield _sse({"type": "token", "content": token})
    except RuntimeError as exc:
        err = str(exc)
        if "429" in err:
            msg = "Limite de tokens atteinte (Groq). Réessayez dans quelques minutes."
        elif "401" in err:
            msg = "Clé API Groq invalide ou expirée."
        else:
            msg = f"Erreur lors de la génération : {err}"
        yield _sse({"type": "error", "message": msg})
        return

    llm_latency = time.perf_counter() - t0
    answer_text = "".join(full_answer)

    try:
        generation.update(
            output=answer_text,
            metadata={"latency_s": round(llm_latency, 3)},
        )
        generation.end()
    except Exception:
        pass

    citations = [
        {
            "index": i,
            "institution": s.source_institution,
            "type_document": s.type_document,
            "annee_fiscale": s.annee_fiscale,
            "url": s.url_origine,
            "url_hash": s.url_hash,
            "contient_tableaux": s.contient_tableaux,
            "content": s.content,
            "page_start": s.page_start,
            "page_end": s.page_end,
        }
        for i, s in enumerate(sources, 1)
    ]

    try:
        trace.set_trace_io(output={"answer": answer_text, "sources": len(sources)})
        trace.update(
            metadata={
                "search_latency_s": round(search_latency, 3),
                "rerank_latency_s": round(rerank_latency, 3),
                "llm_latency_s": round(llm_latency, 3),
            }
        )
        trace.end()
        lf.flush()
    except Exception:
        pass

    yield _sse({"type": "done", "sources": citations})
