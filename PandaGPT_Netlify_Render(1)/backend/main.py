import os
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("AI_MODEL", "gpt-5.5")
AI_NAME = os.getenv("AI_NAME", "PandaGPT")
PERSONALITY = os.getenv(
    "AI_PERSONALITY",
    "You are a helpful, friendly, concise personal AI assistant."
)
DB = os.getenv("DATABASE_PATH", "./ai.db")

if not API_KEY:
    print("WARNING: OPENAI_API_KEY is not set.")

client = OpenAI(api_key=API_KEY) if API_KEY else None
app = FastAPI(title="My AI API", version="1.0.0")

origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        role TEXT,
        content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    con.commit()
    return con

class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str
    use_web: bool = False

class Settings(BaseModel):
    name: Optional[str] = None
    personality: Optional[str] = None

class MemoryRequest(BaseModel):
    session_id: str = "default"
    content: str

def history(session_id: str, limit: int = 30):
    con = db()
    rows = con.execute(
        "SELECT role, content FROM messages WHERE session_id=? "
        "ORDER BY created_at DESC LIMIT ?", (session_id, limit)
    ).fetchall()
    con.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

@app.get("/health")
def health():
    return {"ok": True, "name": AI_NAME, "model": MODEL}

@app.get("/settings")
def get_settings():
    return {"name": AI_NAME, "personality": PERSONALITY, "model": MODEL}

@app.get("/history/{session_id}")
def get_history(session_id: str):
    return {"messages": history(session_id, 100)}

@app.post("/memory")
def add_memory(req: MemoryRequest):
    con = db()
    con.execute(
        "INSERT INTO memories(id, session_id, content) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), req.session_id, req.content)
    )
    con.commit()
    con.close()
    return {"ok": True}

@app.get("/memory/{session_id}")
def get_memory(session_id: str):
    con = db()
    rows = con.execute(
        "SELECT content FROM memories WHERE session_id=? ORDER BY created_at DESC",
        (session_id,)
    ).fetchall()
    con.close()
    return {"memories": [r["content"] for r in rows]}

@app.post("/chat")
def chat(req: ChatRequest):
    if not client:
        raise HTTPException(500, "OPENAI_API_KEY is not configured")

    con = db()
    con.execute(
        "INSERT INTO messages(id, session_id, role, content) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), req.session_id, "user", req.message)
    )
    con.commit()
    con.close()

    memories = get_memory(req.session_id)["memories"][:20]
    memory_text = "\n".join(f"- {m}" for m in memories) or "(none)"
    instructions = (
        f"Your name is {AI_NAME}.\n{PERSONALITY}\n"
        f"Long-term user memories for this session:\n{memory_text}\n"
        "Do not claim to remember something unless it is in the provided context."
    )

    kwargs = {
        "model": MODEL,
        "instructions": instructions,
        "input": history(req.session_id),
    }
    if req.use_web:
        kwargs["tools"] = [{"type": "web_search"}]

    response = client.responses.create(**kwargs)
    answer = response.output_text

    con = db()
    con.execute(
        "INSERT INTO messages(id, session_id, role, content) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), req.session_id, "assistant", answer)
    )
    con.commit()
    con.close()

    return {"answer": answer, "session_id": req.session_id}

@app.post("/image")
def image(prompt: str):
    if not client:
        raise HTTPException(500, "OPENAI_API_KEY is not configured")
    # The image API is intentionally isolated here so the UI can call one route.
    result = client.images.generate(model="gpt-image-2", prompt=prompt)
    item = result.data[0]
    return {"image": getattr(item, "url", None), "b64_json": getattr(item, "b64_json", None)}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not client:
        raise HTTPException(500, "OPENAI_API_KEY is not configured")
    temp = Path("/tmp") / f"{uuid.uuid4()}-{file.filename}"
    temp.write_bytes(await file.read())
    try:
        with temp.open("rb") as f:
            result = client.audio.transcriptions.create(
                model="gpt-transcribe",
                file=f
            )
        return {"text": result.text}
    finally:
        temp.unlink(missing_ok=True)

@app.post("/speak")
def speak(text: str, voice: str = "alloy"):
    if not client:
        raise HTTPException(500, "OPENAI_API_KEY is not configured")
    out = Path("/tmp") / f"{uuid.uuid4()}.mp3"
    with out.open("wb") as f:
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text
        )
        response.write_to_file(out)
    return FileResponse(out, media_type="audio/mpeg", filename="speech.mp3")
