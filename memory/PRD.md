# Cloud District Club - PRD

## Original Problem Statement
Build a mobile app called "Cloud District Club" for local pickup of disposable vape products for adults 21+.

## Core Features
- **Age Verification:** Mandatory 21+ gate (web + native)
- **Design:** Dark premium theme, fast, and simple
- **Home Screen:** Featured products, shop by brand, loyalty points, "Order for Local Pickup" button
- **Product Catalog:** Categories, product details
- **Checkout Flow:** Local pickup only, payment via Zelle, Venmo, Cash App, Chime
- **Order Status System:** With push notifications
- **Loyalty Program:** "Cloudz Points" with tier-based redemption
- **User Profile:** Edit name, email, phone, profile photo
- **User Accounts:** Order history, loyalty tracking
- **Admin Dashboard:** Inventory, order management, payment confirmation, and full CRUD

## Tech Stack
- **Frontend:** React Native (Expo), TypeScript, Expo Router, Zustand
- **Backend:** Python, FastAPI
- **Database:** MongoDB
- **UI:** react-native-safe-area-context, expo-linear-gradient, expo-image-picker

## Architecture
```
/app
├── backend/
│   └── server.py
├── frontend/
│   ├── app/
│   │   ├── (tabs)/            # Main user tabs (home, shop, orders, account)
│   │   ├── admin/             # Admin tabs (orders, products, brands, users)
│   │   ├── auth/              # Login, register
│   │   ├── age-gate.tsx       # 21+ verification (web HTML input + native DateTimePicker)
│   │   ├── cloudz.tsx         # Cloudz tier rewards page
│   │   ├── profile.tsx        # Edit profile page
│   │   ├── checkout.tsx       # Checkout with tier rewards
│   │   └── ...
│   ├── store/                 # Zustand stores (authStore, cartStore)
│   ├── components/            # Shared components (GradientButton)
│   └── theme.ts               # Centralized theme
```

## What's Implemented

### Feb 15, 2026 — Session 1 (Cloudz Loyalty + Admin Fix)
- [x] Fixed admin dashboard route (/admin/dashboard → /admin/orders)
- [x] Cloudz tier-based loyalty system (5 tiers: Bronze/Silver/Gold/Platinum/Diamond)
- [x] Checkout updated to use tier-based rewards instead of per-point $0.10 slider
- [x] Backend: /api/loyalty/tiers, /redeem, /rewards, /history endpoints
- [x] Auth token fix for all loyalty API calls

### Feb 15, 2026 — Session 2 (Profile + Age Gate)
- [x] User Profile Management UI (edit name, email, phone, profile photo)
- [x] Account page: Cloudz balance, unlocked tier badge, redemption history
- [x] Age Gate web fix: HTML date input on web, native DateTimePicker on iOS/Android
- [x] Profile edit page with expo-image-picker for photos

### Earlier (Pre-fork)
- [x] Age verification gate (21+ DOB check)
- [x] User authentication (register, login, JWT)
- [x] Product catalog with brand filtering
- [x] Shopping cart
- [x] Checkout flow with payment methods
- [x] Order management (user & admin)
- [x] Admin Dashboard (CRUD for products, brands, users, orders)
- [x] Dark premium theme with centralized theme file

## Loyalty Tier System
| Tier | Points | Reward |
|------|--------|--------|
| Bronze Cloud | 1,000 | $5.00 |
| Silver Storm | 5,000 | $30.00 |
| Gold Thunder | 10,000 | $75.00 |
| Platinum Haze | 20,000 | $175.00 |
| Diamond Sky | 30,000 | $300.00 |

## Key API Endpoints
- Auth: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`
- Products: `/api/products`, `/api/products/{id}`
- Brands: `/api/brands`
- Orders: `/api/orders`
- Loyalty: `/api/loyalty/tiers`, `/api/loyalty/redeem`, `/api/loyalty/rewards`, `/api/loyalty/history`
- Profile: `PATCH /api/profile`
- Admin: `/api/admin/orders`, `/api/admin/users`, etc.

## Prioritized Backlog
### P1 - Next
- [ ] Implement Referral Program (UI + backend for tracking referrals)

### P2 - Future
- [ ] Build Contact/Support Section
- [ ] Push notifications for order status
- [ ] Live chat feature

### P3 - Polish
- [ ] Admin screen component refactoring

## Credentials
- **Admin:** admin@clouddistrictclub.com / Admin123!
