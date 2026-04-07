from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.document import Document
from app.services.rag_service import rag_service
from app.schemas.schemas import RAGSearchRequest, RAGSearchResponse, ChunkResult

router = APIRouter()

@router.post("/index-document")
def index_document(document_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Generate embeddings and store in vector DB."""
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if not doc.content_text:
        raise HTTPException(400, "Document has no extractable text content")

    num_chunks = rag_service.index_document(
        document_id=doc.document_id,
        title=doc.title,
        company_name=doc.company_name,
        document_type=doc.document_type,
        text=doc.content_text,
    )

    doc.is_indexed = "indexed"
    db.commit()

    return {
        "message": "Document indexed successfully",
        "document_id": document_id,
        "chunks_created": num_chunks,
        "pipeline": "Text → Chunking → Embeddings → Vector DB",
    }

@router.delete("/remove-document/{document_id}")
def remove_document_embeddings(document_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Remove document embeddings from vector DB."""
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    removed = rag_service.remove_document(document_id)
    doc.is_indexed = "pending"
    db.commit()

    return {"message": "Embeddings removed", "document_id": document_id, "chunks_removed": removed}

@router.post("/search", response_model=RAGSearchResponse)
def semantic_search(req: RAGSearchRequest, current_user=Depends(get_current_user)):
    """
    Semantic search pipeline:
    Query → Embedding → Vector Search (top 20) → Reranking → Top 5 Results
    """
    filters = {}
    if req.document_type:
        filters["document_type"] = req.document_type
    if req.company_name:
        filters["company_name"] = req.company_name

    results = rag_service.search(
        query=req.query,
        top_k=req.top_k or 5,
        filters=filters or None,
    )

    chunk_results = []
    for r in results:
        p = r["payload"]
        chunk_results.append(ChunkResult(
            document_id=p["document_id"],
            title=p["title"],
            company_name=p["company_name"],
            document_type=p["document_type"],
            chunk_text=p["chunk_text"],
            score=round(r.get("rerank_score", r["score"]), 4),
            chunk_index=p.get("chunk_index", 0),
        ))

    return RAGSearchResponse(
        query=req.query,
        results=chunk_results,
        total_found=len(chunk_results),
    )

@router.get("/context/{document_id}")
def get_document_context(document_id: str, current_user=Depends(get_current_user)):
    """Retrieve all indexed chunks for a document."""
    chunks = rag_service.get_document_context(document_id)
    if not chunks:
        raise HTTPException(404, "No indexed content found for this document")
    return {
        "document_id": document_id,
        "total_chunks": len(chunks),
        "chunks": chunks,
    }
