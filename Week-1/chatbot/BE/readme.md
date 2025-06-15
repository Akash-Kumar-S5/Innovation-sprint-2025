# RAG Chatbot API (FastAPI + ChromaDB + OpenAI)

This is a simple Retrieval-Augmented Generation (RAG) chatbot backend built with FastAPI. It indexes documents and answers questions using GPT-4o-mini via OpenAI.

---

### 📤 Upload Documents

curl -X POST http://localhost:8000/upload/ \
  -F "files=@/path/to/your/file1.txt" \
  -F "files=@/path/to/your/file2.pdf"
  
### create a session

curl http://localhost:8000/session

### query

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What products does GreenGrow make?",
    "session_id": "your-session-id-here",
    "top_k": 3
  }'

## !important create .env
OPENAI_API_KEY=sk-...your-key-here...


## to run

pip install -r requirements.txt
uvicorn chatbot:app --reload