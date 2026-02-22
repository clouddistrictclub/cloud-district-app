# Cloud District Club - Product Requirements Document

## Original Problem Statement
Mobile app called "Cloud District Club" for the local pickup of disposable vape products, restricted to users aged 21 and over.

## Core Requirements
- **Age Verification:** Mandatory 21+ age gate
- **Design:** Dark, premium, fast, simple UI
- **Home Screen:** Featured products, shop by brand, loyalty points, "Order for Local Pickup" CTA
- **Product Catalog:** Category organization with detailed product views
- **Checkout Flow:** Local pickup only, manual payment methods
- **Order Status System:** Track order progress
- **Loyalty Program ("Cloudz Points"):** Tier-based system with streak bonus
- **Referral Program:** Code-based system with deep linking
- **User Accounts:** Order history, loyalty status, profile management
- **Admin Dashboard:** Full CRUD on products, brands, users, inventory, orders
- **Contact & Support:** Ticket system
- **Live Chat:** Real-time WebSocket chat with typing indicators and read receipts
- **Bulk Discount:** 10% discount when total cart quantity >= 10

## Tech Stack
- **Frontend**: React Native, Expo, Expo Router, TypeScript, Zustand
- **Backend**: FastAPI, Python, MongoDB (Pydantic models)
- **Deployment**: Supervisor for process management

## Architecture
```
/app
├── backend/
│   ├── .env
│   ├── server.py
│   ├── utils/email.py
│   └── uploads/ (products/, brands/)
├── frontend/
│   ├── app/ (Expo Router pages)
│   ├── store/ (cartStore.ts, authStore.ts)
│   ├── components/ (ChatBubble.tsx, HeroBanner.tsx)
│   └── babel.config.js (NEW - import.meta fix)
└── server_enhanced.py (to be removed)
```

## What's Been Implemented
### Completed Features
- Age Gate with DOB verification
- User authentication (login/register)
- Product catalog with categories and detailed views
- Shopping cart with persistence (localStorage/AsyncStorage)
- Checkout flow with local pickup
- Admin dashboard (products, brands, users, orders CRUD)
- Loyalty program ("Cloudz Points")
- Referral program
- Live chat (WebSocket)
- Support ticket system
- Image upload system (file-based, not base64)
- Hero banner component (shared across screens)
- Draggable chat FAB with haptic feedback
- Bulk discount (10% at 10+ items)

### Recent Critical Fix (Feb 2026)
- **P0: Cart Persistence** — FIXED
  - Root Cause #1: `import.meta` error in client bundle prevented React hydration entirely. Client-side JS never executed.
  - Root Cause #2: Zustand `persist` middleware incompatible with Expo web SSR.
  - Fix: Added `babel-plugin-transform-import-meta` to transform `import.meta` references. Replaced Zustand persist with manual localStorage read/write.
  - Files changed: `cartStore.ts`, `_layout.tsx`, `cart.tsx`, `babel.config.js` (new)

## Credentials
- **Admin**: jkaatz@gmail.com / Just1n23$
- **Test User**: testuser@clouddistrict.club / Test1234!

## Upcoming Tasks (Priority Order)
1. **P1: Consolidate server.py & server_enhanced.py** — Remove duplicate
2. **P2: Backend monolith refactor** — Restructure for scalability
3. **P2: Admin screen modularization** — Break down large admin components
4. **P2: Google Workspace email integration** — Implement email sending
5. **P3: Push notifications expansion**

## Key API Endpoints
- `POST /api/auth/login` — User login
- `GET /api/products` — List products
- `POST /api/orders` — Create order
- `POST /api/upload/product-image` — Upload product image
- `POST /api/upload/brand-image` — Upload brand image
- `GET /api/uploads/products/{filename}` — Serve product image
- `GET /api/uploads/brands/{filename}` — Serve brand image

## Known Notes
- Email utility (`backend/utils/email.py`) is scaffolded but MOCKED — not sending emails
- `CI=true` is set in supervisor config (read-only), causing Metro to run in CI mode
- The `babel-plugin-transform-import-meta` is essential for web client-side JS to work
