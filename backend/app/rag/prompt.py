from app.search.hybrid import SearchResult

SYSTEM_PROMPT = """Tu es un assistant spécialisé dans l'analyse de documents administratifs et budgétaires français.

RÈGLE ABSOLUE : Tu dois UNIQUEMENT répondre en te basant sur les extraits de documents fournis.
Si la réponse exacte n'est pas présente dans ces extraits, réponds uniquement :
"Je ne trouve pas cette information dans les documents disponibles."

N'invente jamais de chiffres, de dates, d'articles de loi ou de montants budgétaires.
À chaque fois que tu utilises une information tirée d'un document, cite sa source entre crochets immédiatement après : [Source 1], [Source 2], etc.
Si plusieurs sources confirment ou complètent une information, cite-les toutes : [Source 1][Source 3].
Réponds en français."""


def build_context(sources: list[SearchResult]) -> str:
    blocks = []
    for i, source in enumerate(sources, 1):
        header = (
            f"[Source {i}] {source.source_institution} — {source.type_document}"
            + (f" ({source.annee_fiscale})" if source.annee_fiscale else "")
        )
        blocks.append(f"{header}\nURL: {source.url_origine}\n---\n{source.content}")
    return "\n\n".join(blocks)


def build_user_message(question: str, sources: list[SearchResult]) -> str:
    context = build_context(sources)
    return f"Documents de référence :\n\n{context}\n\n---\n\nQuestion : {question}"
