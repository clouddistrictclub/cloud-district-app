# Cloud District Club - Product Requirements Document

## Original Problem Statement
Mobile app for local pickup of disposable vape products, 21+ age gate.

## Tech Stack
- Frontend: React Native / Expo 54 / Expo Router / TypeScript / Zustand
- Backend: FastAPI / Python / MongoDB
- Deploy: Railway (backend at api.clouddistrict.club, frontend at clouddistrict.club)

## Architecture
```
/app
├── backend/
│   ├── Procfile              (Railway start command: uvicorn)
│   ├── server.py             (canonical — only server file)
│   ├── utils/email.py        (scaffolded, MOCKED)
│   └── uploads/              (product/brand images)
├── frontend/
│   ├── app/                  (Expo Router pages)
│   ├── store/authStore.ts    (localStorage on web)
│   ├── store/cartStore.ts    (localStorage on web)
│   ├── babel.config.js       (import.meta fix)
│   ├── components/
│   └── dist/                 (static web export output)
```

## Critical Web Persistence Pattern
All client state uses direct `localStorage` on web (NOT AsyncStorage):
- Auth token: key `cloud-district-token`
- Age verified: key `ageVerified`
- Cart: key `cloud-district-cart`
- `babel-plugin-transform-import-meta` required for client-side JS to execute

## Railway Deployment Config

### Backend (DEPLOYED at api.clouddistrict.club)
- Root Directory: `backend`
- Start Command: `uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}`
- Health Check: `GET /api/health`

### Frontend (READY for deployment at clouddistrict.club)
- Root Directory: `frontend`
- Build Command: `yarn build` → runs `expo export --platform web`
- Start Command: `yarn start` → runs `npx serve -s dist -l ${PORT:-3000}`
- Required Env Var: `EXPO_PUBLIC_BACKEND_URL=https://api.clouddistrict.club`
- Output: Static HTML/JS/CSS in `dist/`, SPA fallback via `serve -s`
- `serve` v14.2.5 added as production dependency

## Completed
- P0: Cart persistence (localStorage + babel fix)
- P1: Server file consolidation (deleted stale copies)
- Auth persistence across page reload
- Admin upload fix (auth header + Content-Type boundary)
- Age gate persistence across reload
- Backend Procfile for Railway deploy
- **Frontend Railway production setup** (build/start scripts, serve dep, env var config)

## Credentials
- Admin: jkaatz@gmail.com / Just1n23$

## Pending
- Admin product image preview not persisting in form UI (P1, minor UX)
- Railway frontend service creation + domain setup (user action)

## Future (P2+)
- Backend monolith refactor
- Admin screen modularization
- Google Workspace email integration
- Push notifications expansion
