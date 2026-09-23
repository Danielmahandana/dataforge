# DARKROOM DATAFORGE
### Wits–merSETA Darkroom Structured Data Extraction, Validation & Dataset Generation Platform

![Architecture](https://img.shields.io/badge/Architecture-FastAPI%20%2B%20React%20%2B%20TypeScript-1D3557?style=flat-square)
![Frontend](https://img.shields.io/badge/Frontend-Vite%20%7C%20TailwindCSS%20%7C%20Zustand-D4AF37?style=flat-square)
![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20SQLAlchemy%20%7C%20PyMuPDF-22C55E?style=flat-square)
![Storage](https://img.shields.io/badge/Databases-PostgreSQL%20%7C%20SQLite%20Fallback-0ea5e9?style=flat-square)

---

## 1. Overview & Purpose

**Darkroom DataForge** is a centralized, research-grade document intelligence and structured-data extraction web workstation built specifically for the **Wits–merSETA Darkroom** team.

The platform converts complex collections of semi-structured PDF documents—such as **South African Quarterly Labour Force Survey (QLFS) codebooks**, **Public TVET College Occupational Qualifications lists**, **Occupations in High Demand (OIHD) reports**, and technical research annexures—into clean, validated, database-ready machine-readable datasets.

Unlike simplistic "PDF to CSV" converters, Darkroom DataForge implements an end-to-end data engineering pipeline:
- **Zero Blind Trust**: Every cell and record preserves internal provenance (`document_id`, `document_name`, `page_number`, `table_index`, `extraction_method`, `confidence_score`).
- **Embedded Source PDF Viewer**: Instant page-synchronized inspection via the `[ View Source ]` button on any record, jumping directly to the exact source page.
- **Archetype Classification**: Automatically determines whether a PDF is a TVET qualification catalogue, an OIHD occupational priority list, a survey codebook, or general tables.
- **Table Healing & Normalization**: Merges multi-page tables, removes repeated headers across page breaks, standardizes South African provinces, cleans Unicode ligatures, and handles null tokens.
- **Human-in-the-Loop Review**: Low-confidence extractions and schema anomalies are queued for operator inspection with full review audit trails (`HUMAN_REVIEWED`).
- **Multi-Format Export**: One-click exports to CSV, JSON, and Excel (.xlsx) with configurable provenance metadata columns.

---

## 2. Monorepo Architecture

The repository is organized into a clean full-stack monorepo:

```
Darkroom DataForge/
├── backend/                        # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/                 # REST API endpoints (projects, documents, extraction, datasets, records, validation, review, exports)
│   │   ├── config.py               # Pydantic-settings configuration with .env support
│   │   ├── database.py             # SQLAlchemy engine (PostgreSQL + SQLite fallback)
│   │   ├── extractors/             # Specialized parsers (Qualifications, Occupations, Codebook, PdfTables)
│   │   ├── models/                 # SQLAlchemy ORM models (Project, Document, ExtractionJob, Dataset, Record, ValidationIssue, ReviewAudit, ActivityLog)
│   │   ├── pipeline/               # Pipeline engine, Normalizer, SchemaDetector, Validator, Exporter
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── storage/                # Local filesystem storage manager
│   │   └── main.py                 # FastAPI application entry point with CORS
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile                  # Container definition
│
├── frontend/                       # Vite + React + TypeScript Frontend
│   ├── src/
│   │   ├── components/             # Layout (Header, Sidebar), Badges, ProgressBar, SourceDocumentModal
│   │   ├── pages/                  # Dashboard, Projects, Documents, Pipeline, Datasets, DatasetDetails, Validation, Review, Exports
│   │   ├── services/api.ts         # Axios API client with full type safety
│   │   ├── store/useAppStore.ts    # Zustand global state (project scope, source modal)
│   │   ├── types/index.ts          # TypeScript domain interfaces
│   │   ├── App.tsx                 # React Router routing table
│   │   └── main.tsx                # Entry point
│   ├── package.json                # Frontend dependencies
│   ├── tailwind.config.js          # Darkroom palette tokens (#0B1020, #1D3557, #D4AF37)
│   ├── nginx.conf                  # Production reverse proxy config
│   └── Dockerfile                  # Multi-stage production container
│
├── storage/                        # Persistent file workspace
│   ├── uploads/                    # Ingested PDF documents
│   ├── raw/                        # Raw extraction dumps
│   ├── processed/                  # Normalized artifacts
│   ├── exports/                    # Generated CSV, JSON, XLSX exports
│   └── temp/                       # Temporary processing scratch space
│
├── tests/                          # Automated test suite
│   ├── test_api_v1.py              # API endpoint tests
│   └── test_pipeline_e2e.py        # End-to-end pipeline integration tests
│
├── docker-compose.yml              # Multi-container stack (Postgres, Redis, Backend, Frontend)
├── Makefile                        # CLI convenience commands
└── .env.example                    # Environment variable template
```

---

## 3. Quick Start Guide

### Option A: Running with Docker Compose (Production Stack)

Ensure Docker is installed and running, then:

```bash
# 1. Start all containers (Postgres, Redis, Backend, Frontend)
docker compose up -d --build

# 2. Access the applications
# Frontend Workstation: http://localhost:5173
# Backend Swagger Docs: http://localhost:8000/docs
```

### Option B: Local Development (Instant Setup)

Darkroom DataForge automatically defaults to SQLite (`sqlite:///./storage/dataforge.db`) and in-process async workers when PostgreSQL/Redis are not running locally.

#### 1. Backend Setup
```bash
# Activate virtual environment
.venv\Scripts\activate

# Install requirements
pip install -r backend/requirements.txt

# Start backend dev server
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

#### 2. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install packages
npm install

# Start Vite dev server
npm run dev
# Open http://localhost:5173
```

---

## 4. Key Endpoints (API v1)

| Route | Method | Description |
|---|---|---|
| `/api/v1/health` | GET | System and database telemetry |
| `/api/v1/projects` | GET / POST | List or create research projects |
| `/api/v1/documents/upload` | POST | Ingest & auto-classify single or multiple PDFs |
| `/api/v1/documents/{id}/inspect` | GET | Inspect page dimensions, text layer, detected tables |
| `/api/v1/documents/{id}/file` | GET | Stream PDF for embedded viewer |
| `/api/v1/extraction/jobs` | POST / GET | Trigger or monitor extraction jobs |
| `/api/v1/datasets` | GET / DELETE | Manage normalized structured datasets |
| `/api/v1/datasets/{id}/records` | GET | Paginated record viewer with search & status filters |
| `/api/v1/records/{id}` | PATCH | Edit field values with automated audit trail |
| `/api/v1/validation/datasets/{id}` | GET | Quality score breakdown and validation issues |
| `/api/v1/validation/issues/{id}/resolve` | PATCH | Resolve validation exceptions with inline fix |
| `/api/v1/review/datasets/{id}` | GET | Human-in-the-loop review audit trail |
| `/api/v1/datasets/{id}/export` | POST | Export to CSV, JSON, or Excel (.xlsx) |

---

## 5. Automated Verification

Run backend automated tests:

```bash
# In the project root with virtual environment activated:
pytest tests/test_api_v1.py tests/test_pipeline_e2e.py -v
```

Build frontend production bundle:

```bash
cd frontend
npm run build
```

---

## 6. License & Attribution

Internal research tool developed for the **Wits–merSETA Darkroom** team. All rights reserved.
