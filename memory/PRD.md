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

## Completed (2026-03-28 Session 6)
- **Referral Reward System Fix** (CRITICAL):
  - **Bug 1 Fixed**: New user with referral now gets +1000 Cloudz (500 signup + 500 referral_new_user_bonus), was only getting 500
  - **Bug 2 Fixed**: Referrer now gets +1500 Cloudz on referred signup, was only getting 500
  - **Bug 3 Fixed**: Admin `PATCH /admin/users/{id}/referrer` now issues rewards (+500 to user, +1500 to referrer) when assigning a referrer to a user who had none
  - Created `issue_referral_signup_rewards()` helper in `loyalty_service.py` — DRY, idempotent, used by both registration and admin assign flows
  - Idempotency: `referral_new_user_bonus` keyed on userId+type (one per lifetime), `referral_signup_bonus` keyed on userId+type+referredUserId (one per referred user)
  - Atomic MongoDB operations throughout
  - Existing order referral system (50% of order total to referrer on Paid) untouched
  - Ledger entries: `signup_bonus`, `referral_new_user_bonus`, `referral_signup_bonus` all correctly logged
- **Cloudz Ledger UI Fintech Upgrade**:
  - Centralized `constants/ledger.ts` — single source of truth for ALL ledger type labels, icons, and colors; `formatLedgerType()`, `getLedgerIcon()`, `getLedgerColor()` helpers
  - Full label mapping: signup_bonus, referral_signup_bonus, referral_new_user_bonus, referral_bonus, referral_reward, purchase_reward, tier_redemption, admin_adjustment, streak_bonus, credit_adjustment — with fallback (underscore→space, capitalize)
  - Color system: green (rewards/bonuses), red (tier redemptions), orange/amber (admin/credit adjustments)
  - Fintech card design: rounded 16px cards, dark #1A1A1A bg, shadow/elevation, colored icon circles, large bold amounts (18px), balance + timestamp
  - Fade-in animation on each row (staggered 30-40ms delay)
  - Updated 3 screens: `cloudz-history.tsx` (user), `admin/cloudz-ledger.tsx` (admin), `cloudz.tsx` (inline activity)
  - Admin ledger: horizontal scrollable filter chips for all ledger types
  - Zero backend changes — frontend-only presentation upgrade

## Completed (2026-03-31 Session 9)
- **6 Loyalty/Referral Logic Fixes** (CRITICAL, all verified via curl against preview API):
  - **Issue 1 Fixed**: Removed `bulk_discount` ledger entry from `order_routes.py`. Discount only reduces `discountApplied` field on order — zero impact on Cloudz.
  - **Issue 2 Fixed**: `purchase_reward` now fires on "Paid", "Ready for Pickup", OR "Completed" (was only "Paid"). Idempotency via new `loyaltyRewardIssued: bool` flag on `Order` schema (atomic `find_one_and_update` gate). Backward-safe: `already_completed` check prevents re-processing existing "Paid" orders.
  - **Issue 3 Fixed**: New user's +500 `referral_signup_bonus` is issued BEFORE referrer lookup in `issue_referral_signup_rewards()`. Previously, if referrer document was not found, the function returned early and the new user got $0 bonus. Now always awards 1000 Cloudz on referred signup.
  - **Issue 4**: `referral_pending` (+1500, no balance change) was already correctly created. Verified.
  - **Issue 5 Fixed**: `check_and_unlock_referral_reward()` now called AFTER the final `db.orders.update_one(status)` call, so the current order counts in the $50 lifetime-spend aggregate. Previously it ran before, returning 0 spend.
  - **Issue 6 Fixed**: Per-order referral earning type changed from `"referral_reward"` to `"referral_order_reward"` to disambiguate from the one-time unlock reward. Also now fires on all completion statuses, not just "Paid".
  - Files changed: `backend/models/schemas.py`, `backend/routes/order_routes.py`, `backend/routes/admin_routes.py`, `backend/services/loyalty_service.py`

## Completed (2026-03-31 Session 8)
- **Referral anti-abuse + cart discount system**
  - Referrer signup reward now creates `referral_pending` ledger entry (+1500, no balance yet); balance unlocks only when referred user's lifetime spend >= $50
  - `check_and_unlock_referral_reward()` in `loyalty_service.py`: aggregates completed orders, atomically flips `referralUnlocked` flag, converts `referral_pending → referral_reward`, credits +1500 to referrer; idempotent via flag + find_one_and_update gate
  - Called automatically in admin "Paid" status update handler
  - Bulk cart discount: 10% applied when quantity >= 10 items; `discountApplied` stored on order; audit entry in ledger; loyalty points calculated on discounted total; discount applied before store credit
  - All safeguards: no self-referral, no duplicate pending entries, no duplicate unlocks, fully auditable

## Completed (2026-03-31 Session 7)
- **Referral system complete**
  - `GET /api/users/check?username=` — public endpoint, case-insensitive, always 200 with `{exists, userId, username}`
  - Registration: `referredBy` stored as userId (consistent with admin assignment); self-referral blocked pre-insert; `referralRewardGiven` flag added
  - Ledger types updated: new user gets `referral_signup_bonus` (+500); referrer gets `referral_reward` (+500, was +1500) with `metadata.referredUser`
  - `issue_referral_signup_rewards` fully idempotent via `referralRewardGiven` flag + secondary ledger check; backward-compatible with old type names
  - Registration response now includes `referredByUserId`

## Completed (2026-03-30 Session 6)
- **P0 Bug Fix: JWT missing `iat` → /auth/me always 401 for users with forceLogoutAt**
  - Root cause: `create_access_token` in `auth.py` did not include `iat` (issued-at) in JWT payload. `get_current_user` falls back to `iat = 0` when field missing. For users with `forceLogoutAt` set (e.g., jraymasangkay@gmail.com, forceLogoutAt=1773177646), `0 < forceLogoutAt` was always TRUE → every `/auth/me` call returned 401 "Session has been invalidated", even after fresh login.
  - Fix: Added `"iat": now` to `create_access_token`. Fresh tokens now carry current timestamp → `iat > past forceLogoutAt` → check passes.
  - New endpoint: `POST /api/admin/users/{user_id}/clear-force-logout` — admins can unset forceLogoutAt cleanly.
  - **DEPLOYMENT REQUIRED**: These fixes are in preview code. Must deploy to Railway production (api.clouddistrict.club) for affected user jraymasangkay@gmail.com to be unblocked.

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
