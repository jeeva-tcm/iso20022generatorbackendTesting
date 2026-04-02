"""
ISO 20022 RAG Chatbot - Chat Service
Combines retrieval with an LLM to generate answers about ISO 20022 / SWIFT messaging.
Uses OpenAI ChatGPT (GPT-4o) for generation.
Falls back to template-based answers if no API key is configured.
"""

import os
import re
import json
import time
from typing import List, Dict, Optional
from datetime import datetime

# Ensure .env is loaded from the project root
from dotenv import load_dotenv
# Search for .env in current, parent, and grandparent directories
load_dotenv() # try default CWD
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")) # same dir
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")) # parent
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")) # grandparent

from .vector_store import TFIDFVectorStore
from .ingestion import build_knowledge_base, ingest_uploaded_file

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Store directory for persistence
CHATBOT_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_STORE_PATH = os.path.join(CHATBOT_DIR, "data", "vector_store.json")
UPLOADS_DIR = os.path.join(CHATBOT_DIR, "uploads")

SYSTEM_PROMPT = """You are an expert AI assistant specialized in SWIFT ISO 20022 financial messaging standards.

Your role:
- Answer questions about ISO 20022 message types (pacs, camt, pain, etc.)
- Explain XML schema structures, fields, and their meanings
- Help with validation rules and error resolution
- Explain MT-to-MX migration and field mappings
- Provide code-level insights about validation logic

Rules:
1. ONLY use the provided context to answer. If the context doesn't contain the answer, say so honestly.
2. When referencing specific fields or types, mention the source file.
3. Use clear formatting with bullet points and code blocks where appropriate.
4. Keep answers concise but thorough.
5. If asked about a specific message type, focus your answer on that type.
6. Give DIFFERENT, SPECIFIC answers for each question based on the context provided.

Context from the ISO 20022 knowledge base:
---
{context}
---

User question: {question}
"""


