
def search_documents(query):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty")

    from member3_rag.rag_interface import search_corpus

    results = search_corpus(query, top_k=5)

    if not isinstance(results, list):
        raise ValueError("RAG search must return a list")

    passages = []

    for item in results:
        if not isinstance(item, dict):
            continue

        if not all(item.get(k) for k in ["clause_id", "source", "text"]):
            continue

        passages.append({
            "clause_id": item["clause_id"],
            "document": item["source"],
            "page": item.get("page"),
            "passage": item["text"],
            "distance": item.get("distance")
        })

    return {
        "status": "ok",
        "query": query,
        "passages": passages
    }


def lookup_clause(clause_id):
    if not isinstance(clause_id, str) or not clause_id.strip():
        raise ValueError("Clause ID cannot be empty")

    from member3_rag.rag_interface import get_clause_by_id

    item = get_clause_by_id(clause_id)

    if item is None:
        return {
            "status": "not_found",
            "clause": None
        }

    if not isinstance(item, dict):
        raise ValueError("Invalid clause lookup response")

    if not all(item.get(k) for k in ["clause_id", "source", "text"]):
        raise ValueError("Incomplete clause evidence")

    return {
        "status": "ok",
        "clause": {
            "clause_id": item["clause_id"],
            "document": item["source"],
            "page": item.get("page"),
            "passage": item["text"]
        }
    }
