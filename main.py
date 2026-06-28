import os
import re
import zipfile
import requests
from collections import defaultdict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
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

print("Reranker disabled for performance (see CHROMA_RETRIEVE_K/RERANK_KEEP_K comments below) — not loading cross-encoder.")
reranker = None  # kept as a variable so re-enabling later is a one-line change
# To re-enable: uncomment the two lines below and also see the commented
# rerank block further down in the /ask endpoint.
# print("Loading reranker model...")
# reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_or_create_collection(name="lgu_chunks")
print(f"=== Chroma collection 'lgu_chunks' loaded with {collection.count()} chunks ===")

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# Distance threshold for ChromaDB results. Lower distance = better match.
# If the closest chunk's distance is above this, we treat it as "not found
# in our data" and fall back to a web search instead of forcing an answer
# out of irrelevant context. Tune this after watching real distances in logs.
CHROMA_DISTANCE_THRESHOLD = 1.1

# How many chunks to pull from Chroma before reranking, and how many to
# actually keep for the final context after reranking.
CHROMA_RETRIEVE_K = 15
RERANK_KEEP_K = 8
print(f"=== Settings: CHROMA_RETRIEVE_K={CHROMA_RETRIEVE_K}, RERANK_KEEP_K={RERANK_KEEP_K} ===")


def web_search_fallback(question: str):
    """Search the web for a general/common question that isn't covered by
    LGU's own data. Returns (context_text, source_urls). Returns (None, [])
    if the search fails or no key is configured."""
    if not TAVILY_API_KEY:
        return None, []
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": question,
                "search_depth": "basic",
                "max_results": 4,
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None, []
        context_parts = []
        urls = []
        for r in results:
            content = r.get("content", "")
            if content:
                context_parts.append(content)
            url = r.get("url")
            if url:
                urls.append(url)
        return "\n\n".join(context_parts)[:6000], urls
    except Exception as e:
        print(f"Web search fallback failed: {e}")
        return None, []

session_memory = defaultdict(list)
MAX_HISTORY = 6

# ---------- Web-fallback rate limiting ----------
# This bot is meant for LGU-related queries. The web search fallback exists
# only to handle the occasional common/general question. To stop it being
# used as a general-purpose chatbot (and to protect the free Tavily quota),
# we cap how often any one session can trigger it, plus a global daily cap.
MAX_WEB_SEARCHES_PER_SESSION = 3
MAX_WEB_SEARCHES_PER_DAY = 30

session_web_search_count = defaultdict(int)
daily_web_search_count = 0
daily_web_search_date = None


def _check_and_register_web_search(session_id: str):
    """Returns True if a web search is allowed right now, and registers the
    usage. Returns False if either the per-session or daily cap is hit."""
    global daily_web_search_count, daily_web_search_date
    import datetime
    today = datetime.date.today()
    if daily_web_search_date != today:
        daily_web_search_date = today
        daily_web_search_count = 0

    if daily_web_search_count >= MAX_WEB_SEARCHES_PER_DAY:
        return False
    if session_web_search_count[session_id] >= MAX_WEB_SEARCHES_PER_SESSION:
        return False

    daily_web_search_count += 1
    session_web_search_count[session_id] += 1
    return True

CASUAL_PATTERNS = {
    r"^h(i|ey|ello)+[!.]*$": "Hey there! 👋 How can I help you today?",
    r"^good (morning|afternoon|evening)[!.]*$": "Good day! How can I help you?",
    r"^how are you[?!.]*$": "I'm doing great, thanks for asking! What can I help you with?",
    r"^(thanks|thank you|thx|ty)[!.]*$": "You're welcome! Let me know if you need anything else.",
    r"^(bye|goodbye|see ya|see you|cya)[!.]*$": "Goodbye! Have a great day 👋",
    r"^(ok|okay|cool|nice|great)[!.]*$": "👍 Anything else I can help with?",
    r"^who (made|built|created|developed) you[?!.]*$": "I was built for Lahore Garrison University to help students and visitors with their queries. How can I assist you today?",
    r"^who (owns|is behind) you[?!.]*$": "I was built for Lahore Garrison University to help students and visitors with their queries. How can I assist you today?",
    r"^(what are you|who are you)[?!.]*$": "I'm the LGU Assistant — here to help with admissions, programs, fees, and other university-related questions.",
}


