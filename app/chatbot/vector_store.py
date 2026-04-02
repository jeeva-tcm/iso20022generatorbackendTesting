"""
ISO 20022 RAG Chatbot - Vector Store
Uses TF-IDF based similarity search (no external ML dependencies required).
This is a lightweight, dependency-free alternative to FAISS/sentence-transformers.
"""

import os
import json
import math
import re
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional


class TFIDFVectorStore:
    """
    A lightweight TF-IDF based vector store that requires NO external ML libraries.
    Uses BM25-style scoring for better retrieval quality.
    """

    def __init__(self):
        self.documents: List[Dict] = []
        self.doc_tokens: List[List[str]] = []
        self.idf: Dict[str, float] = {}
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.avg_doc_len: float = 0.0
        self.is_built = False

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words, removing XML tags and special chars."""
        # Remove XML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Remove special characters but keep alphanumeric and dots
        text = re.sub(r"[^a-zA-Z0-9.\-_]", " ", text)
        # Tokenize and lowercase
        tokens = text.lower().split()
        # Remove very short tokens
        tokens = [t for t in tokens if len(t) > 1]
        return tokens

    def add_documents(self, documents: List[Dict]):
        """Add documents to the store."""
        for doc in documents:
            self.documents.append(doc)
            tokens = self._tokenize(doc["text"])
            self.doc_tokens.append(tokens)

    def build_index(self):
        """Build the TF-IDF index."""
        n_docs = len(self.documents)
        if n_docs == 0:
            return

        # Calculate document frequencies
        self.doc_freqs = defaultdict(int)
        total_len = 0

        for tokens in self.doc_tokens:
            total_len += len(tokens)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] += 1

        self.avg_doc_len = total_len / n_docs

        # Calculate IDF using BM25 formula
        self.idf = {}
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)

        self.is_built = True
        print(f"[VectorStore] Built index with {n_docs} documents, {len(self.idf)} unique terms")

    def _bm25_score(self, query_tokens: List[str], doc_idx: int, k1: float = 1.5, b: float = 0.75) -> float:
        """Calculate BM25 score for a document given a query."""
        doc_tokens = self.doc_tokens[doc_idx]
        doc_len = len(doc_tokens)
        tf_counter = Counter(doc_tokens)

        score = 0.0
        for qt in query_tokens:
            if qt not in self.idf:
                continue
            tf = tf_counter.get(qt, 0)
            idf = self.idf[qt]
            # BM25 term frequency normalization
            tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / self.avg_doc_len))
            score += idf * tf_norm

        return score

    def search(self, query: str, top_k: int = 8, category_filter: Optional[str] = None) -> List[Dict]:
        """Search for the most relevant documents."""
        if not self.is_built:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Add synonyms / expansions for common ISO 20022 terms
        expanded = list(query_tokens)
        query_lower = query.lower()

        # Domain-specific query expansions
        expansions = {
            "pacs": ["pacs", "payment", "clearing", "settlement", "credit", "transfer"],
            "camt": ["camt", "cash", "management", "statement", "report", "notification"],
            "pain": ["pain", "payment", "initiation", "customer", "bank"],
            "mt103": ["mt103", "mt", "103", "customer", "transfer", "pacs.008"],
            "mt202": ["mt202", "mt", "202", "financial", "institution", "pacs.009"],
            "iban": ["iban", "account", "identifier", "bban"],
            "bic": ["bic", "bicfi", "swift", "code", "financial", "institution"],
            "mandate": ["mandate", "direct", "debit", "pain.008"],
            "creditor": ["creditor", "cdtr", "beneficiary"],
            "debtor": ["debtor", "dbtr", "ordering", "customer"],
            "validation": ["validation", "validate", "check", "rule", "error"],
            "schema": ["schema", "xsd", "xml", "structure", "definition"],
        }

        for key, synonyms in expansions.items():
            if key in query_lower:
                expanded.extend(synonyms)

        # Remove duplicates
        expanded = list(set(expanded))

        # Score all documents
        scores = []
        for idx in range(len(self.documents)):
            # Apply category filter if specified
            if category_filter:
                doc_cat = self.documents[idx].get("metadata", {}).get("category", "")
                if doc_cat and doc_cat.upper() != category_filter.upper():
                    continue

            score = self._bm25_score(expanded, idx)
            if score > 0:
                scores.append((idx, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top-k results
        results = []
        for idx, score in scores[:top_k]:
            result = {
                "text": self.documents[idx]["text"],
                "metadata": self.documents[idx]["metadata"],
                "score": round(score, 4),
            }
            results.append(result)

        return results

    def save(self, path: str):
        """Save the vector store to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "documents": self.documents,
            "doc_tokens": self.doc_tokens,
            "idf": self.idf,
            "doc_freqs": dict(self.doc_freqs),
            "avg_doc_len": self.avg_doc_len,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        print(f"[VectorStore] Saved to {path}")

    def load(self, path: str) -> bool:
        """Load the vector store from disk."""
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.documents = data["documents"]
            self.doc_tokens = data["doc_tokens"]
            self.idf = data["idf"]
            self.doc_freqs = defaultdict(int, data["doc_freqs"])
            self.avg_doc_len = data["avg_doc_len"]
            self.is_built = True
            print(f"[VectorStore] Loaded {len(self.documents)} documents from {path}")
            return True
        except Exception as e:
            print(f"[VectorStore] Failed to load: {e}")
            return False

    @property
    def size(self) -> int:
        return len(self.documents)
