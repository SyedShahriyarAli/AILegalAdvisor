# Backend AGENTS

## Purpose
Guidance for agents editing backend API, graph-RAG logic, ingestion, scraping, and benchmark scripts.

## Runtime Entry Points
- Primary run command: `python run.py` from `backend/`
- Entrypoint file: `backend/run.py`
- Flask app + routes: `backend/app/api/routes.py`

## Core Modules
- RAG generation/retrieval: `backend/app/graph_rag/legal_graph_rag.py`
- Workflow graph: `backend/app/graph_rag/graph.py`
- Graph ingestion builder: `backend/app/graph_rag/legal_graph_builder.py`
- Query complexity: `backend/app/graph_rag/query_classifier.py`

## Current API Surface (high-value endpoints)
- Health/check: `/health`, `/api/ping`
- Query: `/api/query`
- Cases/listing: `/api/cases`
- Draft/search/auth/workspace endpoints are implemented in `routes.py`

## Data and Dataset Contracts
- Canonical laws: `backend/data/jsons/`
- Court case datasets: `backend/data/jsons/cyber_cases/`
- Generated artifacts: `backend/data/generated/`
- Evaluation outputs: `backend/tests/evaluation_results/`
- Ingestion file list source of truth: `backend/scripts/ingestion/file_paths.json`

## Court File Naming Convention
- `lahore-high-court-cyber-cases.json`
- `islamabad-high-court-cyber-cases.json`
- `peshawar-high-court-cyber-cases.json`
- `sindh-high-court-cyber-cases-<year>.json`

## Script Inventory (actively used)
- Ingestion:
  - `backend/scripts/ingestion/ingest_data.py`
  - `backend/scripts/ingestion/ingest_cases.py`
- Scraping/enrichment:
  - `backend/scripts/scrapers/extract_case_pdfs.py`
  - `backend/scripts/scrapers/enrich_combined_cases.py`
  - court-specific scrapers under `backend/scripts/scrapers/`
- Dataset generation:
  - `backend/scripts/generate_finetuning_dataset.py`
  - `backend/scripts/generate_benchmark_dataset.py`
- Benchmark:
  - `backend/tests/evaluate_benchmark.py`

## Editing Rules
- Keep path logic relative and deterministic (`Path(__file__).resolve()`).
- When renaming/moving files, update all references in scripts/routes in same change.
- Keep dataset naming consistent with kebab-case convention.
- Do not hardcode machine-local absolute paths.

## Validation Checklist
- For ingestion/data path changes:
  - verify `ingest_cases.py`, `extract_case_pdfs.py`, `file_paths.json`
- For RAG/eval changes:
  - run `python tests/evaluate_benchmark.py` smoke check when feasible
- For API changes:
  - verify `/health` and `/api/query` behavior at minimum
