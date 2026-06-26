import asyncio
import hashlib
import logging
import re
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Document

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw_pdfs"
PDF_MAGIC = b"%PDF"

SEARCH_TARGETS = [
    {
        "query": 'site:assemblee-nationale.fr filetype:pdf rapport budget',
        "institution": "Assemblée Nationale",
        "type_document": "Rapport parlementaire",
        "annee_fiscale": 2026,
    },
    {
        "query": 'site:economie.gouv.fr filetype:pdf budget PLF',
        "institution": "Ministère de l'Économie",
        "type_document": "Document budgétaire",
        "annee_fiscale": 2026,
    },
    {
        "query": 'site:budget.gouv.fr filetype:pdf rapport annuel depenses',
        "institution": "Ministère du Budget",
        "type_document": "Rapport annuel",
        "annee_fiscale": 2026,
    },
    {
        "query": 'site:senat.fr filetype:pdf rapport commission finances',
        "institution": "Sénat",
        "type_document": "Rapport de commission",
        "annee_fiscale": 2026,
    },
    {
        "query": 'site:collectivites-locales.gouv.fr filetype:pdf bilan financier',
        "institution": "Direction Générale des Collectivités Locales",
        "type_document": "Bilan financier",
        "annee_fiscale": 2026,
    },
]


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:64]


def _institution_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _pdf_path(institution: str, url: str) -> Path:
    directory = DATA_DIR / _institution_slug(institution)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{_url_hash(url)}.pdf"


async def _search(client: httpx.AsyncClient, query: str, pages: int = 2) -> list[str]:
    urls: list[str] = []
    for page in range(1, pages + 1):
        try:
            response = await client.get(
                f"{settings.searxng_url}/search",
                params={"q": query, "format": "json", "categories": "general", "pageno": page},
            )
            response.raise_for_status()
            for result in response.json().get("results", []):
                url = result.get("url", "")
                if url.lower().endswith(".pdf"):
                    urls.append(url)
            await asyncio.sleep(1.0)
        except Exception:
            logger.warning("SearXNG query failed — query=%r page=%d", query, page, exc_info=True)
    return list(dict.fromkeys(urls))


async def _download(
    client: httpx.AsyncClient,
    session: AsyncSession,
    url: str,
    target: dict,
) -> Document | None:
    h = _url_hash(url)

    existing = await session.scalar(select(Document).where(Document.url_hash == h))
    if existing:
        return None

    try:
        async with client.stream("GET", url, timeout=60.0) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                logger.warning("skipping non-PDF %s (%s)", url, content_type)
                return None
            data = b"".join([chunk async for chunk in response.aiter_bytes(8192)])
    except Exception:
        logger.warning("download failed: %s", url, exc_info=True)
        return None

    if not data.startswith(PDF_MAGIC):
        logger.warning("invalid PDF magic bytes: %s", url)
        return None

    path = _pdf_path(target["institution"], url)
    path.write_bytes(data)
    logger.info("saved %.1f KB → %s", len(data) / 1024, path)

    doc = Document(
        url=url,
        url_hash=h,
        source_institution=target["institution"],
        type_document=target["type_document"],
        annee_fiscale=target.get("annee_fiscale"),
        file_path=str(path),
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def run_scraper(session: AsyncSession) -> list[Document]:
    documents: list[Document] = []
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RAG-scraper/1.0)"},
    ) as client:
        for target in SEARCH_TARGETS:
            logger.info("querying SearXNG: %r", target["query"])
            urls = await _search(client, target["query"])
            logger.info("%d PDF URLs found for %s", len(urls), target["institution"])
            for url in urls:
                doc = await _download(client, session, url, target)
                if doc:
                    documents.append(doc)

    return documents
