import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")

MAX_TOKENS = 700
OVERLAP_TOKENS = 100


def chunk(text: str) -> list[tuple[str, int]]:
    """
    Returns list of (chunk_text, token_count).
    Splits at MAX_TOKENS with OVERLAP_TOKENS overlap.
    """
    tokens = _enc.encode(text)
    if not tokens:
        return []

    results: list[tuple[str, int]] = []
    start = 0

    while start < len(tokens):
        end = min(start + MAX_TOKENS, len(tokens))
        chunk_tokens = tokens[start:end]
        results.append((_enc.decode(chunk_tokens), len(chunk_tokens)))
        if end == len(tokens):
            break
        start = end - OVERLAP_TOKENS

    return results
