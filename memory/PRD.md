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
- **Chat FAB visible for ALL authenticated users** (admin and regular)
- **Testing:** 100% pass (11/11 backend, all frontend features verified)

### Feb 21, 2026 — Chat Enhancements
- **Typing Indicators:** TypingDots animated component, throttled emission (2s), 3s auto-clear. Works for both user ChatBubble and admin chats.
- **Read Receipts:** checkmark (sent) / checkmark-done+blue (read) on last sent message. WebSocket `type: 'read'` event triggers bulk update on unread messages. Both user and admin sides send/receive read receipts.

### Feb 21, 2026 — Bulk Discount
- 10% discount when total cart quantity >= 10 items
- Discount shown as line item in cart summary with pricetag icon
- Hint text "Add X more items for 10% off!" when below threshold
- Proper monetary rounding (Math.round to cents)

### Feb 21, 2026 — P0 Validation (All Items PASS)
- **P0-1 Hero Layout:** Hero height 26vh (219.4px on iPhone 14), no black gap, proper safe area. Native uses `Math.round(screen.height * 0.26)`.
- **P0-2 Chat FAB:** Visible for all authenticated users (admin + regular), 56x56px blue circle at bottom-right.
- **P0-3 Chat Enhancements:** Typing indicators + read receipts working in both user and admin chat views. Admin chat now properly filters typing/read WebSocket events.
- **P0-4 Bulk Discount:** 10% discount at 10+ items, correct math, dynamic UI updates. 13/13 backend tests passed.

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
