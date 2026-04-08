from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.database import engine, Base

# ✅ MUST import models before create_all so tables are registered
from app.models.user import User
from app.models.document import Document
from app.models.role import Role

from app.api.routes import auth, documents, roles, users, rag

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FinVault - Financial Document Intelligence",
    description="AI-powered financial document management with semantic analysis",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://fin-vault-woad.vercel.app",
    "https://finvault.vercel.app",
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    origin = request.headers.get("origin", "")
    response = JSONResponse(content={"detail": "OK"}, status_code=200)
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "600"
    return response

app.include_router(auth.router,      prefix="/auth",      tags=["Authentication"])
app.include_router(documents.router, prefix="/documents",  tags=["Documents"])
app.include_router(roles.router,     prefix="/roles",      tags=["Roles"])
app.include_router(users.router,     prefix="/users",      tags=["Users"])
app.include_router(rag.router,       prefix="/rag",        tags=["RAG & Semantic Search"])

@app.get("/")
def root():
    return {"message": "FinVault API is running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}