def get_casual_reply(message: str):
    text = message.strip().lower()
    for pattern, reply in CASUAL_PATTERNS.items():
        if re.match(pattern, text):
            return reply
    return None


# Common abbreviations students use that don't exactly match the full
# wording on LGU's own pages. Expanding these before embedding helps the
# vector search find pages that spell things out in full (e.g. a page
# titled "...Artificial Intelligence" won't score as close to a query that
# just says "AI" unless we expand it first).
ACRONYM_EXPANSIONS = {
    r"\bAI\b": "Artificial Intelligence",
    r"\bCS\b": "Computer Science",
    r"\bIT\b": "Information Technology",
    r"\bSE\b": "Software Engineering",
    r"\bDS\b": "Data Science",
    r"\bBBA\b": "Bachelor of Business Administration",
    r"\bMBA\b": "Master of Business Administration",
    r"\bCMAI\b": "Computational Mathematics and Artificial Intelligence",
}


def expand_acronyms(text: str) -> str:
    """Expand common abbreviations so the embedded query is more likely to
    match full-text page titles/content. Appends the expansion alongside
    the original text rather than replacing it, so we don't lose context
    if the acronym was actually correct as-is."""
    expanded = text
    for pattern, full_form in ACRONYM_EXPANSIONS.items():
        if re.search(pattern, text, re.IGNORECASE):
            expanded += f" {full_form}"
    return expanded


# Direct lookup for specific program pages that are mostly course-code
# tables (e.g. "CMAI-6102 | Introduction to AI | 3 | Major"). Tables like
# that embed poorly against natural-language questions, so vector search
# alone often misses them even when they exist in the database. For known
# programs, we bypass ranking entirely and force-fetch every chunk for that
# exact URL via a metadata filter, guaranteeing the real roadmap is used.
# Add more entries here any time a specific program's details aren't
# surfacing correctly - just need the program's keywords and its exact URL.
PROGRAM_URL_LOOKUP = {
    "computational mathematics and artificial intelligence": "https://lgu.edu.pk/bs-mathematics-in-computational-mathematics-and-artificial-intelligence/",
    "cmai": "https://lgu.edu.pk/bs-mathematics-in-computational-mathematics-and-artificial-intelligence/",
}


def find_forced_url(question: str):
    """Check if the question matches a known program in PROGRAM_URL_LOOKUP.
    Returns the exact URL to force-fetch, or None if no match."""
    text = question.lower()
    for keyword, url in PROGRAM_URL_LOOKUP.items():
        if keyword in text:
            return url
    return None


# Keywords that strongly indicate a real LGU question. If any of these
# appear, we skip the Groq router entirely and go straight to RAG — no
# need to spend an extra API round-trip "deciding" on something obvious.
LGU_KEYWORDS = (
    "fee", "fees", "admission", "course", "courses", "program", "programme",
    "degree", "bscs", "bsse", "bsai", "bba", "mba", "mscs", "faculty",
    "teacher", "professor", "campus", "hostel", "scholarship", "merit",
    "deadline", "apply", "application", "semester", "credit", "exam",
    "result", "fee structure", "department", "hod", "dean", "registrar",
    "transcript", "challan", "library", "timing", "schedule", "syllabus",
    "?",
)


def looks_like_real_question(message: str) -> bool:
    text = message.strip().lower()
    return any(keyword in text for keyword in LGU_KEYWORDS)


