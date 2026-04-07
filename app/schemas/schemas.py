from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# Auth
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    class Config:
        orm_mode= True

# Roles
class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []

class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    class Config:
        orm_mode = True

class AssignRole(BaseModel):
    user_id: int
    role_id: int

# Documents
class DocumentOut(BaseModel):
    id: int
    document_id: str
    title: str
    company_name: str
    document_type: str
    uploaded_by: int
    file_name: Optional[str]
    file_size: Optional[int]
    is_indexed: str
    created_at: datetime
    class Config:
        orm_mode = True

class DocumentSearch(BaseModel):
    title: Optional[str] = None
    company_name: Optional[str] = None
    document_type: Optional[str] = None
    uploaded_by: Optional[int] = None

# RAG
class RAGSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    document_type: Optional[str] = None
    company_name: Optional[str] = None

class ChunkResult(BaseModel):
    document_id: str
    title: str
    company_name: str
    document_type: str
    chunk_text: str
    score: float
    chunk_index: int

class RAGSearchResponse(BaseModel):
    query: str
    results: List[ChunkResult]
    total_found: int
