# FinVault — Financial Document Intelligence Platform

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the API
uvicorn app.main:app --reload --port 8000

# 3. Open the UI
open frontend/index.html
# Or serve it: python -m http.server 3000 --directory frontend
```

## API Documentation
- Swagger UI: http://localhost:8000/api/docs
- ReDoc:       http://localhost:8000/api/redoc

## Default Demo User
Register via POST /auth/register or via the UI, then:
- POST /roles/seed-defaults   → creates Admin, Financial Analyst, Auditor, Client roles

---

## Architecture

```
FinVault/
├── app/
│   ├── main.py                    # FastAPI app entrypoint
│   ├── core/
│   │   ├── config.py              # Settings (env vars)
│   │   ├── database.py            # SQLAlchemy engine
│   │   └── security.py            # JWT auth + RBAC helpers
│   ├── models/
│   │   ├── user.py                # User ORM model
│   │   ├── document.py            # Document ORM model
│   │   └── role.py                # Role, UserRole, RolePermission
│   ├── schemas/
│   │   └── schemas.py             # Pydantic request/response models
│   ├── services/
│   │   └── rag_service.py         # RAG pipeline (chunk→embed→store→rerank)
│   └── api/routes/
│       ├── auth.py                # POST /auth/register, /auth/login
│       ├── documents.py           # CRUD + upload
│       ├── roles.py               # Role management
│       ├── users.py               # User + role assignment
│       └── rag.py                 # Index, search, context
└── frontend/
    └── index.html                 # Full SPA UI
```

---

## API Endpoints

### Authentication
| Method | Endpoint          | Description          |
|--------|-------------------|----------------------|
| POST   | /auth/register    | Register a new user  |
| POST   | /auth/login       | Get JWT token        |

### Documents
| Method | Endpoint                        | Description              |
|--------|---------------------------------|--------------------------|
| POST   | /documents/upload               | Upload financial document|
| GET    | /documents                      | Retrieve all documents   |
| GET    | /documents/{document_id}        | Get document details     |
| DELETE | /documents/{document_id}        | Delete document          |
| GET    | /documents/search               | Search by metadata       |

### Roles & Users (RBAC)
| Method | Endpoint                    | Description             |
|--------|-----------------------------|-------------------------|
| POST   | /roles/create               | Create a role           |
| POST   | /roles/seed-defaults        | Seed default roles      |
| POST   | /users/assign-role          | Assign role to user     |
| GET    | /users/{id}/roles           | Get user's roles        |
| GET    | /users/{id}/permissions     | Get user permissions    |

### RAG & Semantic Search
| Method | Endpoint                         | Description                      |
|--------|----------------------------------|----------------------------------|
| POST   | /rag/index-document              | Generate embeddings → vector DB  |
| DELETE | /rag/remove-document/{id}        | Remove document embeddings       |
| POST   | /rag/search                      | Semantic search (with reranking) |
| GET    | /rag/context/{document_id}       | Get document context chunks      |

---

## RAG Pipeline

```
Document Upload
     ↓
Text Extraction (UTF-8 / PyMuPDF for PDF)
     ↓
Semantic Chunking (512 tokens, 64 overlap)
     ↓
Financial Embeddings (sentence-transformers/all-MiniLM-L6-v2)
     ↓
Vector Database (Qdrant / in-memory fallback)
     ↓
─── At Query Time ──────────────────────────
User Query → Embedding → Vector Search (Top 20)
     ↓
Financial Domain Reranker
     ↓
Top 5 Most Relevant Chunks
```

## Role Permissions Matrix

| Role               | documents:read | documents:write | documents:delete | users:manage | rag:search | rag:index |
|--------------------|:-:|:-:|:-:|:-:|:-:|:-:|
| Admin              | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Financial Analyst  | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Auditor            | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Client             | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Production Upgrades
- Swap in-memory store with real **Qdrant**: `qdrant-client`
- Swap `SimpleEmbedder` with **sentence-transformers** or OpenAI embeddings
- Swap `FinancialReranker` with **BAAI/bge-reranker-base** (cross-encoder)
- Add **PyMuPDF** / **pdfplumber** for proper PDF text extraction
- Use **LangChain** document loaders for multi-format support
- Replace SQLite with **PostgreSQL** for production
