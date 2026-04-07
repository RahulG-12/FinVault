"""
RAG Service: Text extraction → Chunking → Embeddings → Vector DB → Reranking
Uses sentence-transformers for embeddings and in-memory FAISS-like store
(Qdrant-compatible interface, swappable with real Qdrant)
"""
import re
import uuid
import math
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings


class TextChunker:
    """Semantic chunker for financial documents."""

    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        chunks = []
        current = []
        current_len = 0

        for sentence in sentences:
            words = sentence.split()
            if current_len + len(words) > self.chunk_size and current:
                chunks.append(" ".join(current))
                # Keep overlap
                overlap_words = current[-self.overlap:] if len(current) > self.overlap else current
                current = overlap_words + words
                current_len = len(current)
            else:
                current.extend(words)
                current_len += len(words)

        if current:
            chunks.append(" ".join(current))

        return [c for c in chunks if len(c.strip()) > 20]


class SimpleEmbedder:
    """
    Lightweight TF-IDF-style embedder for financial terms.
    In production, swap with sentence-transformers or OpenAI embeddings.
    """
    FINANCIAL_TERMS = [
        "revenue", "profit", "loss", "debt", "equity", "asset", "liability",
        "cash", "flow", "margin", "ebitda", "eps", "dividend", "yield",
        "risk", "portfolio", "investment", "return", "balance", "sheet",
        "income", "statement", "audit", "compliance", "tax", "depreciation",
        "amortization", "capital", "expenditure", "budget", "forecast",
        "variance", "ratio", "leverage", "liquidity", "solvency", "interest",
        "loan", "credit", "invoice", "payment", "contract", "agreement",
        "quarterly", "annual", "fiscal", "gross", "net", "operating",
    ]

    def __init__(self, dim: int = 128):
        self.dim = dim
        self.vocab = {term: i for i, term in enumerate(self.FINANCIAL_TERMS)}

    def embed(self, text: str) -> List[float]:
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        vec = [0.0] * self.dim

        for word in words:
            if word in self.vocab:
                idx = self.vocab[word] % self.dim
                vec[idx] += 1.0

        # Add character n-gram features for remaining dims
        for i, char in enumerate(text_lower[:self.dim]):
            vec[i % self.dim] += ord(char) / 1000.0

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return max(0.0, min(1.0, dot))


class InMemoryVectorStore:
    """
    In-memory vector store with Qdrant-compatible interface.
    Swap with real Qdrant client for production:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    """

    def __init__(self):
        self._store: Dict[str, Dict] = {}  # chunk_id -> {vector, payload}

    def upsert(self, points: List[Dict]):
        for point in points:
            self._store[point["id"]] = {
                "vector": point["vector"],
                "payload": point["payload"],
            }

    def search(self, query_vector: List[float], top_k: int = 20,
               filters: Optional[Dict] = None) -> List[Dict]:
        results = []
        for chunk_id, data in self._store.items():
            # Apply filters
            if filters:
                match = True
                for key, val in filters.items():
                    if data["payload"].get(key) != val:
                        match = False
                        break
                if not match:
                    continue

            sim = _embedder.cosine_similarity(query_vector, data["vector"])
            results.append({
                "id": chunk_id,
                "score": sim,
                "payload": data["payload"],
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def delete_by_document(self, document_id: str):
        keys_to_delete = [
            k for k, v in self._store.items()
            if v["payload"].get("document_id") == document_id
        ]
        for k in keys_to_delete:
            del self._store[k]

    def count_by_document(self, document_id: str) -> int:
        return sum(
            1 for v in self._store.values()
            if v["payload"].get("document_id") == document_id
        )


class FinancialReranker:
    """
    Financial domain reranker. In production, use cross-encoder models like:
    - cross-encoder/ms-marco-MiniLM-L-6-v2
    - BAAI/bge-reranker-base
    """
    BOOST_TERMS = {
        "risk": 1.3, "debt": 1.25, "ratio": 1.2, "liability": 1.2,
        "default": 1.3, "loss": 1.25, "audit": 1.2, "fraud": 1.35,
        "compliance": 1.2, "penalty": 1.3, "breach": 1.3, "overdue": 1.25,
        "deficit": 1.25, "negative": 1.1, "decrease": 1.1, "decline": 1.1,
    }

    def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
        query_lower = query.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower))

        for r in results:
            score = r["score"]
            chunk_text = r["payload"].get("chunk_text", "").lower()
            chunk_words = set(re.findall(r'\b\w+\b', chunk_text))

            # Term overlap boost
            overlap = len(query_words & chunk_words) / (len(query_words) + 1)
            score += overlap * 0.2

            # Financial risk term boost
            for term, boost in self.BOOST_TERMS.items():
                if term in query_lower and term in chunk_text:
                    score *= boost

            # Length normalization
            word_count = len(chunk_text.split())
            if 50 < word_count < 300:
                score *= 1.05

            r["rerank_score"] = score

        results.sort(key=lambda x: x["rerank_score"], reverse=True)
        return results[:top_k]


# Singletons
_chunker = TextChunker(settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
_embedder = SimpleEmbedder(settings.EMBEDDING_DIM)
_vector_store = InMemoryVectorStore()
_reranker = FinancialReranker()


class RAGService:
    """Main RAG orchestration service."""

    @staticmethod
    def index_document(document_id: str, title: str, company_name: str,
                       document_type: str, text: str) -> int:
        """Pipeline: Text → Chunks → Embeddings → Vector DB"""
        # Remove existing chunks
        _vector_store.delete_by_document(document_id)

        chunks = _chunker.chunk(text)
        if not chunks:
            return 0

        points = []
        for i, chunk in enumerate(chunks):
            vector = _embedder.embed(chunk)
            points.append({
                "id": f"{document_id}_chunk_{i}",
                "vector": vector,
                "payload": {
                    "document_id": document_id,
                    "title": title,
                    "company_name": company_name,
                    "document_type": document_type,
                    "chunk_text": chunk,
                    "chunk_index": i,
                }
            })

        _vector_store.upsert(points)
        return len(chunks)

    @staticmethod
    def remove_document(document_id: str) -> int:
        count = _vector_store.count_by_document(document_id)
        _vector_store.delete_by_document(document_id)
        return count

    @staticmethod
    def search(query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Pipeline:
        Query → Embedding → Vector Search (top 20) → Reranking → Top K
        """
        query_vector = _embedder.embed(query)

        # Stage 1: Vector search — top 20
        raw_results = _vector_store.search(
            query_vector,
            top_k=settings.TOP_K_VECTOR,
            filters=filters
        )

        if not raw_results:
            return []

        # Stage 2: Reranking → top 5 (or top_k)
        reranked = _reranker.rerank(query, raw_results, top_k=top_k)
        return reranked

    @staticmethod
    def get_document_context(document_id: str) -> List[Dict]:
        """Retrieve all chunks for a document."""
        results = []
        for chunk_id, data in _vector_store._store.items():
            if data["payload"].get("document_id") == document_id:
                results.append({
                    "chunk_id": chunk_id,
                    "chunk_index": data["payload"].get("chunk_index", 0),
                    "chunk_text": data["payload"].get("chunk_text", ""),
                    "document_id": document_id,
                })
        results.sort(key=lambda x: x["chunk_index"])
        return results


rag_service = RAGService()
