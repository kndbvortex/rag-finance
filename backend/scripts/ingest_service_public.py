"""
Ingest service-public.fr fiscal pages directly into the DB.
Scrapes HTML, extracts clean text, chunks, and inserts.
"""
import asyncio
import hashlib
import logging
import re
import subprocess
import sys
from pathlib import Path

import asyncpg
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.ingestion.chunker import chunk
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

DB_URL = str(settings.database_url).replace("postgresql+asyncpg://", "postgresql://")

# Pages to ingest: (code, url, type)
PAGES = [
    # IR particulier - déclaration
    ("F358",   "https://www.service-public.gouv.fr/particuliers/vosdroits/F358",   "particulier"),
    ("F369",   "https://www.service-public.gouv.fr/particuliers/vosdroits/F369",   "particulier"),
    ("F359",   "https://www.service-public.gouv.fr/particuliers/vosdroits/F359",   "particulier"),
    ("F33885", "https://www.service-public.gouv.fr/particuliers/vosdroits/F33885", "particulier"),
    ("F388",   "https://www.service-public.gouv.fr/particuliers/vosdroits/F388",   "particulier"),
    ("F383",   "https://www.service-public.gouv.fr/particuliers/vosdroits/F383",   "particulier"),
    # Barème et calcul
    ("F1419",  "https://www.service-public.gouv.fr/particuliers/vosdroits/F1419",  "particulier"),
    ("F357",   "https://www.service-public.gouv.fr/particuliers/vosdroits/F357",   "particulier"),
    ("F62",    "https://www.service-public.gouv.fr/particuliers/vosdroits/F62",    "particulier"),
    ("F13216", "https://www.service-public.gouv.fr/particuliers/vosdroits/F13216", "particulier"),
    ("F2705",  "https://www.service-public.gouv.fr/particuliers/vosdroits/F2705",  "particulier"),
    ("F3085",  "https://www.service-public.gouv.fr/particuliers/vosdroits/F3085",  "particulier"),
    # Revenus à déclarer
    ("F1225",  "https://www.service-public.gouv.fr/particuliers/vosdroits/F1225",  "particulier"),
    ("F1989",  "https://www.service-public.gouv.fr/particuliers/vosdroits/F1989",  "particulier"),
    ("F2613",  "https://www.service-public.gouv.fr/particuliers/vosdroits/F2613",  "particulier"),
    ("F1991",  "https://www.service-public.gouv.fr/particuliers/vosdroits/F1991",  "particulier"),
    ("F415",   "https://www.service-public.gouv.fr/particuliers/vosdroits/F415",   "particulier"),
    ("F21618", "https://www.service-public.gouv.fr/particuliers/vosdroits/F21618", "particulier"),
    ("F31725", "https://www.service-public.gouv.fr/particuliers/vosdroits/F31725", "particulier"),
    ("F3153",  "https://www.service-public.gouv.fr/particuliers/vosdroits/F3153",  "particulier"),
    ("F1228",  "https://www.service-public.gouv.fr/particuliers/vosdroits/F1228",  "particulier"),
    # Crédits et réductions
    ("F12",    "https://www.service-public.gouv.fr/particuliers/vosdroits/F12",    "particulier"),
    # Fraude et sanctions
    ("F31451", "https://www.service-public.gouv.fr/particuliers/vosdroits/F31451", "particulier"),
    ("F34175", "https://www.service-public.gouv.fr/particuliers/vosdroits/F34175", "particulier"),
    ("F34176", "https://www.service-public.gouv.fr/particuliers/vosdroits/F34176", "particulier"),
    ("F31130", "https://www.service-public.gouv.fr/particuliers/vosdroits/F31130", "particulier"),
    # IS / entreprises - via entreprendre portal
    ("F23257", "https://entreprendre.service-public.fr/vosdroits/F23257", "entreprise"),
    ("F23259", "https://entreprendre.service-public.fr/vosdroits/F23259", "entreprise"),
    ("F31909", "https://entreprendre.service-public.fr/vosdroits/F31909", "entreprise"),
    ("F32105", "https://entreprendre.service-public.fr/vosdroits/F32105", "entreprise"),
    ("F31431", "https://entreprendre.service-public.fr/vosdroits/F31431", "entreprise"),
    ("F33429", "https://entreprendre.service-public.fr/vosdroits/F33429", "entreprise"),
]


