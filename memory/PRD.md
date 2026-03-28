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

## Completed (2026-03-28 Session 5)
- **Age Gate Replaced**: Rewrote `age-gate.tsx` — simple 1-button modal with hero image, warning box, "I am 21+ Enter" CTA, "Exit" button, and disclaimer. Persists via `cloudDistrictAgeVerified` + legacy `ageVerified` in AsyncStorage/localStorage. DOB picker fully removed.
- **Login with Username OR Email**: Backend `UserLogin` schema changed from `email: EmailStr` to `identifier: str`. Login handler detects `@` to route by email vs username. `authStore.login()` now sends `{ identifier, password }`. Login form label updated to "Email or Username". Login response now includes `username` field.
- **Avatar Upload at Signup**: Circular avatar picker added above First Name in `register.tsx` using `expo-image-picker`. Converts to base64, sends as `profilePhoto` in register payload. Field is optional — registration works without it. Backend `UserRegister` schema + handler updated to accept and store `profilePhoto`.

## Completed (2026-03-28 Session 4)
- **Phone Number Field**: Added between Email and Password. Auto-formats as `(608) 555-1234`, strips non-digits on submit, requires 10 digits minimum. Stored in user record.
- **Username Availability Check**: Debounced 400ms after 3+ chars → calls new `GET /api/auth/check-username?username=xxx` endpoint. Shows green "✓ Available" or red "✗ Already taken" inline next to the label. Input border turns green/red accordingly. Blocks submit if taken.
- **Validation updates**: Submit blocked for missing phone, phone < 10 digits, or username taken.
- **Backend**: New `GET /api/auth/check-username` endpoint (no auth) checks against DB + reserved words + regex format.
- **authStore**: `register()` now accepts optional `phone` 8th param and sends it in payload.

## Completed (2026-03-28 Session 3)
- **Registration Form Overhaul**:
  - Reordered fields: First Name → Last Name → Username → Email → Password → Confirm Password → Age Checkbox → Referral → Sign Up
  - Username field: auto-lowercases, removes spaces, helper text "This becomes your permanent referral ID"
  - Confirm Password field added with match validation before submit
  - Date of Birth input REMOVED and REPLACED with 21+ age verification checkbox ("I confirm I am 21 years of age or older")
  - Backend still receives `dateOfBirth: "1990-01-01"` hardcoded (no backend changes needed)
  - Fixed CRITICAL bug: `Alert.alert()` is a no-op in react-native-web 0.21.0 — replaced all 5+ calls with inline `errorMsg` state rendered as a styled red error box above Sign Up button
  - Referral field label updated to "Referral Username (optional)"
  - Submit blocked for: missing fields, password mismatch, age unchecked, invalid username format
  - API errors extracted with `error?.response?.data?.detail` (no [object Object])
  - Removed unused `Alert` and `Platform` imports
- Admin screen modularization (user-profile.tsx is 600+ lines)
- Google Workspace email integration (email_service.py is currently MOCKED)
- Push notifications expansion
- Social sharing (X, Facebook, Instagram) for Ways to Earn
