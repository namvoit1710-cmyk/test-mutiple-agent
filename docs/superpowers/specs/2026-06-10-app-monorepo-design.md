# Design: `app/` Source of Truth Monorepo

**Date:** 2026-06-10
**Status:** Approved

## Overview

Add an `app/` folder at the repo root as the single source of truth for the target application. It contains a blank FastAPI backend, a blank React frontend, and a `docs/` folder for specs and plans. This serves as the demo target that the opencode-agents system operates on.

## Folder Structure

```
opencode-agents/
└── app/
    ├── be/                  # FastAPI backend skeleton
    │   ├── main.py
    │   ├── requirements.txt
    │   └── Dockerfile
    ├── fe/                  # React (Vite + TypeScript) frontend skeleton
    │   ├── src/
    │   │   └── App.tsx
    │   ├── package.json
    │   └── Dockerfile
    └── docs/
        ├── spec/            # Requirements and design specs (planner input)
        └── plan/            # Task breakdowns and implementation plans (planner output)
```

## Components

### `app/be/` — Backend Skeleton
- FastAPI application with a single `GET /health` endpoint returning `{"status": "ok"}`
- `requirements.txt` with `fastapi` and `uvicorn`
- `Dockerfile` for containerized runs
- No database, no auth — intentionally blank

### `app/fe/` — Frontend Skeleton
- React + TypeScript app scaffolded with Vite
- Single `App.tsx` rendering a "Hello World" page
- `Dockerfile` for containerized runs
- No routing, no state management — intentionally blank

### `app/docs/` — Documentation
- `spec/` — input folder: requirements, design specs written before coding
- `plan/` — output folder: task breakdowns and implementation plans from the planner agent

## Rationale

Co-locating `app/` inside the `opencode-agents` repo keeps the demo target immediately available without extra repos or submodule complexity. The blank skeleton gives agents a valid, runnable base to build on top of without any domain assumptions baked in.
