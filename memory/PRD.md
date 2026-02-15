# Cloud District Club - PRD

## Original Problem Statement
Build a mobile app called "Cloud District Club" for local pickup of disposable vape products for adults 21+.

## Core Features
- **Age Verification:** Mandatory 21+ gate
- **Design:** Dark premium theme, fast, and simple
- **Home Screen:** Featured products, shop by brand, loyalty points, "Order for Local Pickup" button
- **Product Catalog:** Categories, product details
- **Checkout Flow:** Local pickup only, payment via Zelle, Venmo, Cash App, Chime
- **Order Status System:** With push notifications
- **Loyalty Program:** "Cloudz Points" with tier-based redemption
- **Live Chat:** In-app chat
- **User Accounts:** Order history, loyalty tracking
- **Admin Dashboard:** Inventory, order management, payment confirmation, and full CRUD

## Tech Stack
- **Frontend:** React Native (Expo), TypeScript, Expo Router, Zustand
- **Backend:** Python, FastAPI
- **Database:** MongoDB
- **UI:** react-native-safe-area-context, expo-linear-gradient

## Architecture
```
/app
├── backend/
│   └── server.py              # All API routes
├── frontend/
│   ├── app/
│   │   ├── (tabs)/            # Main user tabs (home, shop, orders, account)
│   │   ├── admin/             # Admin tabs (orders, products, brands, users)
│   │   ├── auth/              # Login, register
│   │   ├── cloudz.tsx         # Cloudz tier rewards page
│   │   ├── checkout.tsx       # Checkout with tier rewards
│   │   ├── cart.tsx
│   │   └── ...
│   ├── store/                 # Zustand stores (authStore, cartStore)
│   ├── components/            # Shared components (GradientButton)
│   └── theme.ts               # Centralized theme
```

## What's Implemented (Feb 15, 2026)
- [x] Age verification gate (21+ DOB check)
- [x] User authentication (register, login, JWT)
- [x] Product catalog with brand filtering
- [x] Shopping cart
- [x] Checkout flow with payment methods (Zelle, Venmo, Cash App, Chime)
- [x] Order management (user & admin)
- [x] Admin Dashboard (CRUD for products, brands, users, orders)
- [x] Dark premium theme with centralized theme file
- [x] **Cloudz tier-based loyalty system** (NEW)
  - 5 tiers: Bronze Cloud (1k/$5), Silver Storm (5k/$30), Gold Thunder (10k/$75), Platinum Haze (20k/$175), Diamond Sky (30k/$300)
  - Redeem full tier amount only (no per-point $0.10 logic)
  - Locked/unlocked tier visualization
  - Active rewards applied at checkout
- [x] Admin Dashboard navigation fix (was /admin/dashboard → /admin/orders)

## Loyalty Tier System
| Tier | Points Required | Reward |
|------|----------------|--------|
| Bronze Cloud | 1,000 | $5.00 |
| Silver Storm | 5,000 | $30.00 |
| Gold Thunder | 10,000 | $75.00 |
| Platinum Haze | 20,000 | $175.00 |
| Diamond Sky | 30,000 | $300.00 |

**Rules:**
- Earn 1 point per $1 spent (awarded when order marked "Paid")
- Must redeem full tier amount (no partial)
- One active reward per tier at a time
- Rewards applied at checkout as discount

## Key API Endpoints
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/products`, `GET /api/products/{id}`
- `GET /api/brands`
- `POST /api/orders`, `GET /api/orders`
- `GET /api/loyalty/tiers` - Get tiers with unlock status
- `POST /api/loyalty/redeem` - Redeem a tier
- `GET /api/loyalty/rewards` - Active (unused) rewards
- `GET /api/loyalty/history` - All redemption history
- Admin: `/api/admin/orders`, `/api/admin/users`, etc.

## Prioritized Backlog
### P1 - Next
- [ ] Build User Profile Management UI (backend APIs exist)
- [ ] Implement Referral Program (UI + backend)

### P2 - Future
- [ ] Build Contact/Support Section
- [ ] Push notifications for order status
- [ ] Live chat feature

### P3 - Polish
- [ ] Admin screen component refactoring (break monolithic files)

## Credentials
- **Admin:** admin@clouddistrictclub.com / Admin123!
