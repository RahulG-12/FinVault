from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, documents, roles, users, rag
from app.core.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FinVault - Financial Document Intelligence",
    description="AI-powered financial document management with semantic analysis",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(roles.router, prefix="/roles", tags=["Roles"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(rag.router, prefix="/rag", tags=["RAG & Semantic Search"])

@app.get("/")
def root():
    return {"message": "FinVault API is running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}