def fetch_html(url: str) -> str:
    r = subprocess.run(
        ["/usr/bin/curl", "-s", "-L", "--max-time", "15",
         "-A", "Mozilla/5.0 (X11; Linux x86_64) Chrome/124",
         url],
        capture_output=True,
    )
    return r.stdout.decode("utf-8", errors="replace")


_NOISE_CLASSES = re.compile(
    r"sp-notation|rs_skip|sp-no-print|fr-modal|fr-header|fr-footer|"
    r"fr-breadcrumb|sp-ancres|sp-share|fr-skiplinks|orejime|fr-consent|"
    r"sp-notation-title",
    re.I,
)


def extract_text(html: str) -> tuple[str, str]:
    """Returns (title, clean_text) — uses article.article and strips feedback widgets."""
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    # Prefer the article element; fall back to main or whole soup
    content = (
        soup.find("article", class_="article")
        or soup.find("main")
        or soup
    )

    # Remove structural noise and feedback/rating widgets
    for tag in content.find_all(["nav", "header", "footer", "script", "style", "aside", "noscript"]):
        tag.decompose()
    for tag in content.find_all(class_=_NOISE_CLASSES):
        tag.decompose()

    text = content.get_text("\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 15]
    return title, "\n".join(lines)


def make_segments(text: str) -> list[tuple[str, int]]:
    """Pass full text as one segment so chunker preserves newlines between paragraphs."""
    return [(text, 1)]


async def ingest_page(conn: asyncpg.Connection, code: str, url: str, page_type: str) -> int:
    url_hash = hashlib.sha256(url.encode()).hexdigest()

    # Check if already in DB
    existing = await conn.fetchval("SELECT id FROM documents WHERE url_hash=$1", url_hash)
    if existing:
        logger.info("SKIP %s — already in DB", code)
        return 0

    html = fetch_html(url)
    if len(html) < 5000:
        logger.warning("SKIP %s — empty/not found (%d chars)", code, len(html))
        return 0

    title, text = extract_text(html)
    words = len(text.split())
    if words < 100:
        logger.warning("SKIP %s — too short (%d words)", code, words)
        return 0

    logger.info("Processing %s — %s (%d words)", code, title[:60], words)

    # Save text to file (as placeholder for file_path)
    file_dir = Path(__file__).parent.parent / "data" / "raw_pdfs" / "service_public"
    file_path = file_dir / f"{code}.txt"
    file_path.write_text(text, encoding="utf-8")

    source_institution = "service-public.fr"
    type_doc = f"guide_pratique_IR_{page_type}"

    doc_id = await conn.fetchval(
        """
        INSERT INTO documents (url, url_hash, source_institution, type_document, file_path)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (url_hash) DO NOTHING
        RETURNING id
        """,
        url, url_hash, source_institution, type_doc, str(file_path),
    )

    if not doc_id:
        logger.warning("INSERT failed for %s", code)
        return 0

    segments = make_segments(text)
    chunks = chunk(segments)

    for i, (content, token_count, _page_start, _page_end) in enumerate(chunks):
        await conn.execute(
            """
            INSERT INTO document_chunks
                (document_id, content, chunk_index, contient_tableaux, token_count)
            VALUES ($1, $2, $3, $4, $5)
            """,
            doc_id, content, i, False, token_count,
        )

    logger.info("  → %d chunks inserted for %s", len(chunks), code)
    return len(chunks)


async def main() -> None:
    conn = await asyncpg.connect(DB_URL)
    total = 0
    for code, url, page_type in PAGES:
        try:
            n = await ingest_page(conn, code, url, page_type)
            total += n
        except Exception:
            logger.exception("Error ingesting %s", code)
    await conn.close()
    logger.info("Done — %d total chunks inserted", total)


if __name__ == "__main__":
    asyncio.run(main())
# This is appended - new pages only, not re-run
