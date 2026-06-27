import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")

MAX_TOKENS = 700
OVERLAP_TOKENS = 100

# (chunk_text, token_count, page_start, page_end)
Chunk = tuple[str, int, int, int]


def chunk(segments: list[tuple[str, int]]) -> list[Chunk]:
    """
    Accepts a list of (text, page_number) segments.
    Returns list of (chunk_text, token_count, page_start, page_end).
    Splits at MAX_TOKENS with OVERLAP_TOKENS overlap, tracking page spans.
    """
    if not segments:
        return []

    # Flatten into (token_id, page_number) pairs
    token_pages: list[tuple[int, int]] = []
    for text, page_num in segments:
        ids = _enc.encode(text)
        for tok_id in ids:
            token_pages.append((tok_id, page_num))

    if not token_pages:
        return []

    results: list[Chunk] = []
    start = 0

    while start < len(token_pages):
        end = min(start + MAX_TOKENS, len(token_pages))
        window = token_pages[start:end]

        token_ids = [t[0] for t in window]
        pages = [t[1] for t in window]

        chunk_text = _enc.decode(token_ids)
        results.append((chunk_text, len(token_ids), min(pages), max(pages)))

        if end == len(token_pages):
            break
        start = end - OVERLAP_TOKENS

    return results
