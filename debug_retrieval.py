import chromadb
from sentence_transformers import SentenceTransformer

embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection(name="lgu_chunks")

# Try a few different phrasings to compare results
queries = [
    "which subjects do I learn in 3rd semester BSCS",
    "BSCS scheme of studies semester 3",
    "Computer Science semester 3 courses",
]

for q in queries:
    print("=" * 70)
    print("QUERY:", q)
    print("=" * 70)
    query_embedding = embed_model.encode([q]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=5)

    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        print(f"\n--- Result {i+1} | source: {meta.get('url','')} ---")
        print(doc[:300])  # print first 300 chars of the chunk
    print("\n")
