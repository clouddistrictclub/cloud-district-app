# Cloud District Club — PRD (Product Requirements Document)

## Original Problem Statement

Building a mobile-first web app called "Cloud District Club" for local pickup of disposable vape products, restricted to users 21+.

---

## Core Product Requirements

- **Age Verification**: Mandatory 21+ age gate on every session
- **Design**: Dark, premium, fast, simple mobile-first UI
- **Home Screen**: Featured products, shop by brand, loyalty points display, "Order for Local Pickup" CTA
- **Checkout Flow**: Local pickup only, manual payment methods (Cash, Venmo, Zelle, etc.)
- **Order Status System**: Track order progress (Pending → Paid → Preparing → Ready → Completed)
- **Loyalty Program ("Cloudz Points")**: Tier-based system, streak bonus, daily check-in rewards, weekly leaderboard rewards
- **Referral Program**: Username-based referral system (referrer gets pending rewards that unlock after referred user spends $50)
- **User Accounts**: Order history, loyalty status, profile management, profile photo
- **Admin Dashboard**: Full CRUD on products, brands, users, inventory, orders; user management, store credit, account notes

---

## Architecture

```
/app
├── backend/
│   ├── auth.py                    # JWT + password hashing
│   ├── database.py                # MongoDB Motor async client
│   ├── models/schemas.py          # Pydantic models + reward constants
│   ├── routes/
│   │   ├── admin_routes.py        # Admin CRUD + order status management
│   │   ├── auth_routes.py         # Signup (strict referral) + login
│   │   ├── loyalty_routes.py      # Leaderboard + check-in endpoints
│   │   ├── order_routes.py        # PATCH /api/orders/{id}/status
│   │   └── product_routes.py      # Products + brands + image fallback
│   ├── services/
│   │   ├── loyalty_service.py     # Atomic check-in, streak, weekly rewards
│   │   └── order_service.py       # Centralized update_order_status_shared()
│   └── scripts/
│       └── catalog_repair.py      # Product catalog repair/creation script
├── frontend/
│   ├── app/
│   │   ├── (admin)/               # Admin dashboard screens
│   │   ├── (tabs)/                # User-facing screens (home, shop, account)
│   │   └── ...
│   ├── constants/
│   │   └── api.ts                 # WARNING: Hardcoded to production API URL
│   └── store/authStore.ts         # Zustand auth store
```

---

## Tech Stack

- **Frontend**: React Native (Expo for Web), Zustand state management
- **Backend**: FastAPI, Motor (async MongoDB driver)
- **Database**: MongoDB
- **External Libs**: slowapi (rate limiting), expo-image-picker

---

## Key Database Schema

| Collection | Key Fields |
|---|---|
| `users` | `loyaltyPoints, creditBalance, referralCode, referredBy, referralUnlocked, checkInStreak, lastCheckInDate` |
| `cloudz_ledger` | `type, amount, balanceAfter, userId, reference, isoDate` |
| `products` | `brandId, brandName, model, flavor, name, productType, puffCount, nicotinePercent, price, stock, image, isActive, isFeatured` |
| `orders` | `status, discountApplied, loyaltyRewardIssued, finalTotal` |
| `brands` | `name, image, description, isActive` |
| `leaderboard_rewards` | `isoYear, isoWeek, rewardsIssued, topUsers` |

---

## Key API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/register` | Signup with strict referral code (username) |
| `POST` | `/api/auth/login` | Login (field: `identifier`, not `email`) |
| `GET` | `/api/products` | Product catalog with fallback image URL |
| `GET` | `/api/products/{id}` | Single product with fallback image URL |
| `PATCH` | `/api/orders/{order_id}/status` | Web order status update (triggers rewards) |
| `PATCH` | `/api/admin/orders/{order_id}/status` | Admin order status update |
| `POST` | `/api/loyalty/check-in` | Daily check-in reward (atomic) |
| `GET` | `/api/leaderboard` | Leaderboard with weekly rewards + current user |
| `GET` | `/api/loyalty/streak` | Real-time streak calculation |

---

## What's Been Implemented

### Phase 1 – Core MVP (Complete)
- Age gate, auth (JWT), product catalog, cart, checkout, order tracking
- Admin dashboard (CRUD: products, brands, users, orders)
- Loyalty points system (Cloudz Points) with tier display

### Phase 2 – Loyalty & Gamification (Complete)
- Referral program: username-based, $50 spend unlock, 50% bonus points
- Daily check-in system: ladder rewards, atomic MongoDB operations
- Weekly leaderboard: top 3 rewards, idempotency-safe
- Streak calculation: counts both "Paid" and "Completed" orders
- `isCurrentUser` fix on leaderboard for users outside top 20

