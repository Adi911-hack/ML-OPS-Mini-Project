
from pathlib import Path
from functools import lru_cache
import json
import argparse
import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
CHUNKS_FILE = BASE_DIR / "chunks.json"
DB_DIR = BASE_DIR / "chroma_db"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "aviation_regulations"
DGCA_SOURCE = "dgca_car_section3_series_m_part4.pdf"


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL_NAME)


def load_chunks():
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError("Run process_documents.py first.")

    with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    if not chunks:
        raise ValueError("No chunks found.")

    return chunks


def get_collection():
    client = chromadb.PersistentClient(path=str(DB_DIR))
    names = [c.name for c in client.list_collections()]

    if COLLECTION_NAME not in names:
        raise RuntimeError("Database not found. Run --build first.")

    return client.get_collection(COLLECTION_NAME)


def build_database():
    chunks = load_chunks()
    model = get_model()
    client = chromadb.PersistentClient(path=str(DB_DIR))

    names = [c.name for c in client.list_collections()]

    if COLLECTION_NAME in names:
        client.delete_collection(COLLECTION_NAME)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    batch_size = 32

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        texts = [item["text"] for item in batch]

        embeddings = model.encode(
            texts,
            normalize_embeddings=True
        ).tolist()

        collection.add(
            ids=[item["id"] for item in batch],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {
                    "source": item["source"],
                    "page": item["page"],
                    "chunk": item["chunk"]
                }
                for item in batch
            ]
        )

        print(f"Indexed {min(start + batch_size, len(chunks))}/{len(chunks)} chunks")

    print(f"Database created with {collection.count()} chunks.")


def query_collection(collection, embedding, count, source=None):
    if count <= 0:
        return []

    options = {
        "query_embeddings": embedding,
        "n_results": count,
        "include": ["documents", "metadatas", "distances"]
    }

    if source:
        options["where"] = {"source": source}

    results = collection.query(**options)
    matches = []

    for i, text in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][i]

        matches.append({
            "source": metadata["source"],
            "page": metadata["page"],
            "chunk": metadata["chunk"],
            "distance": round(results["distances"][0][i], 4),
            "text": text
        })

    return matches


def search_regulations(question, top_k=5, dgca_first=True):
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    collection = get_collection()
    total = collection.count()

    if total == 0:
        return []

    model = get_model()

    embedding = model.encode(
        [question],
        normalize_embeddings=True
    ).tolist()

    limit = min(top_k, total)

    if not dgca_first:
        return query_collection(collection, embedding, limit)

    dgca_count = len(collection.get(
    where={"source": DGCA_SOURCE},
    include=[]
)["ids"])
    

    if dgca_count == 0:
        return query_collection(collection, embedding, limit)

    dgca_limit = min(max(limit - 1, 1), dgca_count)

    dgca_results = query_collection(
        collection,
        embedding,
        dgca_limit,
        DGCA_SOURCE
    )

    other_limit = limit - len(dgca_results)

    other_results = []

    if other_limit > 0:
        other_count = len(collection.get(
    where={"source": {"$ne": DGCA_SOURCE}},
    include=[]
)["ids"]
        )

        if other_count > 0:
            results = collection.query(
                query_embeddings=embedding,
                n_results=min(other_limit, other_count),
                where={"source": {"$ne": DGCA_SOURCE}},
                include=["documents", "metadatas", "distances"]
            )

            for i, text in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]

                other_results.append({
                    "source": metadata["source"],
                    "page": metadata["page"],
                    "chunk": metadata["chunk"],
                    "distance": round(results["distances"][0][i], 4),
                    "text": text
                })

    return dgca_results + other_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--query", type=str)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--semantic-only", action="store_true")

    args = parser.parse_args()

    if args.build:
        build_database()

    elif args.query is not None:
        results = search_regulations(
            args.query,
            args.top_k,
            dgca_first=not args.semantic_only
        )

        for index, item in enumerate(results, start=1):
            print(f"\nResult {index}")
            print(f"Source: {item['source']}")
            print(f"Page: {item['page']}")
            print(f"Chunk: {item['chunk']}")
            print(f"Distance: {item['distance']}")
            print(f"Text: {item['text']}\n")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
