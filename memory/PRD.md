# Cloud District Club - Product Requirements Document
_Last updated: 2026-04-01_

## Original Problem Statement
Mobile-first web app for local pickup of disposable vape products, restricted to 21+ users.

## Tech Stack
- Frontend: React Native / Expo 54 / Expo Router / TypeScript / Zustand
- Backend: FastAPI / Python / MongoDB (Motor async)
- Deploy: Backend on Railway (api.clouddistrict.club), Frontend on Emergent (clouddistrict.club)
- Frontend API is HARDCODED to https://api.clouddistrict.club in constants/api.ts

## Architecture
```
/app
├── backend/
│   ├── server.py / main.py
│   ├── database.py
│   ├── models/schemas.py
│   ├── routes/
│   │   ├── admin_routes.py     # handle_order_completed (centralized)
│   │   ├── auth_routes.py      # inline referral logic on signup
│   │   └── order_routes.py
│   ├── services/
│   │   └── loyalty_service.py  # log_cloudz_transaction, DB writes
│   └── tests/
│       └── test_loyalty_referral.py
├── frontend/
│   ├── app/
│   │   ├── (tabs)/             (Home, Shop, Orders, Account)
│   │   ├── cloudz.tsx
│   │   ├── cloudz-history.tsx  # Safe area layout fixed
│   │   └── admin/
│   │       └── cloudz-ledger.tsx # Safe area layout fixed
│   ├── constants/
│   │   ├── api.ts              # HARDCODED to production API URL
│   │   └── ledger.ts           # Centralized label/color/icon mapping
│   └── store/authStore.ts
├── SYSTEM_EXPORT.md
└── memory/
    ├── PRD.md
    └── test_credentials.md
```

## Key Business Rules
- Age gate: 21+ mandatory
- Products: Disposable vapes, local pickup only
- Payment: Manual (no payment processor)

## Cloudz Earn Rate
- 3 Cloudz per $1 spent
- Formula: `points_earned = int(order_data.total) * 3`
- Rewards trigger ONLY when order.status == "Completed"

## Loyalty Tiers
- Bronze Cloud  — 1,000 pts → $5.00
- Silver Storm  — 5,000 pts → $30.00
- Gold Thunder  — 10,000 pts → $75.00
- Platinum Haze — 20,000 pts → $175.00
- Diamond Sky   — 30,000 pts → $300.00

## Referral System
- New user with valid referral code receives +500 bonus (total: 500 signup + 500 referral = 1000)
- Referrer gets 1500 pts PENDING (created at signup of referred user)
- Pending 1500 UNLOCKS when referred user spends $50 cumulative
- Referrer also gets 50 pts bonus on each referred user's completed order (while pending is locked)
- No self-referral allowed

## DB Schema (key fields)
- users: `loyaltyPoints`, `creditBalance`, `referralCode`, `referredBy`, `referralUnlocked`, `referralCount`
- cloudz_ledger: `type`, `amount`, `balanceAfter`, `userId`, `status` (pending/unlocked), `referredUserId`
- orders: `status`, `discountApplied`, `loyaltyRewardIssued`, `finalTotal`, `userId`

## Key API Endpoints
- POST /api/auth/register — Signup with optional referralCode
- PATCH /api/admin/orders/{order_id}/status — Triggers handle_order_completed on "Completed"
- GET /api/auth/me — Returns updated user profile
- GET /api/debug/env — Shows which MongoDB database is connected

## Reward Logic Flow (on order "Completed")
1. purchase_reward: loyaltyPoints += int(finalTotal) * 3
2. referral_order_reward: if referrer exists and not yet unlocked → referrer +50
3. referral_unlock: if referred user total spend >= $50 → unlock pending 1500 for referrer

## What's Been Built
- Age gate (21+ verification)
- Full product catalog with categories and brands
- Shopping cart and checkout flow (local pickup, manual payment)
- Order status system (Pending → Paid → Ready for Pickup → Completed)
- Cloudz (loyalty) points system with tier display
- Referral program with pending/unlock flow
- User account: order history, loyalty status, profile photo
- Admin dashboard: products, brands, users, orders, inventory
- Live chat (WebSocket)
- Store credit system
- Push notifications (partial)
- Cloudz Ledger UI (fintech-style with dark cards, running balance)

## Email Service
- MOCKED in backend/services/email_service.py — No actual emails sent

## Known Constraints
- Frontend hardcoded to production API — test new features against preview backend by temporarily editing constants/api.ts
- Safe Area Layout: Use `useSafeAreaInsets().top` on header wrapper; avoid SafeAreaView for scrollable content

## Credentials
- Admin: jkaatz@gmail.com / Just1n23$ / username: dad

## P0/P1 Backlog
- P1: Display user profilePhoto on Account screen and admin user list
- P2: Modularize frontend/app/(admin)/user-profile.tsx (600+ lines)
- P2: Real email sending (Google Workspace / SendGrid integration)
- P3: Push notifications expansion
- P3: Social sharing for referral links (X, Facebook, Instagram)
