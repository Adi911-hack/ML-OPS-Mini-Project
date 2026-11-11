
from ast import pattern
from pathlib import Path
from functools import lru_cache
from bisect import bisect_right
import argparse
import re
import chromadb
import pymupdf
from sentence_transformers import SentenceTransformer
from member3_rag.process_documents import clean_text

BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE_DIR / "documents"
DB_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "aviation_clauses"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

SOURCES = {
    "DGCA": "dgca_car_section3_series_m_part4.pdf",
    "INDIGO": "indigo_conditions_of_carriage.pdf",
    "MOCA": "moca_passenger_charter.pdf"
}


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL_NAME)


def extract_numbered_clauses(source, filename):
    path = DOCUMENTS_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing document: {path}")

    pages = []

    with pymupdf.open(path) as pdf:
        for page in pdf:
            pages.append(page.get_text("text"))

    starts = []
    position = 0

    for page in pages:
        starts.append(position)
        position += len(page) + 1

    full_text = "\n".join(pages)

    pattern = re.compile(
        r"(?m)^[ \t]*(\d+(?:\.\d+){1,2})[ \t]+(?=[A-Z])"
)

    matches = list(pattern.finditer(full_text))
    clauses = []

    for i, match in enumerate(matches):
        start = match.start()
        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(full_text)
        )

        clause_number = match.group(1)
        text = full_text[start:end].strip()

        if len(text) < 30:
            continue

        page_number = bisect_right(starts, start)

        clauses.append({
            "clause_id": f"{source}:{clause_number}",
            "source": filename,
            "page": page_number,
            "text": text
        })

    return clauses


def extract_charter_pages():
    filename = SOURCES["MOCA"]
    path = DOCUMENTS_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing document: {path}")

    passages = []

    with pymupdf.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = clean_text(page.get_text("text"))

            if text:
                passages.append({
                    "clause_id": f"MOCA:P{page_number}",
                    "source": filename,
                    "page": page_number,
                    "text": text
                })

    return passages


def build_corpus():
    passages = []

    passages.extend(
        extract_numbered_clauses("DGCA", SOURCES["DGCA"])
    )

    passages.extend(
        extract_numbered_clauses("INDIGO", SOURCES["INDIGO"])
    )

    passages.extend(extract_charter_pages())

    unique = {}

    for passage in passages:
        unique[passage["clause_id"]] = passage

    passages = list(unique.values())

    if not passages:
        raise ValueError("No passages were extracted.")

    model = get_model()
    client = chromadb.PersistentClient(path=str(DB_DIR))

    names = [c.name for c in client.list_collections()]

    if COLLECTION_NAME in names:
        client.delete_collection(COLLECTION_NAME)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    for start in range(0, len(passages), 32):
        batch = passages[start:start + 32]
        texts = [item["text"] for item in batch]

        embeddings = model.encode(
            texts,
            normalize_embeddings=True
        ).tolist()

        collection.add(
            ids=[item["clause_id"] for item in batch],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {
                    "source": item["source"],
                    "page": item["page"]
                }
                for item in batch
            ]
        )

        print(f"Indexed {min(start + 32, len(passages))}/{len(passages)}")

    print(f"Clause database ready: {collection.count()} passages")


def get_collection():
    client = chromadb.PersistentClient(path=str(DB_DIR))

    names = [c.name for c in client.list_collections()]

    if COLLECTION_NAME not in names:
        raise RuntimeError("Run rag_interface.py --build first.")

    return client.get_collection(COLLECTION_NAME)


def search_corpus(query: str, top_k: int = 5) -> list[dict]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be positive.")

    collection = get_collection()

    if collection.count() == 0:
        return []

    embedding = get_model().encode(
        [query],
        normalize_embeddings=True
    ).tolist()

    results = collection.query(
        query_embeddings=embedding,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    passages = []

    for i, clause_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][i]

        passages.append({
            "clause_id": clause_id,
            "source": metadata["source"],
            "page": metadata["page"],
            "text": results["documents"][0][i],
            "distance": round(results["distances"][0][i], 4)
        })

    return passages


def get_clause_by_id(clause_id: str) -> dict | None:
    collection = get_collection()

    result = collection.get(
        ids=[clause_id],
        include=["documents", "metadatas"]
    )

    if not result["ids"]:
        return None

    metadata = result["metadatas"][0]

    return {
        "clause_id": result["ids"][0],
        "source": metadata["source"],
        "page": metadata["page"],
        "text": result["documents"][0]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--query", type=str)
    parser.add_argument("--clause", type=str)
    args = parser.parse_args()

    if args.build:
        build_corpus()

    elif args.query:
        for result in search_corpus(args.query):
            print(result)
            print()

    elif args.clause:
        print(get_clause_by_id(args.clause))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

