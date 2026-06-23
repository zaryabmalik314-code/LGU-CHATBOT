import json
import chromadb
from sentence_transformers import SentenceTransformer

# Load embedding model (small, fast, good quality)
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Setup ChromaDB (saves to local folder "chroma_db")
client = chromadb.PersistentClient(path="chroma_db")

try:
    client.delete_collection(name="lgu_chunks")
    print("Old collection deleted.")
except:
    print("No old collection found, starting fresh.")

collection = client.create_collection(name="lgu_chunks")

# Load chunks
chunks = []
with open("lgu_chunks.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        chunks.append(json.loads(line))

print(f"Embedding {len(chunks)} chunks...")

batch_size = 100
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i+batch_size]
    texts = [c["text"] for c in batch]
    ids = [c["chunk_id"] for c in batch]
    metadatas = [{"url": c["url"], "title": c["title"]} for c in batch]

    embeddings = model.encode(texts).tolist()

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )
    print(f"  Added batch {i//batch_size + 1} / {(len(chunks)//batch_size)+1}")

print("Done! ChromaDB stored in folder: chroma_db")