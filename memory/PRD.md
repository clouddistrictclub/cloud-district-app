# Cloud District Club - Product Requirements Document

## Original Problem Statement
Build a mobile app called "Cloud District Club" for the local pickup of disposable vape products, restricted to users aged 21 and over.

## Core Requirements
- **Age Verification:** Mandatory 21+ age gate with DOB verification
- **Design:** Dark, premium, fast, simple UI
- **Home Screen:** Hero banner, shop by brand, loyalty points, featured products
- **Product Catalog:** Categories, detailed views
- **Checkout Flow:** Local pickup only, cash on pickup
- **Order Status System:** Track order progress
- **Loyalty Program ("Cloudz Points"):** Tier-based, streak bonuses
- **Referral Program:** Code-based with deep linking
- **User Accounts:** Order history, loyalty tracking, profile management
- **Admin Dashboard:** Full CRUD on inventory, orders, products, brands, users
- **Contact & Support:** Support tickets
- **Future:** Live chat, push notifications (done)

## Tech Stack
- **Frontend:** React Native, Expo (SDK 50+), Expo Router, TypeScript, Zustand
- **Backend:** Python, FastAPI, MongoDB Atlas (Production)
- **Deployment:** Backend on Railway (`https://api.clouddistrict.club`), Frontend preview on Emergent

## What's Been Implemented

### Core Features (Complete)
- Age gate with DOB verification
- User auth (login/register)
- Product catalog with brand filtering
- Checkout flow (Cash on Pickup)
- Order confirmation screen
- Order status tracking
- Loyalty program with streak bonuses
- Referral system
- Push notifications (Expo Push Notifications)
- Contact & Support with ticket system
- Admin dashboard (orders, products, brands, users)
- Production branding (logos, icons, splash screens)

### Feb 21, 2026 — Performance Pass & Product Card Polish
- **Hero Image Optimization:** Compressed mobile hero from 585KB to 301KB (resized to 750px wide)
- **Shared ProductCard Component:** Created `/components/ProductCard.tsx` with:
  - `React.memo()` for render optimization
  - `loading="lazy"` on web product images
  - 4:3 aspect ratio image containers
  - Bold price ($17px, weight 800)
  - Puff count pills (subtle gray badges)
  - Brand/Name/Flavor hierarchy
  - Sold Out badge overlay
  - Consistent dark card styling (#141414 + #1e1e1e border)
- **Re-render Prevention:** Fixed `useCartStore` selector (was calling `getItemCount()` function, now uses inline reducer). Added `useCallback` to data loaders.
- **Login Screen Hero:** Updated to match home screen (26vh, cover, gradient fade from hero to form)
- **Header Refinement:** Replaced skyline logo with CD app icon. Added animated side drawer (Profile, Cloudz Points, Orders, Support, Admin). Safe area handling for iOS.
- **Code Cleanup:** Removed duplicate product card styles from both home.tsx and shop.tsx. Both now use shared ProductCard component.

### Earlier Sessions
- Production deployment to Railway
- Production database seeding
- Order confirmation screen
- Push notifications integration
- Streak bonus system
- Contact & Support section
- Production branding integration
- Responsive hero banner (26vh, cover, edge-to-edge on mobile)

## Prioritized Backlog

### P0 (Next)
- Live chat implementation

### P1
- Fix invalid image data in DB (`data:image/png;base64,admintest`)
- Clean deployment duplication (`server_enhanced.py` → guide user to update Railway start command)

### P2
- Add maxWidth constraint for product cards on desktop viewport
- Refactor backend monolith (`server.py`) into smaller routers
- Refactor large admin screen components

### P3
- Remove `server_enhanced.py` workaround file

## Key Files
- `/app/frontend/app/(tabs)/home.tsx` — Home screen
- `/app/frontend/app/(tabs)/shop.tsx` — Shop tab
- `/app/frontend/components/ProductCard.tsx` — Shared product card
- `/app/frontend/app/auth/login.tsx` — Login screen
- `/app/backend/server.py` — Main backend
- `/app/server_enhanced.py` — Railway deployment duplicate (tech debt)

## DB Schema
- **users**: `{_id, email, password, name, phone, loyaltyPoints, referralCode, isAdmin}`
- **cloudz_ledger**: `{_id, userId, type, amount, reference, balanceAfter, createdAt}`
- **orders**: `{_id, userId, products, totalAmount, status, paymentMethod}`
- **push_tokens**: `{_id, userId, token}`
- **support_tickets**: `{_id, userId, subject, message, status}`

## Credentials
- **Admin:** jkaatz@gmail.com / Just1n23$
- **Production API:** https://api.clouddistrict.club
