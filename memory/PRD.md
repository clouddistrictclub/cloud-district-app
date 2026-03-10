# Cloud District Club - Product Requirements Document
_Last updated: 2026-03-10_

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
- **SafeArea Fix** (Mar 2026): AppHeader now uses `useSafeAreaInsets()` hook
- **Cloudz History Crash Fix** (Mar 2026): Fixed `undefined.toLocaleString()` crash
- **Parity Fixes** (2026-03-08): Removed Venmo, restored AppHeader on product page
- **Admin Password Management** (2026-03-09):
  - `POST /api/admin/users/{user_id}/set-password` — hash + update password (min 8 chars, admin-only)
  - `POST /api/admin/users/{user_id}/force-logout` — stores `forceLogoutAt` timestamp to invalidate sessions
  - `isDisabled` check in `/auth/login` — disabled accounts get 403
  - `isDisabled` + `forceLogoutAt` check in `get_current_user` — auto-blocks disabled/force-logged-out users
  - Admin user profile page: ADMIN ACTIONS section with Reset Password / Disable Account / Force Logout
  - Reset Password modal with validation (min 8 chars, confirm match)
  - Users list: "Profile" button navigates to user detail page
  - Auth race condition fix: `users.tsx` and `user-profile.tsx` now wait for token before calling admin APIs
- **Admin Capability Audit & Expansion** (2026-03-09):
  - AUDITED: Cloudz Adjustment ✅ COMPLETE; Store Credit API ✅ (UI was missing); Order Status ✅; Order Edit (items/notes) ✅; Pickup Time + Payment Method edit ❌ added; Admin Notes on User ❌ added; Account Merge ❌ added; Next Order Coupon ❌ added; Cloudz Progress Reminder ❌ added
  - NEW endpoints: `PATCH /api/admin/users/{id}/notes`, `POST /api/admin/users/merge`, `GET /api/me/coupon`
  - `OrderEdit` model updated with optional `pickupTime` and `paymentMethod` fields
  - `OrderCreate` model updated with `couponApplied: bool` for coupon redemption at checkout
  - Auto-issues `nextOrderCoupon` ($5, 7-day expiry) when order status → Completed
  - Frontend: Notes tab + Credit tab added to admin user-profile
  - Frontend: Merge Into action with warning modal added to admin user-profile
  - Frontend: Pickup time + payment method selectors added to admin order edit modal
  - Frontend: Cloudz Progress Reminder in account.tsx (shows when within 20% of next tier)
  - Frontend: Coupon section in checkout.tsx — display, toggle, and apply at order placement
  - DB Consistency: preview uses local MongoDB (localhost:27017/test_database); production uses separate instance
- **ToastProvider Fix** (2026-03-10): Added `ToastProvider` to root `_layout.tsx` — previously missing, causing all `toast.show()` calls to be silent no-ops; admin actions (password reset, credit adjustments, etc.) now show success/error toasts

## Completed (2026-03-10 Session 2)
- **Leaderboard Rank Movement** (2026-03-10):
  - `leaderboard_snapshot_loop` runs on startup, writes one snapshot to `leaderboard_snapshots` per day (idempotent)
  - `GET /api/leaderboard` returns `movement: number | null` per entry (positive=up, negative=down, 0=same, null=no prior snapshot)
  - `leaderboard.tsx` interface extended with `movement` field; `renderItem()` renders ↑ green / ↓ red / — neutral indicators
  - End-to-end verified: Justin K. +1, Brianna C. -1, Andrew M. 0, others null (no prior snapshot)
- **Store Credit at Checkout** (2026-03-10):
  - `OrderCreate` schema: `storeCreditApplied: float = 0.0`; `Order` schema: same field persisted
  - Backend deducts `storeCreditApplied` from `user.creditBalance` atomically on order creation
  - Order cancellation now restores `storeCreditApplied` to user's `creditBalance`
  - `checkout.tsx`: shows "Apply Store Credit" toggle when `user.creditBalance > 0`; discount shown in summary; capped at min(balance, orderTotal)
  - Verified: $25 credit → apply $5 → balance becomes $20; cancel order → credit restored to $25

## Future (P2+)
- Admin screen modularization (user-profile.tsx is 600+ lines)
- Google Workspace email integration (email_service.py is currently MOCKED)
- Push notifications expansion
- Social sharing (X, Facebook, Instagram) for Ways to Earn
