# Cloud District Club - Product Requirements Document

## Original Problem Statement
Build a mobile app called "Cloud District Club" for the local pickup of disposable vape products, restricted to users aged 21 and over.

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
- Order confirmation screen, order status tracking
- Loyalty program ("Cloudz Points") with streak bonuses
- Referral system
- Push notifications (Expo Push Notifications)
- Contact & Support with ticket system
- Admin dashboard (orders, products, brands, users, ledger)
- Production branding (logos, icons, splash screens)

### Feb 21, 2026 — Performance Pass & Product Card Polish
- Hero image optimized (585KB → 301KB)
- Shared `ProductCard` component with `React.memo`, `loading="lazy"`, 4:3 aspect ratio, bold price, puff pills, sold-out badge
- Fixed `useCartStore` selector re-renders, `useCallback` on loaders
- Login hero matched to home (26vh, cover, gradient)
- Header: app icon + animated side drawer

### Feb 21, 2026 — Live Chat (P0)
- **Backend:** WebSocket `/api/ws/chat/{chat_id}` with JWT auth, `ConnectionManager` for broadcasting, `chat_messages` + `chat_sessions` MongoDB collections, REST endpoints for history + admin sessions
- **Frontend (User):** Floating chat FAB (bottom-right, above tab bar), slide-up chat modal, real-time messaging via WebSocket, message history, empty state
- **Frontend (Admin):** Chats tab in admin dashboard, session list with online status indicators, per-conversation view with reply capability
- **Hidden for admin users** — admin uses admin dashboard Chats tab instead
- **Testing:** 100% pass (11/11 backend, all frontend features verified)

## Key Files
- `/app/frontend/components/ChatBubble.tsx` — Floating chat FAB + modal
- `/app/frontend/components/ProductCard.tsx` — Shared product card
- `/app/frontend/app/(tabs)/_layout.tsx` — Tab layout with ChatBubble
- `/app/frontend/app/admin/chats.tsx` — Admin chat management
- `/app/backend/server.py` — Main backend (all endpoints)
- `/app/server_enhanced.py` — Railway deployment copy (must stay in sync)

## DB Collections
- **users**, **orders**, **cloudz_ledger**, **push_tokens**, **support_tickets**
- **chat_messages**: `{chatId, senderId, senderName, isAdmin, message, createdAt}`
- **chat_sessions**: `{chatId, userId, lastMessage, lastMessageAt, updatedAt, createdAt}`

## Prioritized Backlog

### P1 (Next)
- Fix invalid image data in DB + implement product image upload in Admin
- Clean Railway deployment config (remove `server_enhanced.py` duplication)

### P2
- Desktop product card max-width constraint
- Backend monolith refactoring
- Admin screen refactoring

## Credentials
- **Admin:** jkaatz@gmail.com / Just1n23$
- **Test user:** testuser@cloud.club / Test1234!
- **Production API:** https://api.clouddistrict.club
