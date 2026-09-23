# AI Legal Advisor - Global AGENTS

## Scope and Precedence
- This file applies repository-wide.
- More specific rules live in:
  - `backend/AGENTS.md`
  - `frontend/AGENTS.md`
- If guidance conflicts, use the closest AGENTS file to the edited code.

## Current Repository Layout
- Backend runtime + ingestion pipelines: `backend/`
- Frontend React app: `frontend/`
- Local/experimental scripts (currently present): `scratch/`
- Root docs/design artifacts: root markdown and report files

## Data Layout Contract (Backend)
- Canonical/source datasets: `backend/data/jsons/`
- Generated datasets/artifacts: `backend/data/generated/`
- Court case datasets: `backend/data/jsons/cyber_cases/`
- Benchmark/eval outputs: `backend/tests/evaluation_results/`

## Naming and Path Standards
- Use lowercase kebab-case for new dataset filenames.
- Use descriptive names over abbreviations when practical.
- Prefer relative `Path(__file__).resolve()` pathing in Python scripts.
- Do not introduce machine-specific absolute paths.

## Change Safety Rules
- For moves/renames, update all references in the same change.
- Do not keep stale references to old file/folder names.
- Avoid destructive operations unless explicitly requested.
- Keep unrelated refactors out of targeted cleanup changes.

## Validation Expectations
- Run diagnostics/lints for changed files.
- Run at least one relevant smoke check:
  - backend change: a backend script/API/benchmark check
  - frontend change: `npm run build` and/or `npm run lint`
- If pre-existing failures block full validation, report clearly.

## Documentation Policy
- AGENTS files are operational docs for coding agents.
- Keep these docs synchronized with actual code paths/routes/scripts.
- Avoid redundant operational READMEs when AGENTS already covers it.
