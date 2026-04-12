# Career Planning Project

This folder is a GitHub-ready copy of the project for team collaboration.

## Included

- `backend/`: FastAPI backend, business modules, tests
- `frontend/`: React + Vite frontend source
- `docs/`: project documentation
- `data/processed/`: processed job data used by the project
- `data/interim/`: intermediate cleaned data used by import flow
- `data/seeds/`: demo and seed data
- `.env.example`: environment variable template
- `docker-compose.yml`: local startup file

## Excluded On Purpose

- `.git/`
- `.env`
- `frontend/node_modules/`
- `frontend/dist/`
- cache folders such as `__pycache__`, `.pytest_cache`
- generated output such as local report exports
- `data/raw/` and `data/archive/` to keep the shared package cleaner and smaller

## Quick Start

1. Copy environment variables

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

2. Start the project

```bash
docker compose up --build
```

3. Open the app

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Suggested Manual Test Flow

1. Open the frontend and confirm the page loads.
2. Register or log in.
3. Paste a resume text and build a student profile.
4. Run job matching and confirm recommended jobs appear.
5. Open the job graph related page or call graph APIs from Swagger.
6. Generate a career report.
7. Edit one report section, save it, refresh, and confirm the content is preserved.
8. Export the report as HTML and PDF and confirm markdown content is rendered.

## Backend Tests

Run all backend tests inside the running container:

```bash
docker exec career-planning-backend python -m pytest tests -q
```

If you only want a targeted report export check:

```bash
docker exec career-planning-backend python -m pytest tests/test_reporting_exporters.py -q
```

## Frontend Tests

If teammates want to run frontend tests locally:

```bash
cd frontend
npm install
npm test
```

## Collaboration Notes

- Keep the GitHub repo private unless you are sure the data can be shared publicly.
- Do not commit `.env` or any personal API key.
- Prefer feature branches and pull requests for collaboration.
- If new seed data is needed, put shareable data under `data/seeds/` or `data/processed/`.

## Recommended First Commit

After placing this folder in its own git repository, the first commit message can be:

```text
chore: add github-ready collaboration copy of career planning project
```
