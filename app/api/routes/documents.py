import uuid
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.document import Document
from app.models.user import User
from app.schemas.schemas import DocumentOut, DocumentSearch

router = APIRouter()
UPLOAD_DIR = "/tmp/finvault_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = ["invoice", "report", "contract"]

@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    title: str = Form(...),
    company_name: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if document_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"document_type must be one of: {ALLOWED_TYPES}")

    content = await file.read()
    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(content)

    # Extract text (basic extraction — production should use PyMuPDF, pdfplumber, etc.)
    try:
        text_content = content.decode("utf-8", errors="ignore")
    except Exception:
        text_content = ""

    doc = Document(
        document_id=doc_id,
        title=title,
        company_name=company_name,
        document_type=document_type,
        uploaded_by=current_user.id,
        file_path=file_path,
        file_name=file.filename,
        content_text=text_content,
        file_size=len(content),
        mime_type=file.content_type,
        is_indexed="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

@router.get("", response_model=List[DocumentOut])
def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Document).offset(skip).limit(limit).all()

@router.get("/search", response_model=List[DocumentOut])
def search_documents(
    title: Optional[str] = Query(None),
    company_name: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Document)
    if title:
        q = q.filter(Document.title.ilike(f"%{title}%"))
    if company_name:
        q = q.filter(Document.company_name.ilike(f"%{company_name}%"))
    if document_type:
        q = q.filter(Document.document_type == document_type)
    return q.all()

@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc

@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    # Remove from vector store too
    from app.services.rag_service import rag_service
    rag_service.remove_document(document_id)
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted", "document_id": document_id}
