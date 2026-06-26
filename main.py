import os
import re
import zipfile
import requests
from collections import defaultdict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CHROMA_DB_URL = "https://github.com/zaryabmalik314-code/LGU-CHATBOT/releases/download/chromadb-v1/chroma_db.zip"

if not os.path.exists("chroma_db"):
    print("chroma_db not found, downloading...")
    response = requests.get(CHROMA_DB_URL, stream=True, allow_redirects=True)
    response.raise_for_status()
    with open("chroma_db.zip", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Download complete ({os.path.getsize('chroma_db.zip')} bytes), extracting...")
    with zipfile.ZipFile("chroma_db.zip", "r") as zip_ref:
        zip_ref.extractall(".")
    print("chroma_db ready.")

print("=== chroma_db contents ===")
for root, dirs, files in os.walk("chroma_db"):
    for f in files:
        fp = os.path.join(root, f)
        print(f"{fp} — {os.path.getsize(fp)} bytes")
print("=== end contents ===")

print("Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_or_create_collection(name="lgu_chunks")

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

session_memory = defaultdict(list)
MAX_HISTORY = 6

CASUAL_PATTERNS = {
    r"^h(i|ey|ello)+[!.]*$": "Hey there! 👋 How can I help you today?",
    r"^good (morning|afternoon|evening)[!.]*$": "Good day! How can I help you?",
    r"^how are you[?!.]*$": "I'm doing great, thanks for asking! What can I help you with?",
    r"^(thanks|thank you|thx|ty)[!.]*$": "You're welcome! Let me know if you need anything else.",
    r"^(bye|goodbye|see ya|see you|cya)[!.]*$": "Goodbye! Have a great day 👋",
    r"^(ok|okay|cool|nice|great)[!.]*$": "👍 Anything else I can help with?",
}


def get_casual_reply(message: str):
    text = message.strip().lower()
    for pattern, reply in CASUAL_PATTERNS.items():
        if re.match(pattern, text):
            return reply
    return None


class Question(BaseModel):
    question: str
    session_id: str = "default"


@app.post("/ask")
def ask(q: Question):
    question = q.question
    session_id = q.session_id

    casual_reply = get_casual_reply(question)
    if casual_reply:
        return {"answer": casual_reply, "sources": [], "session_id": session_id}

    history = session_memory[session_id]
    history_text = ""
    if history:
        history_text = "Previous conversation:\n"
        for pair in history:
            history_text += f"User: {pair['question']}\nAssistant: {pair['answer']}\n"
        history_text += "\n"

    query_embedding = embed_model.encode([question]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=10
    )
    chunks = results["documents"][0]
    sources = [m["url"] for m in results["metadatas"][0]]
    context = "\n\n".join(chunks)[:12000]

    prompt = f"""You are a helpful assistant for Lahore Garrison University (LGU).
{history_text}Answer the question using ONLY the context below. If the question doesn't specify which program (e.g. BS CS, BS SE, MS CS), assume BS CS unless context says otherwise. Use data from ONE matching table only — do not mix or compare courses from different programs. Quote course codes and names exactly as written in the context, do not rephrase or guess. Copy each table row exactly as it appears, do not reorder or pair a code with a different course name.

Known data quirks — do NOT flag these as errors, just present them as-is:
- The course code MATH6608 appears twice in some tables (for both "Linear Algebra" and "Probability & Statistics"). This is a known duplication in the university's own data — present both rows normally without commenting on it.
- Course codes shown as "CSE-" or "ALD-" are intentional placeholders. The university assigns the actual code later based on which elective a student picks. Do not say this is missing or incorrect — just state it's a placeholder assigned by the department later.

If you don't know something, say you don't have that information.

Context:
{context}

Question: {question}
Answer:"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for LGU. Answer concisely for simple questions, but show full lists or tables when asked."},
            {"role": "user", "content": prompt}
        ]
    )
    answer = response.choices[0].message.content

    session_memory[session_id].append({"question": question, "answer": answer})
    if len(session_memory[session_id]) > MAX_HISTORY:
        session_memory[session_id] = session_memory[session_id][-MAX_HISTORY:]

    return {
        "answer": answer,
        "sources": list(set(sources)),
        "session_id": session_id
    }


@app.get("/")
def home():
    return {"status": "LGU chatbot backend running"}