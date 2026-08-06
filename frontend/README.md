# Cloud Masking — Frontend

React + TypeScript + Vite application. **Milestone 2 status: scaffold only** — directory structure and a
placeholder `package.json`; the real Vite project (with `index.html`, `vite.config.ts`, `tsconfig.json`,
and source) is created in **Milestone 14**.

## Planned structure

```
frontend/src/
├── components/   # reusable UI (upload, map overlay, metric tiles, comparison views)
├── pages/        # Dashboard, Upload, Prediction, Comparison, Statistics, Map, History, Metrics
├── services/     # API client (axios) to the FastAPI backend
├── hooks/        # custom React hooks
├── utils/        # helpers
└── assets/       # static assets
```

## Stack (declared, not installed at M2)

React 18 · TypeScript 5 · Vite 6 · react-router · axios · Leaflet/react-leaflet (Map Viewer).
Requires Node ≥ 20.

## Setup (Milestone 14 — do NOT run at M2)

```bash
cd frontend
npm install
npm run dev
```
