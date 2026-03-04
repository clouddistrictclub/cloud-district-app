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
│   ├── Procfile
│   ├── server.py
│   ├── utils/email.py        (MOCKED)
│   └── uploads/
├── frontend/
│   ├── app/
│   │   ├── (tabs)/           (Home, Shop, Orders, Account)
│   │   ├── cloudz.tsx        (Rewards dashboard - 4 sections)
│   │   ├── cloudz-history.tsx
│   │   └── admin/
│   ├── components/
│   │   ├── AppHeader.tsx     (Shared header: icon + cloudz badge + cart)
│   │   ├── ProductCard.tsx
│   │   ├── HeroBanner.tsx
│   │   └── ChatBubble.tsx
│   ├── store/
│   └── dist/
```

## Cloudz Earn Rate
- **3 Cloudz per $1 spent** (changed from 1x)
- Formula: `points_earned = int(order_data.total) * 3`
- Example: $20 purchase = 60 Cloudz

## Loyalty Tiers (unchanged)
- Bronze Cloud — 1,000 pts → $5.00
- Silver Storm — 5,000 pts → $30.00
- Gold Thunder — 10,000 pts → $75.00
- Platinum Haze — 20,000 pts → $175.00
- Diamond Sky — 30,000 pts → $300.00

## Persistent AppHeader
- Renders on ALL tab screens (Home, Shop, Orders, Account)
- Shows: Cloud District icon, Cloudz balance badge, Cart icon with count
- Component: `components/AppHeader.tsx`
- Each tab imports and renders `<AppHeader />` at top of container

## Deployment Configuration

### Backend (DEPLOYED on Railway at api.clouddistrict.club)
- Start: `uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}`
- Health: `GET /api/health`
- CORS: `allow_origins=["*"]`

### Frontend (READY for Emergent deployment)
- `EXPO_PUBLIC_BACKEND_URL=https://api.clouddistrict.club`
- Also has Railway build/start scripts as fallback

## Completed
- Cart/Auth/Age-gate persistence (localStorage + babel fix)
- Server consolidation, backend Procfile
- Product image upload fix (base64 inline)
- Cloudz Rewards UI (4-section dashboard)
- DB cleanup (7 users, 0 orders, loyalty intact)
- Admin role verified (jkaatz@gmail.com = isAdmin: true)
- **Cloudz earn rate 3x** (backend verified: $20 → 60 pts)
- **Persistent AppHeader across all tabs**
- Production deployment prep (Emergent + Railway fallback)

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
- Social sharing (X, Facebook, Instagram) for Ways to Earn
