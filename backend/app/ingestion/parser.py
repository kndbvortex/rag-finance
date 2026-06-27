import logging
from pathlib import Path

from bs4 import BeautifulSoup
from unstructured.documents.elements import Footer, Header, Image, PageBreak, Table
from unstructured.partition.pdf import partition_pdf

logger = logging.getLogger(__name__)

_SKIP = (Header, Footer, PageBreak, Image)
_SCANNED_WORD_THRESHOLD = 50

# (segment_text, page_number)
Segment = tuple[str, int]


def _partition(path: Path, strategy: str) -> list:
    return partition_pdf(
        filename=str(path),
        strategy=strategy,
        infer_table_structure=True,
        languages=["fra", "eng"],
    )


def _is_scanned(elements: list) -> bool:
    words = sum(
        len(e.text.split())
        for e in elements
        if hasattr(e, "text") and e.text
    )
    return words < _SCANNED_WORD_THRESHOLD


def _html_table_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return ""

    rows = []
    for tr in table.find_all("tr"):
        cells = [
            td.get_text(" ", strip=True).replace("|", "\\|")
            for td in tr.find_all(["td", "th"])
        ]
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    max_cols = max(len(r) for r in rows)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]

    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * max_cols) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def _element_to_text(element) -> str:
    if isinstance(element, Table):
        html = getattr(element.metadata, "text_as_html", None)
        if html:
            return _html_table_to_markdown(html)
    return element.text or ""


def extract(path: Path) -> tuple[list[Segment], bool]:
    """
    Returns (segments, has_tables) where segments is a list of (text, page_number).
    Falls back to OCR if the fast pass yields almost no text.
    """
    try:
        elements = _partition(path, "fast")
    except Exception:
        logger.warning("fast partition failed for %s, trying ocr_only", path.name, exc_info=True)
        try:
            elements = _partition(path, "ocr_only")
        except Exception:
            logger.error("all partition strategies failed for %s", path.name, exc_info=True)
            return [], False

    if _is_scanned(elements):
        logger.info("%s looks scanned, switching to ocr_only", path.name)
        try:
            elements = _partition(path, "ocr_only")
        except Exception:
            logger.warning("ocr_only failed for %s, using fast output", path.name, exc_info=True)

    segments: list[Segment] = []
    has_tables = False

    for el in elements:
        if isinstance(el, _SKIP):
            continue
        if isinstance(el, Table):
            has_tables = True
        text = _element_to_text(el).strip()
        if not text:
            continue
        page_num = getattr(getattr(el, "metadata", None), "page_number", None) or 1
        segments.append((text, page_num))

    return segments, has_tables
