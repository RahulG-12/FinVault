"""
seed_data.py
Run this after starting the server to populate FinVault with:
  - 1 admin user (admin / admin123)
  - 4 default roles (Admin, Financial Analyst, Auditor, Client)
  - 9 sample financial documents (3 invoices, 3 reports, 3 contracts)
  - All documents auto-indexed for semantic search

Usage:
    python seed_data.py
    # or with custom base URL:
    python seed_data.py --url http://localhost:8000
"""
import argparse
import json
import os
import sys
import requests

SAMPLE_DOCS_DIR = os.path.join(os.path.dirname(__file__), "sample_documents")

DOCUMENTS = [
    # Invoices
    {
        "path": "invoices/INV-2047-AcmeCorp.txt",
        "title": "Invoice #INV-2047 — GlobalTech to Acme Corp",
        "company_name": "Acme Corporation India",
        "document_type": "invoice",
    },
    {
        "path": "invoices/INV-3312-VertexCapital.txt",
        "title": "Invoice #INV-3312 — NovaSys to Vertex Capital",
        "company_name": "Vertex Capital Management",
        "document_type": "invoice",
    },
    {
        "path": "invoices/INV-0891-MeridianAdvisors.txt",
        "title": "Invoice #INV-0891 — PrimeAudit to Meridian (OVERDUE)",
        "company_name": "Meridian Financial Advisors",
        "document_type": "invoice",
    },
    # Reports
    {
        "path": "reports/Q3-FY2024-Revenue-Report-AcmeCorp.txt",
        "title": "Q3 FY2024-25 Quarterly Financial Report — Acme Corp",
        "company_name": "Acme Corporation India",
        "document_type": "report",
    },
    {
        "path": "reports/Annual-Audit-Report-GlobalTech-FY2024.txt",
        "title": "Annual Internal Audit Report FY2023-24 — GlobalTech",
        "company_name": "GlobalTech Solutions",
        "document_type": "report",
    },
    {
        "path": "reports/Risk-Assessment-VertexCapital-FY2025.txt",
        "title": "Enterprise Risk Assessment Report FY2024-25 — Vertex Capital",
        "company_name": "Vertex Capital Management",
        "document_type": "report",
    },
    # Contracts
    {
        "path": "contracts/MSA-2024-0142-NovaSys-Acme.txt",
        "title": "Master Services Agreement — NovaSys & Acme Corp",
        "company_name": "Acme Corporation India",
        "document_type": "contract",
    },
    {
        "path": "contracts/TermLoan-SBI-AcmeCorp-2022.txt",
        "title": "Term Loan Agreement — SBI & Acme Corp (INR 45 Cr)",
        "company_name": "Acme Corporation India",
        "document_type": "contract",
    },
    {
        "path": "contracts/IMA-VertexCapital-PinnaclePension-2024.txt",
        "title": "Investment Management Agreement — Vertex Capital Fund III",
        "company_name": "Vertex Capital Management",
        "document_type": "contract",
    },
]


def log(msg, status="INFO"):
    colors = {"INFO": "\033[94m", "OK": "\033[92m", "WARN": "\033[93m", "ERR": "\033[91m"}
    reset = "\033[0m"
    print(f"{colors.get(status,'')}{status:5}{reset} {msg}")


def run_seed(base_url="http://localhost:8000"):
    log(f"Seeding FinVault at {base_url}", "INFO")

    # 1. Register admin user
    log("Creating admin user (admin / admin123)...", "INFO")
    resp = requests.post(f"{base_url}/auth/register", json={
        "username": "admin",
        "email": "admin@finvault.io",
        "password": "admin123",
        "full_name": "FinVault Administrator",
    })
    if resp.status_code == 201:
        log("Admin user created", "OK")
    elif resp.status_code == 400 and "already" in resp.text:
        log("Admin user already exists", "WARN")
    else:
        log(f"Could not create admin: {resp.text}", "ERR")

    # 2. Login
    log("Logging in as admin...", "INFO")
    resp = requests.post(f"{base_url}/auth/login", json={
        "username": "admin", "password": "admin123"
    })
    if resp.status_code != 200:
        log(f"Login failed: {resp.text}", "ERR")
        sys.exit(1)
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    log("Login successful", "OK")

    # 3. Seed roles
    log("Seeding default roles...", "INFO")
    resp = requests.post(f"{base_url}/roles/seed-defaults", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("created"):
            log(f"Roles created: {', '.join(data['created'])}", "OK")
        else:
            log("Roles already exist", "WARN")
    else:
        log(f"Role seeding issue: {resp.text}", "WARN")

    # 4. Upload + index each sample document
    log(f"\nUploading {len(DOCUMENTS)} sample documents...", "INFO")
    success_count = 0

    for doc_meta in DOCUMENTS:
        file_path = os.path.join(SAMPLE_DOCS_DIR, doc_meta["path"])
        if not os.path.exists(file_path):
            log(f"File not found: {file_path}", "ERR")
            continue

        # Upload
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/documents/upload",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "title": doc_meta["title"],
                    "company_name": doc_meta["company_name"],
                    "document_type": doc_meta["document_type"],
                },
                files={"file": (os.path.basename(file_path), f, "text/plain")},
            )

        if resp.status_code != 201:
            log(f"Upload failed [{doc_meta['title'][:40]}]: {resp.text}", "ERR")
            continue

        doc = resp.json()
        doc_id = doc["document_id"]
        log(f"Uploaded: {doc_meta['title'][:55]}", "OK")

        # Index for RAG
        idx_resp = requests.post(
            f"{base_url}/rag/index-document?document_id={doc_id}",
            headers=headers,
        )
        if idx_resp.status_code == 200:
            chunks = idx_resp.json().get("chunks_created", 0)
            log(f"  └─ Indexed: {chunks} semantic chunks", "OK")
        else:
            log(f"  └─ Indexing failed: {idx_resp.text}", "WARN")

        success_count += 1

    log(f"\n{'='*60}", "INFO")
    log(f"Seeding complete: {success_count}/{len(DOCUMENTS)} documents loaded", "OK")
    log(f"API Docs: {base_url}/api/docs", "INFO")
    log(f"Login: admin / admin123", "INFO")
    log(f"{'='*60}", "INFO")

    print("\nSample RAG queries to try:")
    queries = [
        "financial risk related to high debt ratio",
        "covenant breach and default risk",
        "accounts receivable overdue collections",
        "interest coverage ratio below threshold",
        "SEBI compliance and regulatory requirements",
        "personal guarantee and security collateral",
    ]
    for q in queries:
        print(f'  POST /rag/search  {{"query": "{q}"}}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    run_seed(args.url)
