# Cloud District Club - Product Requirements Document
_Last updated: 2026-03-08_

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
- **SafeArea Fix** (Mar 2026): AppHeader now uses `useSafeAreaInsets()` hook — fixes iPhone Dynamic Island/status bar overlap on iOS native. Web still uses `env(safe-area-inset-top)`.
- **Cloudz History Crash Fix** (Mar 2026): Fixed `undefined.toLocaleString()` crash on cloudz-history.tsx — added `?? 0` guard for `item.amount` and `item.balanceAfter`. Added `Array.isArray()` guard on API response in both cloudz.tsx and cloudz-history.tsx. Also added missing `referral_reward` type to TYPE_LABELS/TYPE_ICONS.

## Credentials
- Admin: jkaatz@gmail.com / Just1n23$

## Architecture Change (2026)
- Frontend moved to **Vercel** (clouddistrict.club)
- Backend is now **API-only** on Railway (api.clouddistrict.club)
- `server.py`: All static file serving removed (DIST_DIR, StaticFiles mounts for frontend, serve_index, serve_spa catch-all)
- `GET /` → `{"status": "Cloud District API running"}`
- `EXPO_PUBLIC_BACKEND_URL` updated to `https://api.clouddistrict.club`

## Pending
- P1: Store Credit at Checkout (allow users to apply creditBalance at order placement)

## Parity Fixes Applied (2026-03-08)
- `checkout.tsx`: Removed Venmo from paymentMethods (now: Cash on Pickup, Zelle, Cash App, Chime)
- `product/[id].tsx`: Restored AppHeader + back row header — fixes cart badge bug on product screen
  - Staging used AppHeader (with Cloudz balance + cart count badge) + TouchableOpacity backRow
  - Previous code had a custom header with NO badge
  - Both fixes verified with screenshots, DOM checks, and staging bundle comparison

## Future (P2+)
- Backend monolith refactor
- Admin screen modularization
- Google Workspace email integration
- Push notifications expansion
- Social sharing (X, Facebook, Instagram) for Ways to Earn
