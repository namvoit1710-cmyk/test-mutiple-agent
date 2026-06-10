# App Monorepo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an `app/` folder at the repo root containing a blank FastAPI backend, a blank React+TypeScript frontend, and a `docs/` folder for specs and plans.

**Architecture:** Three sibling folders under `app/` — `be/` (FastAPI), `fe/` (Vite + React + TypeScript), and `docs/` (spec + plan subfolders). Each service has its own Dockerfile. No shared build system — each is independently runnable.

**Tech Stack:** Python 3.11 + FastAPI + Uvicorn (backend), Node 20 + Vite + React + TypeScript (frontend)

---

## File Map

**Create:**
- `app/be/main.py` — FastAPI app with `/health` endpoint
- `app/be/requirements.txt` — fastapi, uvicorn
- `app/be/Dockerfile` — Python 3.11 slim image
- `app/fe/package.json` — Vite + React + TypeScript deps
- `app/fe/vite.config.ts` — Vite config
- `app/fe/tsconfig.json` — TypeScript config
- `app/fe/index.html` — Vite entry HTML
- `app/fe/src/main.tsx` — React mount point
- `app/fe/src/App.tsx` — Hello World component
- `app/fe/Dockerfile` — Node 20 build + serve image
- `app/docs/spec/.gitkeep` — keep folder in git
- `app/docs/plan/.gitkeep` — keep folder in git

---

### Task 1: Backend skeleton

**Files:**
- Create: `app/be/main.py`
- Create: `app/be/requirements.txt`

- [ ] **Step 1: Create `app/be/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
```

- [ ] **Step 2: Create `app/be/main.py`**

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Verify it runs locally (optional, skip if no Python env)**

```bash
cd app/be
pip install -r requirements.txt
uvicorn main:app --reload
# Visit http://localhost:8000/health → {"status":"ok"}
```

- [ ] **Step 4: Commit**

```bash
git add app/be/main.py app/be/requirements.txt
git commit -m "feat(app/be): add FastAPI skeleton with /health endpoint"
```

---

### Task 2: Backend Dockerfile

**Files:**
- Create: `app/be/Dockerfile`

- [ ] **Step 1: Create `app/be/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Verify build (optional, skip if no Docker)**

```bash
cd app/be
docker build -t app-be .
docker run --rm -p 8000:8000 app-be
# curl http://localhost:8000/health → {"status":"ok"}
```

- [ ] **Step 3: Commit**

```bash
git add app/be/Dockerfile
git commit -m "feat(app/be): add Dockerfile"
```

---

### Task 3: Frontend skeleton

**Files:**
- Create: `app/fe/package.json`
- Create: `app/fe/vite.config.ts`
- Create: `app/fe/tsconfig.json`
- Create: `app/fe/index.html`
- Create: `app/fe/src/main.tsx`
- Create: `app/fe/src/App.tsx`

- [ ] **Step 1: Create `app/fe/package.json`**

```json
{
  "name": "app-fe",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.4.5",
    "vite": "^5.3.1"
  }
}
```

- [ ] **Step 2: Create `app/fe/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
```

- [ ] **Step 3: Create `app/fe/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Create `app/fe/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create `app/fe/src/main.tsx`**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 6: Create `app/fe/src/App.tsx`**

```tsx
export default function App() {
  return <h1>Hello World</h1>
}
```

- [ ] **Step 7: Verify it runs locally (optional, skip if no Node env)**

```bash
cd app/fe
npm install
npm run dev
# Visit http://localhost:5173 → "Hello World"
```

- [ ] **Step 8: Commit**

```bash
git add app/fe/
git commit -m "feat(app/fe): add React+TypeScript skeleton with Hello World"
```

---

### Task 4: Frontend Dockerfile

**Files:**
- Create: `app/fe/Dockerfile`

- [ ] **Step 1: Create `app/fe/Dockerfile`**

```dockerfile
FROM node:20-slim AS builder

WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM node:20-slim
RUN npm install -g serve
WORKDIR /app
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
```

- [ ] **Step 2: Verify build (optional, skip if no Docker)**

```bash
cd app/fe
docker build -t app-fe .
docker run --rm -p 3000:3000 app-fe
# Visit http://localhost:3000 → "Hello World"
```

- [ ] **Step 3: Commit**

```bash
git add app/fe/Dockerfile
git commit -m "feat(app/fe): add Dockerfile"
```

---

### Task 5: Docs folders and repo init

**Files:**
- Create: `app/docs/spec/.gitkeep`
- Create: `app/docs/plan/.gitkeep`

- [ ] **Step 1: Create `.gitkeep` files to preserve empty folders**

```bash
mkdir -p app/docs/spec app/docs/plan
touch app/docs/spec/.gitkeep app/docs/plan/.gitkeep
```

- [ ] **Step 2: Initialize git repo (if not already initialized)**

```bash
git init
git add .
```

- [ ] **Step 3: Commit**

```bash
git add app/docs/
git commit -m "chore(app/docs): add spec and plan folders"
```

---
