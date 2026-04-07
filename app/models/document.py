from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, unique=True, index=True)
    title = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    document_type = Column(String, nullable=False)  # invoice, report, contract
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    file_path = Column(String)
    file_name = Column(String)
    content_text = Column(Text)
    file_size = Column(Integer)
    mime_type = Column(String)
    is_indexed = Column(String, default="pending")  # pending, indexed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
