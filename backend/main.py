# backend/main.py
#
# Single responsibility: expose the chat system as a clean HTTP API.
# This file only handles HTTP concerns — routing, validation, responses.
# All business logic lives in chat.py and the modules it calls.

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
import uvicorn

import bible_db
import embeddings
import chat as chat_module
from safety import classify, is_image_request, BLOCKED, SENSITIVE, SAFE


class ChatMessage(BaseModel):
    role:    Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    message:      str = Field(..., min_length=1, max_length=2000)
    history:      list[ChatMessage] = Field(default_factory=list)
    denomination: Literal["general", "catholic", "protestant", "orthodox"] = "general"

class ChatResponse(BaseModel):
    type:      Literal["text", "image", "blocked"]
    response:  str
    image_url: str | None
    verified:  bool
    flagged:   list[dict]
    history:   list[dict]
    metadata:  dict

class HealthResponse(BaseModel):
    status:  str
    message: str


class SetupResponse(BaseModel):
    status:  str
    message: str


# ─────────────────────────────────────────────
# STARTUP — runs once when server starts
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[main] Server starting — running setup...")
    bible_db.setup()
    embeddings.embed_all_verses()
    print("[main] Setup complete. Server ready.")
    yield
    print("[main] Server shutting down.")

app = FastAPI(
    title="Christianity AI Assistant",
    description="Scripture-grounded Christian AI with hallucination prevention",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health", response_model=HealthResponse)
async def health():
    
    return HealthResponse(
        status="ok",
        message="Christianity AI Assistant is running."
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    
    try:
        history_dicts = [
            {"role": m.role, "content": m.content}
            for m in request.history
        ]

        result = chat_module.chat(
            user_message=request.message,
            conversation_history=history_dicts,
            denomination=request.denomination
        )

        return ChatResponse(**result)

    except Exception as e:
        # Never expose raw Python exceptions to the client
        print(f"[main] Error in /chat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An internal error occurred: {str(e)}"
        )


@app.get("/books")
async def get_books(translation: str = "KJV"):
    try:
        translation = translation.upper()
        if translation not in ["KJV", "BSB"]:
            raise HTTPException(
                status_code=400,
                detail="Translation must be KJV or BSB"
            )
        books = bible_db.get_book_list(translation)
        return {"translation": translation, "books": books}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/verse")
async def get_verse( book:str,chapter:int,verse:int,translation: str = "KJV"):
    
    result = bible_db.get_verse(translation.upper(), book, chapter, verse)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"{book} {chapter}:{verse} not found in {translation.upper()}"
        )

    return result

if __name__ == "__main__":
    uvicorn.run("main:app",host="0.0.0.0",port=8000,reload=False)