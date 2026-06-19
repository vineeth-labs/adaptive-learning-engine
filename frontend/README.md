# Assessment Learner — Frontend

A Vite + React + TypeScript dashboard for the AI Competency Mapping backend. It answers the two
questions the product cares about: **"Where am I?"** (mastery radar + concept breakdown) and
**"What do I do next?"** (the recommendation hero).

Design reference lives in `ai_generated/dashboard/` (kept for comparison, not built).

## Requirements

- Node 18+ and npm (`brew install node`).

## Quick start (mock data — no backend needed)

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

By default `VITE_USE_MOCKS` is on (anything other than `"false"`), so the dashboard renders from
in-memory mock data shaped to the real API schema. No Postgres or backend required.

## Pointing at the live backend

1. Add CORS to the backend (already wired in `backend/main.py`) and run it:
   ```bash
   cd ..              # repo root
   source .venv/bin/activate
   PYTHONPATH=. uvicorn backend.main:app --reload   # http://localhost:8000
   ```
   Make sure Postgres is up, the curriculum is seeded
   (`python scripts/populate_java_curriculum.py`), and you have a real user UUID.
2. Configure the frontend:
   ```bash
   cp .env.example .env.local
   # in .env.local:
   #   VITE_USE_MOCKS=false
   #   VITE_API_BASE_URL=http://localhost:8000/api/v1
   #   VITE_USER_ID=<a real user UUID>
   ```
3. `npm run dev` again.

## Screens

- **Dashboard** — recommendation hero, mastery radar, concept deep-dive.
- **Take Assessment** — clicking the hero's action button starts a frontier
  assessment (`POST /assessments/next`), steps through one free-text question per
  concept, submits (`POST /assessments/{id}/submit`), and shows per-concept mastery
  updates. On completion the dashboard's competency map and recommendation are
  invalidated so they reflect the new mastery. In mock mode a deterministic local
  grader rewards longer, more substantive answers.

## Structure

```
src/
  api/        types.ts (mirror backend schemas) · client.ts · mocks.ts · hooks.ts (React Query) · config.ts
  lib/        mastery.ts — pure derivations (status thresholds, radar grouping, readiness)
  components/ ui/ · layout/ · dashboard/ · assessment/ (QuestionStep, AssessmentResults)
  pages/      Dashboard.tsx · Assessment.tsx
  App.tsx · main.tsx
```

## Scripts

- `npm run dev` — dev server
- `npm run build` — type-check + production build
- `npm run preview` — preview the build
- `npm run lint` — type-check only

## Not yet implemented

- Other nav screens (My Path, Concept Library, Analytics) are static links.
- Level / streak / display name / target role have no backend source and are static placeholders.
```
