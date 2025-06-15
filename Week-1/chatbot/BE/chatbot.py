import os
import uuid
import docx
import PyPDF2
import chromadb
from datetime import datetime
from openai import OpenAI
from chromadb.utils import embedding_functions
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
DOCUMENT_FOLDER = "docs"
os.makedirs(DOCUMENT_FOLDER, exist_ok=True)

app = FastAPI(title="RAG Chatbot")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def read_text(path): return open(path, "r", encoding="utf-8").read()
def read_pdf(path): return "\n".join([p.extract_text() for p in PyPDF2.PdfReader(open(path, "rb")).pages])
def read_docx(path): return "\n".join([p.text for p in docx.Document(path).paragraphs])

def read_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt": return read_text(path)
    if ext == ".pdf": return read_pdf(path)
    if ext == ".docx": return read_docx(path)
    raise ValueError(f"Unsupported file type: {ext}")

def split_text(text, chunk_size=500):
    sentences = text.replace("\n", " ").split(". ")
    chunks, chunk, size = [], [], 0
    for s in sentences:
        s = s.strip() + ("" if s.endswith(".") else ".")
        if size + len(s) > chunk_size:
            chunks.append(" ".join(chunk))
            chunk, size = [s], len(s)
        else:
            chunk.append(s)
            size += len(s)
    if chunk: chunks.append(" ".join(chunk))
    return chunks

class RAG:
    def __init__(self, key, db_path="chroma_db"):
        os.environ["OPENAI_API_KEY"] = key
        self.client = OpenAI()
        self.db = chromadb.PersistentClient(path=db_path)
        self.embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.collection = self.db.get_or_create_collection(name="docs", embedding_function=self.embed)
        self.sessions = {}

    def index_file(self, path):
        try:
            content = read_file(path)
            chunks = split_text(content)
            ids = [f"{os.path.basename(path)}_chunk_{i}" for i in range(len(chunks))]
            metas = [{"source": os.path.basename(path), "chunk": i} for i in range(len(chunks))]
            self.collection.add(documents=chunks, metadatas=metas, ids=ids)
            return len(chunks)
        except Exception as e:
            print(f"Failed to index {path}: {e}")
            return 0

    def create_session(self):
        sid = str(uuid.uuid4())
        self.sessions[sid] = []
        return sid

    def log(self, sid, role, content):
        self.sessions.setdefault(sid, []).append({"role": role, "content": content, "ts": datetime.now().isoformat()})

    def history_text(self, sid, limit=5):
        return "\n\n".join([f"{'Human' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in self.sessions.get(sid, [])[-limit:]])

    def rephrase(self, query, history):
        if not history.strip(): return query
        prompt = "Given a chat history and a follow-up question, rewrite it as a standalone question."
        try:
            res = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": f"Chat:\n{history}\n\nQuestion:\n{query}"}]
            )
            return res.choices[0].message.content.strip()
        except Exception:
            return query

    def search(self, query, k=3):
        return self.collection.query(query_texts=[query], n_results=k)

    def extract_context(self, results):
        docs = results["documents"][0]
        sources = [f"{m['source']} (chunk {m['chunk']})" for m in results["metadatas"][0]]
        return "\n\n".join(docs), sources

    def respond(self, query, context, history):
        prompt = f"""Answer based on the context and conversation history.
If unknown, say "I don't know".

Context:
{context}

History:
{history}

Human: {query}
Assistant:"""
        try:
            res = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            return f"Response error: {e}"

    def chat(self, query, session_id, top_k=3):
        history = self.history_text(session_id)
        q_final = self.rephrase(query, history)
        results = self.search(q_final, top_k)
        context, sources = self.extract_context(results)
        answer = self.respond(q_final, context, history)
        self.log(session_id, "user", query)
        self.log(session_id, "assistant", answer)
        return {"response": answer, "sources": sources, "contextualized_query": q_final}

rag = RAG(key=API_KEY)

class Query(BaseModel):
    query: str
    session_id: str
    top_k: int = 3

@app.post("/chat")
def chat(q: Query):
    return rag.chat(q.query, q.session_id, q.top_k)

@app.post("/upload/")
async def upload(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        path = os.path.join(DOCUMENT_FOLDER, file.filename)
        with open(path, "wb") as f: f.write(await file.read())
        chunks = rag.index_file(path)
        results.append({file.filename: f"{chunks} chunks"})
    return {"status": "ok", "details": results}

@app.get("/session")
def new_session():
    return {"session_id": rag.create_session()}