class ChatService:
    """RAG-based chat service for ISO 20022 questions."""

    def __init__(self):
        self.vector_store = TFIDFVectorStore()
        self.is_initialized = False
        self.llm_provider = "fallback" # "openai" or "fallback"
        self.llm_client = None
        self.active_model = None
        self._llm_initialized = False
        # Initialize LLM immediately (dotenv has already loaded the .env file)
        self._ensure_llm()

    def _ensure_llm(self):
        """Initialize the OpenAI provider if key is available."""
        if self._llm_initialized and self.llm_client:
            return

        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key and openai_key != "your_openai_api_key_here" and HAS_OPENAI:
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=openai_key)
                self.llm_provider = "openai"
                self.active_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                print(f"[ChatService] OpenAI initialized with model: {self.active_model}")
                self._llm_initialized = True
                return
            except Exception as e:
                print(f"[ChatService] OpenAI init failed: {e}")

        self.llm_provider = "fallback"
        self.llm_client = None
        self._llm_initialized = True

    def initialize(self, base_dir: str):
        """Initialize the knowledge base. Call this on startup."""
        # Initialize LLM now (env vars are loaded by this point)
        self._ensure_llm()

        # Try loading existing vector store first
        if self.vector_store.load(VECTOR_STORE_PATH):
            self.is_initialized = True
            print(f"[ChatService] Loaded existing knowledge base ({self.vector_store.size} chunks)")
            return

        # Build from scratch
        print("[ChatService] Building knowledge base from source files...")
        documents = build_knowledge_base(base_dir)
        self.vector_store.add_documents(documents)
        self.vector_store.build_index()

        # Persist
        os.makedirs(os.path.dirname(VECTOR_STORE_PATH), exist_ok=True)
        self.vector_store.save(VECTOR_STORE_PATH)

        self.is_initialized = True
        print(f"[ChatService] Knowledge base ready ({self.vector_store.size} chunks)")

    def rebuild_index(self, base_dir: str):
        """Force rebuild the knowledge base."""
        print("[ChatService] Force rebuilding knowledge base...")
        self.vector_store = TFIDFVectorStore()

        documents = build_knowledge_base(base_dir)
        self.vector_store.add_documents(documents)
        self.vector_store.build_index()

        os.makedirs(os.path.dirname(VECTOR_STORE_PATH), exist_ok=True)
        self.vector_store.save(VECTOR_STORE_PATH)

        self.is_initialized = True
        print(f"[ChatService] Rebuild complete ({self.vector_store.size} chunks)")
        return self.vector_store.size

    def add_uploaded_document(self, file_path: str, file_name: str) -> int:
        """Add an uploaded document to the knowledge base."""
        new_docs = ingest_uploaded_file(file_path, file_name)
        if new_docs:
            self.vector_store.add_documents(new_docs)
            self.vector_store.build_index()
            self.vector_store.save(VECTOR_STORE_PATH)
        return len(new_docs)

    def _retrieve_context(self, question: str, top_k: int = 10) -> List[Dict]:
        """Retrieve relevant context chunks for a question."""
        if not self.is_initialized:
            return []
        return self.vector_store.search(question, top_k=top_k)

    def _format_context(self, results: List[Dict]) -> str:
        """Format retrieved results into a context string for the LLM."""
        parts = []
        for i, r in enumerate(results):
            source = r["metadata"].get("source", "unknown")
            doc_type = r["metadata"].get("type", "unknown")
            msg_type = r["metadata"].get("message_type", "")
            text = r["text"][:1200]  # Limit each chunk
            header = f"--- Source {i + 1}: {source}"
            if msg_type:
                header += f" (message: {msg_type})"
            header += f" | type: {doc_type} | relevance: {r['score']} ---"
            parts.append(f"{header}\n{text}")
        return "\n\n".join(parts)

    def _generate_with_llm(self, question: str, context: str) -> str:
        """Generate answer using OpenAI ChatGPT."""
        prompt = SYSTEM_PROMPT.format(context=context, question=question)
        
        try:
            if self.llm_provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model=self.active_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                return response.choices[0].message.content
                
            return None # No provider active
        except Exception as e:
            error_str = str(e)
            print(f"[ChatService] OpenAI LLM generation failed: {error_str[:300]}")
            if "insufficient_quota" in error_str or "429" in error_str:
                 return "⚠️ **OpenAI API quota exceeded.** Your plan limit has been reached. Please check your billing or wait for the quota to reset.\n\n"
            return None

    def _generate_fallback(self, question: str, results: List[Dict]) -> str:
        """Generate a structured answer without an LLM, using the retrieved chunks directly."""
        if not results:
            return (
                "I couldn't find specific information about that in the ISO 20022 knowledge base. "
                "Could you rephrase your question or ask about a specific message type (e.g., pacs.008, camt.052, pain.001)?"
            )

        answer_parts = []
        q_lower = question.lower()

        # Add a question-specific header
        answer_parts.append(f"**Regarding: \"{question}\"**\n")
        answer_parts.append("Based on the ISO 20022 knowledge base, here's what I found:\n")

        # Group results by source type
        by_type = {}
        for r in results:
            t = r["metadata"].get("type", "other")
            by_type.setdefault(t, []).append(r)

        for doc_type, items in by_type.items():
            type_labels = {
                "xsd_complex_type": "📋 Schema Definitions",
                "xsd_simple_type": "📝 Type Constraints & Enumerations",
                "xsd_overview": "📊 Message Overview",
                "validation_rule": "✅ Validation Rules",
                "mt_mapping": "🔄 MT-to-MX Mappings",
                "validator_code": "⚙️ Validation Logic",
                "uploaded_document": "📄 Reference Documents",
                "uploaded_json": "📄 Reference Data",
                "uploaded_schema": "📄 Schema Reference",
                "uploaded_text": "📄 Reference Text",
            }
            label = type_labels.get(doc_type, "📌 Related Information")
            answer_parts.append(f"\n**{label}:**\n")

            for item in items[:3]:  # Max 3 per type
                source = item["metadata"].get("source", "")
                msg_type = item["metadata"].get("message_type", "")
                complex_type = item["metadata"].get("complex_type", "")
                text = item["text"]

                # Build a descriptive sub-header
                desc = f"From `{source}`"
                if complex_type:
                    desc += f" — type **{complex_type}**"
                if msg_type:
                    desc += f" ({msg_type})"

                # Extract meaningful lines from the text
                lines = text.split("\n")
                snippet_lines = []
                for line in lines[:20]:
                    line = line.strip()
                    if line and len(line) > 5:
                        snippet_lines.append(line)

                snippet = "\n".join(snippet_lines[:10])
                if len(snippet) > 600:
                    snippet = snippet[:600] + "..."

                answer_parts.append(f"- {desc}")
                answer_parts.append(f"  ```\n  {snippet}\n  ```\n")

        # Check if we should show instructions on how to enable AI
        if self.llm_provider == "fallback":
            openai_key = os.getenv("OPENAI_API_KEY", "")
            
            if not openai_key or openai_key == "your_openai_api_key_here":
                answer_parts.append(
                    "\n💡 *Tip: For more precise AI-powered answers, set OPENAI_API_KEY in the backend .env file.*"
                )
            else:
                 answer_parts.append(
                    "\n⚠️ *Note: OpenAI API key is configured but initialization failed. Check your API plan or quota.*"
                )

        return "\n".join(answer_parts)

    async def chat(self, question: str, session_id: str = "") -> Dict:
        """
        Main chat endpoint. Retrieves context and generates an answer.
        """
        start_time = time.time()

        # Ensure LLM is initialized (lazy init after .env is loaded)
        self._ensure_llm()

        if not self.is_initialized:
            return {
                "answer": "The chatbot knowledge base is still initializing. Please try again in a moment.",
                "sources": [],
                "processing_time_ms": 0,
            }

        # 1) Retrieve relevant context
        results = self._retrieve_context(question, top_k=10)

        # 2) Generate answer
        if self.llm_client and results:
            context_str = self._format_context(results)
            answer = self._generate_with_llm(question, context_str)
            if not answer:
                answer = self._generate_fallback(question, results)
        else:
            answer = self._generate_fallback(question, results)

        # 3) Extract source references
        sources = []
        seen_sources = set()
        for r in results:
            src = r["metadata"].get("source", "")
            if src and src not in seen_sources:
                seen_sources.add(src)
                sources.append({
                    "file": src,
                    "type": r["metadata"].get("type", ""),
                    "relevance": r["score"],
                })

        elapsed_ms = round((time.time() - start_time) * 1000)

        return {
            "answer": answer,
            "sources": sources[:6],
            "processing_time_ms": elapsed_ms,
            "has_llm": self.llm_client is not None,
        }

    def get_stats(self) -> Dict:
        """Get chatbot knowledge base statistics."""
        self._ensure_llm()

        if not self.is_initialized:
            return {"status": "not_initialized", "total_chunks": 0}

        # Count by type
        type_counts = {}
        for doc in self.vector_store.documents:
            t = doc.get("metadata", {}).get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "status": "ready",
            "total_chunks": self.vector_store.size,
            "chunks_by_type": type_counts,
            "has_llm": self.llm_client is not None,
            "llm_provider": f"ChatGPT ({self.active_model})" if self.llm_client else "Fallback (no API key)",
        }


# Singleton instance
chat_service = ChatService()