def classify_intent_with_groq(message: str) -> str:
    """Second-stage check for messages the regex fast-path above didn't
    catch. Uses a small, fast Groq model to decide whether this is casual
    chat (including Roman Urdu fillers like 'acha', 'theek hai', 'haan',
    'bas', 'chalo') or an actual question that needs the RAG pipeline.
    Falls back to 'university_query' on any error, so RAG still runs as a
    safe default and nothing breaks if Groq is briefly unavailable."""
    router_prompt = f"""Classify the user's message into exactly ONE category. Respond with ONLY the category word, nothing else, no punctuation.

Categories:
- chitchat: greetings, thanks, acknowledgments, filler words, casual talk in English or Roman Urdu (examples: "acha", "acha listen", "theek hai", "haan", "bas", "chalo", "ok then", "got it", "achaaa")
- university_query: anything that is or could be a real question, even if short or vague (examples: "fees?", "BSCS", "admission", "tell me more", "3")

Message: "{message}"
Category:"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": router_prompt}],
            temperature=0,
            max_tokens=10,
        )
        category = response.choices[0].message.content.strip().lower()
        if category not in ("chitchat", "university_query"):
            category = "university_query"
        return category
    except Exception as e:
        print(f"Intent router failed, defaulting to university_query: {e}")
        return "university_query"


def get_chitchat_reply(message: str) -> str:
    """Generates a brief, natural reply for messages the Groq router
    classified as chitchat (i.e. ones the regex fast-path didn't already
    handle)."""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a friendly assistant for Lahore Garrison University (LGU). The user just sent a casual/filler message (e.g. 'acha', 'ok then', 'haan'). Reply briefly and naturally in 1 short sentence, and invite them to ask their question."},
                {"role": "user", "content": message},
            ],
            temperature=0.5,
            max_tokens=40,
        )
        return response.choices[0].message.content
    except Exception:
        return "Got it! Let me know what you'd like to ask. 🙂"


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

    # Regex didn't catch it — let Groq decide if this is still casual chat
    # (e.g. Roman Urdu like "acha listen") before we run the full RAG pipeline.
    # Skip this check entirely if the message already looks like a real
    # question (has a "?" or an obvious LGU keyword) — saves a Groq round
    # trip on the common case and avoids slowing down real questions.
    if len(question.strip()) <= 40 and not looks_like_real_question(question):
        intent = classify_intent_with_groq(question)
        if intent == "chitchat":
            answer = get_chitchat_reply(question)
            return {"answer": answer, "sources": [], "session_id": session_id}

    history = session_memory[session_id]
    history_text = ""
    if history:
        history_text = "Previous conversation:\n"
        for pair in history:
            history_text += f"User: {pair['question']}\nAssistant: {pair['answer']}\n"
        history_text += "\n"

    embedding_query = expand_acronyms(question)
    query_embedding = embed_model.encode([embedding_query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=CHROMA_RETRIEVE_K,
        include=["documents", "metadatas", "distances"]
    )
    chunks = results["documents"][0]
    sources = [m["url"] for m in results["metadatas"][0]]
    distances = results["distances"][0]
    best_distance = min(distances) if distances else None
    print(f"Query: '{question}' | best chroma distance: {best_distance}")

    # If the question matches a known program with table-heavy content that
    # vector search tends to miss, force-fetch every chunk for that exact
    # page directly and prepend it to whatever vector search found. This
    # guarantees the real roadmap/course data is included regardless of how
    # it ranks by embedding similarity.
    forced_url = find_forced_url(embedding_query)
    if forced_url:
        forced_results = collection.get(
            where={"url": forced_url},
            include=["documents", "metadatas"],
        )
        if forced_results["documents"]:
            print(f"  -> Forced fetch: found {len(forced_results['documents'])} chunks for {forced_url}")
            chunks = forced_results["documents"] + chunks
            sources = [m["url"] for m in forced_results["metadatas"]] + sources
            best_distance = 0.0  # treat as a confident match, skip web fallback

    # NOTE: We previously reran every chunk through a cross-encoder reranker
    # here for sharper relevance. On Railway's free-tier CPU that step alone
    # was taking ~20-30 seconds per request (a full transformer forward pass
    # per chunk, no GPU). Chroma already returns results sorted by distance
    # (best match first), so we just trust that ordering and keep the top N.
    # This trades a small amount of relevance precision for a massive speed
    # win. If you upgrade to a host with more CPU/a GPU later, the reranker
    # can be re-enabled by uncommenting it below.
    chunks = chunks[:RERANK_KEEP_K]
    sources = sources[:RERANK_KEEP_K]
    # --- to re-enable reranking later, replace the two lines above with: ---
    # if chunks:
    #     pairs = [[question, c] for c in chunks]
    #     rerank_scores = reranker.predict(pairs)
    #     ranked = sorted(zip(rerank_scores, chunks, sources), key=lambda x: x[0], reverse=True)
    #     ranked = ranked[:RERANK_KEEP_K]
    #     chunks = [c for _, c, _ in ranked]
    #     sources = [s for _, _, s in ranked]

    used_web_fallback = False
    rate_limited = False
    if best_distance is None or best_distance > CHROMA_DISTANCE_THRESHOLD:
        if _check_and_register_web_search(session_id):
            web_context, web_sources = web_search_fallback(question)
            if web_context:
                context = web_context
                sources = web_sources
                used_web_fallback = True
            else:
                context = "\n\n".join(chunks)[:12000]
        else:
            rate_limited = True
            context = "\n\n".join(chunks)[:12000]
    else:
        context = "\n\n".join(chunks)[:12000]

    if rate_limited:
        answer = "I'm primarily built to help with LGU-related questions — admissions, programs, fees, faculty, and campus life. I'm not able to look up general questions right now, but feel free to ask me anything about the university!"
        session_memory[session_id].append({"question": question, "answer": answer})
        if len(session_memory[session_id]) > MAX_HISTORY:
            session_memory[session_id] = session_memory[session_id][-MAX_HISTORY:]
        return {"answer": answer, "sources": [], "session_id": session_id}

    if used_web_fallback:
        fallback_note = "The context below comes from a general web search because this question isn't covered in LGU's own records. Answer normally using this context, and you don't need to mention where the information came from unless asked."
    else:
        fallback_note = ""

    prompt = f"""You are a helpful assistant for Lahore Garrison University (LGU).
{history_text}If the user's message is short, vague, or seems to reference a previous list/answer (e.g. "3", "the second one", "ok then answer", "tell me more"), use the conversation history above to figure out what they mean before asking for clarification. Only ask the user to clarify if the conversation history truly doesn't help.

