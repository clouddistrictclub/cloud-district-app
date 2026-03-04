# Cloud District Club - Product Requirements Document

## Original Problem Statement
Mobile app for local pickup of disposable vape products, 21+ age gate.

## Tech Stack
- Frontend: React Native / Expo 54 / Expo Router / TypeScript / Zustand
- Backend: FastAPI / Python / MongoDB
- Deploy: Backend on Railway (api.clouddistrict.club), Frontend on Emergent (clouddistrict.club)

## Architecture
```
/app
├── backend/
│   ├── Procfile              (Railway start command: uvicorn)
│   ├── server.py             (canonical — only server file)
│   ├── utils/email.py        (scaffolded, MOCKED)
│   └── uploads/              (product/brand images)
├── frontend/
│   ├── app/
│   │   ├── cloudz.tsx        (Rewards dashboard - 4 sections)
│   │   ├── cloudz-history.tsx (Full ledger history)
│   │   └── admin/products.tsx (Fixed image upload)
│   ├── store/authStore.ts    (localStorage on web)
│   ├── store/cartStore.ts    (localStorage on web)
│   ├── babel.config.js       (import.meta fix)
│   └── dist/                 (static web export output)
```

## Critical Web Persistence Pattern
All client state uses direct `localStorage` on web (NOT AsyncStorage):
- Auth token: key `cloud-district-token`
- Age verified: key `ageVerified`
- Cart: key `cloud-district-cart`

## Deployment Configuration

### Backend (DEPLOYED on Railway at api.clouddistrict.club)
- Root Directory: `backend`
- Start Command: `uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}`
- Health Check: `GET /api/health`
- CORS: `allow_origins=["*"]`

### Frontend (READY for Emergent deployment at clouddistrict.club)
- Runs via Expo dev server (supervisor: `expo` process on port 3000)
- Backend URL: `EXPO_PUBLIC_BACKEND_URL=https://api.clouddistrict.club`
- Also has Railway-compatible build/start scripts in package.json as fallback

## Loyalty Tiers (Backend)
- tier_1: Bronze Cloud — 1,000 pts → $5.00
- tier_2: Silver Storm — 5,000 pts → $30.00
- tier_3: Gold Thunder — 10,000 pts → $75.00
- tier_4: Platinum Haze — 20,000 pts → $175.00
- tier_5: Diamond Sky — 30,000 pts → $300.00

## Completed
- Cart persistence (localStorage + babel fix)
- Server file consolidation
- Auth/age-gate persistence
- Admin upload fix
- Backend Procfile for Railway
- Frontend Railway/Emergent production setup
- DB cleanup (7 users, 0 orders, loyalty intact)
- Admin role verified (jkaatz@gmail.com = isAdmin: true)
- Product image upload fix (base64 inline, matching brands)
- **Cloudz Rewards UI overhaul** — 4-section dashboard:
  1. Balance Panel (balance + next threshold + active reward chips)
  2. Ways to Earn (6 cards: 3 active + 3 disabled social placeholders)
  3. Ways to Redeem (5 tier cards with Redeem buttons)
  4. Your Activity (latest 5 ledger entries + View All link)

## Credentials
- Admin: jkaatz@gmail.com / Just1n23$

## Pending
- Emergent frontend deployment (user clicks Deploy)
- Custom domain DNS for clouddistrict.club

## Future (P2+)
- Backend monolith refactor
- Admin screen modularization
- Google Workspace email integration
- Push notifications expansion
- Social sharing integration (X, Facebook, Instagram) for Ways to Earn