### Phase 3b – Payment Methods Standardization (Complete — 2026-04)
- **6-method checkout**: Zelle (0%), Cash on Pickup (0%), Apple Pay (1.75%), Cash App (1.75%), Chime (1.75%), Card (disabled + "Coming Soon")
- **Backend fee enforcement**: `FEE_METHODS = {"Apple Pay", "Cash App", "Chime"}` in `order_routes.py` — server-side 1.75% fee, never trusted from client. Fixed prior bug where old `"apple_pay"` ID check never fired.
- **Apple Pay payment instructions**: Pre-payment flow via Apple Cash to (608) 417-9336 with two sections — "Via Messages" (4 steps) and "Via Wallet" (5 steps)
- **Removed**: Venmo from payment-instructions (not in active methods). Old 3% fee logic removed entirely.

### Phase 3 – Order Status Reward Centralization (Complete)
- `update_order_status_shared()` in `order_service.py` as single truth for reward triggers
- Web order status endpoint (`PATCH /api/orders/{id}/status`) added
- Admin and web both route through shared service

### Phase 4 – Product Catalog Repair (Complete — 2025-04)
- **Fixed 43 products with empty images** — all now have CDN URLs
- **CLIO Platinum 50K fix**: Kit → BigCommerce product/2810 image (full device); Pod → BigCommerce product/2816 image (pod cartridge only); Kit ≠ Pod images enforced
- **CLR 50K fix**: All 8 products now have BigCommerce product/2822 CDN image
- **Normalized 40+ local-upload products** to absolute HTTPS CDN URLs (Pulse X, CA6000, TN9000, RYL 35K, Pulse, Meloso Mini, Meloso, Meloso Max)
- **Created 17 new products** (all with verified CDN images, zero duplicates):
  - Geek Bar CLR 50K: Blue Razz Ice, Sour Strawberry, Sour Apple Ice
  - Geek Bar CLIO Platinum 50K POD: Dragonfruit Lemonade, Blue Razz Ice (stock updates)
  - RAZ VUE 50K Kit: Hawaiian Punch, Blue Razz Ice (stock updates)
  - Lost Mary Nera Fullview 70K POD: Scary Berry, Blue Razz Ice, Golden Berry, Pink Lemonade, Rocket Freeze
  - Lost Mary Nera 70K KIT: Pink Lemonade + Pink Blue, Scary Berry + Golden Berry, Blue Razz Ice
  - Geek Bar Pulse: Peach Lemonade (Thermal), Strawberry Kiwi (Thermal), Blueberry Watermelon, Strawberry Mango, Blow Pop / B-Burst (B-Pop)
  - Geek Bar RIA NV30K: Blue Razz Ice (NEW model, 30K puffs)
- **Backend fallback image**: `product_routes.py` now returns `https://clouddistrict.club/placeholder.png` for any null/empty image
- **Final 7 local-upload images fixed** (2026-04): RAZ RX50K Dew Edition (Code Green/Pink/Red/White — flavor-specific BigCommerce CDN) + Geek Bar RIA (Deep Purple/Dualicious/Watermelon B-Burst — nexussmoke CDN). Migration added to `migrate_catalog_images()` for production sync.
- **Total catalog**: 162 products | 0 empty images | 162 absolute HTTPS CDN URLs | 0 /api/uploads/ paths

---

## Credentials

| Role | Email/Username | Password |
|---|---|---|
| Admin | `jkaatz@gmail.com` / `dad` | `Just1n23$` |

### Auth Note
- Login API uses `identifier` field (accepts email OR username), NOT `email`

---

## Critical Notes for Developers

1. **FRONTEND API LOCK**: `frontend/constants/api.ts` is hardcoded to `https://api.clouddistrict.club`. Change to `process.env.EXPO_PUBLIC_BACKEND_URL` for preview testing, revert before commit.
2. **Reward Triggers**: MUST pass through `update_order_status_shared()` in `order_service.py`. Never duplicate reward logic in route files.
3. **Referral Contract**: `POST /api/auth/register` expects `referralCode` = referrer's username (case-insensitive).
4. **Login Field**: Uses `identifier` (not `email`) — accepts both email and username.
5. **Image Fallback**: `product_routes.py` → `resolve_image()` returns `https://clouddistrict.club/placeholder.png` for null/empty images.

---

## Mocked Services

| Service | File | Status |
|---|---|---|
| Email service | `backend/services/email_service.py` | MOCKED — no real emails sent |

---

## Prioritized Backlog

### P1 (Next)
- Display User Avatar (`profilePhoto`) on Account screen and in admin user list

### P2
- Modularize `frontend/app/(admin)/user-profile.tsx` (600+ lines → smaller components)
- Google Workspace Integration: Replace mocked email service via `integration_playbook_expert_v2`

### P3 (Future)
- Push notifications expansion
- Social sharing for referral links (X, Facebook, Instagram)
- Remaining 25 local-upload products → migrate to object storage (VIHO TRX, RX50K, Switch Ultra, Hookah X, Digiflavor SKY, ExtreBar, LTX 25K, Turbo X, RIA 25K)