If the question is something inappropriate, harmful, or completely unrelated to any reasonable use case (e.g. asking for help with something dangerous or unrelated technical tasks like writing unrelated code), politely say you're focused on helping with LGU-related queries and general questions, and ask if they have something else in mind.

If the user asks who built you, who developed you, who owns you, or what company/team is behind you, simply say you were built for Lahore Garrison University to help students and visitors with their queries. Do not mention specific AI model names, providers, or technical implementation details.

{fallback_note}

Answer the question using ONLY the context below. If the question doesn't specify which program (e.g. BS CS, BS SE, MS CS), assume BS CS unless context says otherwise. Use data from ONE matching table only — do not mix or compare courses from different programs. Quote course codes and names exactly as written in the context, do not rephrase or guess. Copy each table row exactly as it appears, do not reorder or pair a code with a different course name.

Known data quirks — do NOT flag these as errors, just present them as-is:
- The course code MATH6608 appears twice in some tables (for both "Linear Algebra" and "Probability & Statistics"). This is a known duplication in the university's own data — present both rows normally without commenting on it.
- Course codes shown as "CSE-" or "ALD-" are intentional placeholders. The university assigns the actual code later based on which elective a student picks. Do not say this is missing or incorrect — just state it's a placeholder assigned by the department later.

If you don't know something, say you don't have that information.

If the question is about whether admissions are currently open, the current admission schedule, or application deadlines, and the context does not contain a specific current date or status, say you don't have the live status, and tell the user they can check by calling the Admission Office at 0322 2757543 or 042 37181827, or by visiting the "Apply" page on the LGU website.

Context:
{context}

Question: {question}
Answer:"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for LGU. Keep answers short and to the point by default (2-4 sentences). Only give a longer, detailed answer or a full table/list if the user explicitly asks for details, a list, or a table."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,
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