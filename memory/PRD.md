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

### Cash on Pickup Payment Method (Feb 15, 2026 - Latest)
- [x] "Cash on Pickup" added as first payment option, no processing fee
- [x] Order status set to "Awaiting Pickup (Cash)" on creation
- [x] Cloudz points awarded only when admin marks order as "Paid"
- [x] Existing digital payment logic (Zelle, Venmo, Cash App, Chime) unchanged

### Leaderboard (Feb 15, 2026)
- [x] `GET /api/leaderboard` endpoint with projection-only query (no full docs)
- [x] Returns `{byPoints, byReferrals}` top 20 each, sorted descending
- [x] Display name privacy (firstName + last initial), tier resolution, isCurrentUser flag
- [x] Frontend screen with Points/Referrals tabs, rank medals, tier badges, current user highlight
- [x] Account page "Leaderboard" menu item with trophy icon

### Admin Cloudz Ledger (Feb 15, 2026)
- [x] `GET /api/admin/ledger` admin-only endpoint with pagination (skip/limit), userId and type filters
- [x] User email joined from users collection for each entry
- [x] Admin "Ledger" tab in dashboard with filter chips, userId search, +/- color formatting
- [x] Non-admin requests blocked (403)

### Cloudz Transaction Ledger + History UI (Feb 15, 2026)
- [x] `cloudz_ledger` MongoDB collection logging every Cloudz change
- [x] All 5 mutation points instrumented: purchase_reward, referral_bonus (x2), tier_redemption, admin_adjustment
- [x] `GET /api/loyalty/ledger` endpoint returns chronological transactions
- [x] Cloudz History screen with type labels, +/- color formatting, balanceAfter tracking
- [x] Account page menu link to Cloudz History

### Referral Deep Linking - Phase 2 (Feb 15, 2026)
- [x] Universal link format: `https://clouddistrict.club/register?ref=CODE`
- [x] Auto-fill referral code from URL `?ref=` param on register page
- [x] Ignore ref param if user is already logged in
- [x] "Share Referral Link" button on Account page with native Share API
- [x] Full link preview displayed before share button
- [x] URL scheme set to `clouddistrict` in app.json

### Referral Program - Phase 1 (Feb 15, 2026)
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
- Deep link format: `https://clouddistrict.club/register?ref=CODE`
- Share via native Share API from Account page

## Growth Strategy Roadmap
- [x] Phase 1: Referral code system (DONE)
- [x] Phase 2: Deep link sharing (DONE)
- [ ] Phase 3: Share incentives + streak bonus
- [ ] Phase 4: Push notifications
- [ ] Phase 5: Paid ads / influencer seeding

## Key API Endpoints
- Auth: `/api/auth/register` (w/ referralCode), `/api/auth/login`, `/api/auth/me`
- Products: `/api/products`, `/api/products/{id}`
- Orders: `/api/orders` (supports "Cash on Pickup" + digital methods), `PATCH /api/admin/orders/{id}/status` (triggers referral rewards + ledger)
- Loyalty: `/api/loyalty/tiers`, `/api/loyalty/redeem`, `/api/loyalty/rewards`, `/api/loyalty/history`, `/api/loyalty/ledger`
- Admin Ledger: `GET /api/admin/ledger` (paginated, ?userId=, ?type=, admin-only)
- Profile: `PATCH /api/profile`

## Payment Methods
- Supported: Zelle, Venmo, Cash App, Chime, Cash on Pickup
- "Cash on Pickup" sets order status to "Awaiting Pickup (Cash)"; others set "Pending Payment"
- Verified working: Feb 2026

## Post-Checkout Screens
- **Order Confirmation** (`/order-confirmation`): For "Cash on Pickup" orders — shows order #, status, pickup instructions, store address, "Open in Maps" + "View My Orders" buttons
- **Payment Instructions** (`/payment-instructions`): For digital payment methods (Zelle, Venmo, Cash App, Chime) — shows payment details, deep links, copy-to-clipboard
- Routing logic in `checkout.tsx` lines 104-108

## Push Notifications
- `POST /api/push/register`: Stores Expo push tokens (keyed by userId, upsert)
- Dispatched via Expo Push API (`exp.host/--/api/v2/push/send`) when admin updates order status
- Frontend: Token registered on login/register/loadToken (mobile only, skipped on web)
- Root layout (`_layout.tsx`): Notification handler + received listener configured

## Prioritized Backlog
### P1 - Growth (Next)
- [x] Phase 3: Streak bonus (Feb 2026) — +50/+100/+200/+500 Cloudz for consecutive weekly purchases
- [x] Phase 4: Push notifications (Feb 2026)

## Streak Bonus System
- Tracks consecutive ISO weeks (Mon–Sun) with at least one Paid order
- Bonus scale: Week 2: +50, Week 3: +100, Week 4: +200, Week 5+: +500 Cloudz
- Awarded once per ISO week via `maybe_award_streak_bonus()` when first order marked Paid
- Logged to `cloudz_ledger` as type `streak_bonus` with `isoYear` + `isoWeek` for idempotency
- `GET /api/loyalty/streak`: Returns streak count, currentBonus, nextBonus, daysUntilExpiry
- Frontend: Streak card on Account tab between Cloudz Points and menu items

### P2 - Future
- [ ] Phase 5: Paid ads / influencer seeding
- [x] Build Contact/Support Section (Feb 2026)
- [ ] Live chat feature

### P3 - Polish
- [ ] Refactor server.py into separate API routers
- [ ] Admin screen component refactoring

## Contact & Support
- `POST /api/support/tickets`: Creates ticket (subject, message) in `support_tickets` collection
- `GET /api/admin/support/tickets`: Admin-only paginated list with `?status=` filter
- Frontend: `/support` screen with contact info + "Send Message" form
- Account tab: "Contact & Support" menu item
- Contact: support@clouddistrictclub.com, (555) 123-4567, Mon–Sat 10AM–8PM

## Production Deployment
- **API**: https://api.clouddistrict.club (Railway)
- **Frontend env**: EXPO_PUBLIC_BACKEND_URL=https://api.clouddistrict.club
- **Admin**: jkaatz@gmail.com (isAdmin: true)
- **Seeded Data**: 5 brands (Geek Bar, Lost Mary, RAZ, Elf Bar, Flum) + 10 products
- **Seed script**: /app/backend/seed_production.py
- **Note**: Production API runs older code version — some newer endpoints (loyalty, streak, push, support, admin ledger) may not be available until Railway is redeployed with latest code

## Credentials
- **Admin:** jkaatz@gmail.com (production)
- **Dev Admin:** admin@clouddistrictclub.com / Admin123! (local preview only)
