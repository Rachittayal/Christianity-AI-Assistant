import os
from sentence_transformers import SentenceTransformer
import chromadb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma")
COLLECTION_NAME = "bible_kjv"
BATCH_SIZE = 500

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

print("[embeddings] Loading sentence-transformer model...")
_model = SentenceTransformer(EMBEDDING_MODEL)
print("[embeddings] Model ready.")

def get_chroma_collection() -> chromadb.Collection:

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "KJV Bible verses — semantic embeddings"}
    )
    return collection


def embed_all_verses() -> None:
    from bible_db import get_all_verses

    collection     = get_chroma_collection()
    existing_count = collection.count()

    if existing_count > 0:
        print(f"[embeddings] Already have {existing_count} verses embedded. Skipping.")
        return

    print("[embeddings] Loading all KJV verses from database...")
    verses = get_all_verses("KJV")
    total  = len(verses)
    print(f"[embeddings] Loaded {total} verses. Starting local embedding...")
    print(f"[embeddings] This runs once only — no API calls, no cost.")

    for batch_start in range(0, total, BATCH_SIZE):
        batch = verses[batch_start : batch_start + BATCH_SIZE]

        texts = [
            f"{v['reference']} — {v['text']}"
            for v in batch
        ]

        ids = [
            f"{v['book']}_{v['chapter']}_{v['verse']}"
            for v in batch
        ]

        metadatas = [
            {
                "book":      v["book"],
                "chapter":   v["chapter"],
                "verse":     v["verse"],
                "reference": v["reference"],
                "text":      v["text"],
            }
            for v in batch
        ]

        embeddings = _model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

        completed = min(batch_start + BATCH_SIZE, total)
        print(f"[embeddings] Progress: {completed}/{total} verses embedded...")

    print(f"[embeddings] Complete. {total} verses stored in ChromaDB.")

def query_similar_verses(query: str, n_results: int = 5) -> list[dict]:

    collection = get_chroma_collection()

    if collection.count() == 0:
        print("[embeddings] Warning: no embeddings found. Run embed_all_verses() first.")
        return []

    query_embedding = _model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )

    verses = []
    for metadata in results["metadatas"][0]:
        verses.append({
            "reference": metadata["reference"],
            "text":      metadata["text"],
            "book":      metadata["book"],
            "chapter":   int(metadata["chapter"]),
            "verse":     int(metadata["verse"]),
        })

    return verses