# Cloud District Club - PRD

## Original Problem Statement
Build a mobile app called "Cloud District Club" for local pickup of disposable vape products for adults 21+.

## Tech Stack
- **Frontend:** React Native (Expo), TypeScript, Expo Router, Zustand
- **Backend:** Python, FastAPI
- **Database:** MongoDB

## Architecture
```
/app
├── backend/
│   └── server.py
├── frontend/
│   ├── app/
│   │   ├── (tabs)/            # Main user tabs (home, shop, orders, account)
│   │   ├── admin/             # Admin tabs (orders, products, brands, users)
│   │   ├── auth/              # Login, register (w/ referral code)
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

### Referral Program (Feb 15, 2026 - Latest)
- [x] Auto-generated 7-char referral codes for all users
- [x] Optional referral code field on registration
- [x] Referral reward trigger on first paid order: referrer +2,000 Cloudz, referred +1,000 Cloudz
- [x] Abuse protection: invalid code rejection, referralRewardIssued flag prevents double rewards
- [x] Refer & Earn section on Account page: code display, copy button, referral count, Cloudz earned
- [x] Case-insensitive referral code matching

### Cloudz Tier Loyalty System (Feb 15, 2026)
- [x] 5 tiers: Bronze Cloud (1k/$5), Silver Storm (5k/$30), Gold Thunder (10k/$75), Platinum Haze (20k/$175), Diamond Sky (30k/$300)
- [x] Redeem full tier amount only
- [x] Active rewards applied at checkout

### User Profile Management (Feb 15, 2026)
- [x] Edit name, email, phone, profile photo
- [x] Tier badge display on account page
- [x] Redemption history

### Age Gate Web Fix (Feb 15, 2026)
- [x] HTML date input on web, native DateTimePicker on iOS/Android

### Core Features (Pre-fork)
- [x] Age verification, auth, product catalog, shopping cart
- [x] Checkout (Zelle, Venmo, Cash App, Chime)
- [x] Order management, Admin CRUD dashboard
- [x] Dark premium theme

## Loyalty Tier System
| Tier | Points | Reward |
|------|--------|--------|
| Bronze Cloud | 1,000 | $5.00 |
| Silver Storm | 5,000 | $30.00 |
| Gold Thunder | 10,000 | $75.00 |
| Platinum Haze | 20,000 | $175.00 |
| Diamond Sky | 30,000 | $300.00 |

## Referral System
- Referrer: +2,000 Cloudz per successful referral
- Referred: +1,000 Cloudz after first paid order
- One-time reward per referred user (referralRewardIssued flag)

## Key API Endpoints
- Auth: `/api/auth/register` (w/ referralCode), `/api/auth/login`, `/api/auth/me`
- Products: `/api/products`, `/api/products/{id}`
- Orders: `/api/orders`, `PATCH /api/admin/orders/{id}/status` (triggers referral rewards)
- Loyalty: `/api/loyalty/tiers`, `/api/loyalty/redeem`, `/api/loyalty/rewards`, `/api/loyalty/history`
- Profile: `PATCH /api/profile`

## Prioritized Backlog
### P2 - Future
- [ ] Build Contact/Support Section
- [ ] Push notifications for order status
- [ ] Live chat feature

### P3 - Polish
- [ ] Admin screen component refactoring

## Credentials
- **Admin:** admin@clouddistrictclub.com / Admin123! (Referral code: STAV20H)
