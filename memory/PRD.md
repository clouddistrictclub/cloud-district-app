# Cloud District Club - Product Requirements Document

## Original Problem Statement
Mobile app for local pickup of disposable vape products, 21+ age gate.

## Tech Stack
- Frontend: React Native / Expo 54 / Expo Router / TypeScript / Zustand
- Backend: FastAPI / Python / MongoDB
- Deploy: Backend on Railway (api.clouddistrict.club), Frontend on Emergent (clouddistrict.club)
Mobile app called "Cloud District Club" for the local pickup of disposable vape products, restricted to users aged 21 and over.

## Core Requirements
- **Age Verification:** Mandatory 21+ age gate
- **Design:** Dark, premium, fast, simple UI
- **Home Screen:** Featured products, shop by brand, loyalty points, "Order for Local Pickup" CTA
- **Product Catalog:** Category organization with detailed product views
- **Checkout Flow:** Local pickup only, manual payment methods
- **Order Status System:** Track order progress
- **Loyalty Program ("Cloudz Points"):** Tier-based system with streak bonus
- **Referral Program:** Code-based system with deep linking
- **User Accounts:** Order history, loyalty status, profile management
- **Admin Dashboard:** Full CRUD on products, brands, users, inventory, orders
- **Contact & Support:** Ticket system
- **Live Chat:** Real-time WebSocket chat with typing indicators and read receipts
- **Bulk Discount:** 10% discount when total cart quantity >= 10

## Tech Stack
- **Frontend**: React Native, Expo, Expo Router, TypeScript, Zustand
- **Backend**: FastAPI, Python, MongoDB (Pydantic models)
- **Deployment**: Supervisor for process management

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

## Pending
- Emergent frontend deployment (user clicks Deploy)
- Custom domain DNS for clouddistrict.club

## Future (P2+)
- Backend monolith refactor
- Admin screen modularization
- Google Workspace email integration
- Push notifications expansion
- Social sharing (X, Facebook, Instagram) for Ways to Earn
│   ├── .env
│   ├── server.py          (canonical — only server file)
│   ├── tests/
│   ├── utils/email.py
│   └── uploads/ (products/, brands/)
├── frontend/
│   ├── app/ (Expo Router pages)
│   ├── store/ (cartStore.ts, authStore.ts)
│   ├── components/ (ChatBubble.tsx, HeroBanner.tsx)
│   └── babel.config.js (import.meta fix)
```

## What's Been Implemented
### Completed Features
- Age Gate with DOB verification
- User authentication (login/register)
- Product catalog with categories and detailed views
- Shopping cart with persistence (localStorage/AsyncStorage)
- Checkout flow with local pickup
- Admin dashboard (products, brands, users, orders CRUD)
- Loyalty program ("Cloudz Points")
- Referral program
- Live chat (WebSocket) with typing indicators and read receipts
- Support ticket system
- Image upload system (file-based, not base64)
- Hero banner component (shared across screens)
- Draggable chat FAB with haptic feedback
- Bulk discount (10% at 10+ items)

### Recent Fixes (Feb 2026)
- **P0: Cart Persistence** — FIXED
  - Root Cause #1: `import.meta` error crashed client bundle, preventing React hydration
  - Root Cause #2: Zustand `persist` middleware incompatible with Expo web SSR
  - Fix: `babel-plugin-transform-import-meta` + manual localStorage read/write
  - Files: `cartStore.ts`, `_layout.tsx`, `cart.tsx`, `babel.config.js` (new)

- **P1: Server File Consolidation** — DONE
  - Deleted: `server_enhanced.py` (root + backend), `server_backup.py`, `server_original.py`
  - Canonical: `/app/backend/server.py` (unchanged)
  - Supervisor: `uvicorn server:app` from `/app/backend/` (already correct)
  - Regression: 100% pass (auth, products, brands, images, cart, checkout, WebSocket)

## Credentials
- **Admin**: jkaatz@gmail.com / Just1n23$
- **Test User**: testuser@clouddistrict.club / Test1234!

## Upcoming Tasks (Priority Order)
1. **P2: Backend monolith refactor** — Restructure server.py for scalability
2. **P2: Admin screen modularization** — Break down large admin components
3. **P2: Google Workspace email integration** — Implement email sending
4. **P3: Push notifications expansion**
5. **P3: Recently Viewed Products carousel**

## Key API Endpoints
- `POST /api/auth/login` — User login
- `GET /api/auth/me` — Current user
- `GET /api/products` — List products
- `GET /api/brands` — List brands
- `POST /api/orders` — Create order
- `POST /api/upload/product-image` — Upload product image
- `GET /api/uploads/products/{filename}` — Serve product image
- `WS /api/ws/chat/{chatId}` — WebSocket chat

## Known Notes
- Email utility (`backend/utils/email.py`) is scaffolded but MOCKED — not sending emails
- `CI=true` in supervisor config (read-only), Metro runs in CI mode
- `babel-plugin-transform-import-meta` is essential for web client-side JS
