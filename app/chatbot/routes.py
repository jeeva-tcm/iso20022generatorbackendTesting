"""
ISO 20022 RAG Chatbot - FastAPI Routes
Provides /chatbot/* endpoints for the chatbot UI.
"""

import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional

from .chat_service import chat_service

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Directory for uploaded reference documents
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list
    processing_time_ms: int
    has_llm: bool = False


@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """Ask a question about ISO 20022 / SWIFT messaging."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    result = await chat_service.chat(request.question, request.session_id)
    return result


@router.api_route("/stats", methods=["GET", "HEAD"])
def get_chatbot_stats():
    """Get knowledge base statistics."""
    return chat_service.get_stats()


@router.api_route("/suggestions", methods=["GET", "HEAD"])
def get_suggestions():
    """Get suggested questions for the chatbot."""
    return {
        "suggestions": [
            "What is pacs.008 and what fields does it contain?",
            "Explain the difference between MT103 and pacs.008",
            "What validation rules apply to IBAN fields?",
            "What is the structure of a camt.052 message?",
            "How does the MT-to-MX conversion work for MT202?",
            "What are the mandatory fields in pain.001?",
            "Explain the BIC/BICFI validation rules",
            "What is the purpose of camt.055 (Payment Cancellation)?",
            "What are the Layer 1, 2, and 3 validation checks?",
            "How is the creditor agent (CdtrAgt) structured in pacs.008?",
        ]
    }


@router.post("/rebuild")
def rebuild_knowledge_base():
    """Force rebuild the knowledge base index."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    count = chat_service.rebuild_index(base_dir)
    return {"status": "rebuilt", "total_chunks": count}


@router.post("/upload")
async def upload_reference_document(file: UploadFile = File(...)):
    """Upload a reference document to expand the knowledge base."""
    allowed_extensions = {".txt", ".json", ".xml", ".xsd", ".csv", ".md"}
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(allowed_extensions)}",
        )

    # Save file
    file_path = os.path.join(UPLOADS_DIR, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Ingest into knowledge base
    chunks_added = chat_service.add_uploaded_document(file_path, file.filename)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "chunks_added": chunks_added,
        "total_chunks": chat_service.vector_store.size,
    }


