# Cloud District Club - Product Requirements Document

## Original Problem Statement
Mobile app for local pickup of disposable vape products, 21+ age gate.

## Tech Stack
- Frontend: React Native / Expo / Expo Router / TypeScript / Zustand
- Backend: FastAPI / Python / MongoDB
- Deploy: Railway (backend), Expo web (frontend)

## Architecture
```
/app
├── backend/
│   ├── Procfile              (Railway start command)
│   ├── server.py             (canonical — only server file)
│   ├── utils/email.py        (scaffolded, MOCKED)
│   └── uploads/              (product/brand images)
├── frontend/
│   ├── app/                  (Expo Router pages)
│   ├── store/authStore.ts    (localStorage on web)
│   ├── store/cartStore.ts    (localStorage on web)
│   ├── babel.config.js       (import.meta fix)
│   └── components/
```

## Critical Web Persistence Pattern
All client state uses direct `localStorage` on web (NOT AsyncStorage):
- Auth token: key `cloud-district-token`
- Age verified: key `ageVerified`
- Cart: key `cloud-district-cart`
- `babel-plugin-transform-import-meta` required for client-side JS to execute

## Completed
- P0: Cart persistence (localStorage + babel fix)
- P1: Server file consolidation (deleted 4 stale copies)
- Auth persistence across page reload
- Admin upload fix (auth header + Content-Type boundary)
- Age gate persistence across reload
- Procfile for Railway deploy

## Credentials
- Admin: jkaatz@gmail.com / Just1n23$

## Remaining (NOT P2)
- Railway deploy verification (user to push + verify)
- Expo Go: inherent preview env limitation (--web mode, no native Metro)

## Future (P2+)
- Backend monolith refactor
- Admin screen modularization
- Google Workspace email integration
- Push notifications expansion
