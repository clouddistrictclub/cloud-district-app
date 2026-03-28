# Cloud District Club — Complete System Export

> Generated from live codebase. Every field, rule, and endpoint below is exact.

---

## 1. AUTH SYSTEM

### 1.1 Registration

**Endpoint:** `POST /api/auth/register`
**Rate limit:** 5/minute

**Request body (`UserRegister`):**

| Field | Type | Required | Constraints |
|---|---|---|---|
| `email` | EmailStr | YES | Must be valid email, unique (case-sensitive match in DB) |
| `password` | string | YES | min 8, max 128 characters |
| `firstName` | string | YES | min 1, max 50 |
| `lastName` | string | YES | min 1, max 50 |
| `dateOfBirth` | string | YES | Format `YYYY-MM-DD`, must be 21+ years old (server enforced) |
| `phone` | string | NO | max 20 chars, stored as-is (frontend formats `(XXX) XXX-XXXX`) |
| `username` | string | YES | 3–20 chars, `[a-zA-Z0-9_]`, auto lowercased+trimmed, unique, not in reserved list |
| `referralCode` | string | NO | max 50, must match an existing user's username (case-insensitive) |
| `profilePhoto` | string | NO | base64 data URI string (e.g. `data:image/jpeg;base64,...`), stored raw in DB |

**Username rules:**
- Regex: `^[a-zA-Z0-9_]{3,20}$`
- Normalized: `.strip().lower().replace(" ", "")` before storage
- Uniqueness: case-insensitive check
- Immutable after creation (user can change via `PATCH /api/me/username`, admin via `PATCH /api/admin/users/{id}/username`)
- Reserved: `admin`, `support`, `api`, `clouddistrict`, `orders`, `root`, `help`

**Registration side effects:**
1. User document created in `users` collection
2. `referralCode` is set to the user's username
3. `referralRewardIssued` set to `false`
4. +500 Cloudz signup bonus (ledger type: `signup_bonus`)
5. If `referralCode` provided and valid:
   - Self-referral check: if referrer username == own username, `referredBy` is set to `null`
   - +500 Cloudz to new user (ledger type: `referral_new_user_bonus`)
   - +1500 Cloudz to referrer (ledger type: `referral_signup_bonus`)
   - Referrer's `referralCount` incremented by 1
   - Referrer's `referralRewardsEarned` incremented by 1500

**Response (`Token`):**

```json
{
  "access_token": "jwt...",
  "token_type": "bearer",
  "user": {
    "id": "mongo_objectid_string",
    "email": "...",
    "firstName": "...",
    "lastName": "...",
    "dateOfBirth": "YYYY-MM-DD",
    "phone": "...",
    "isAdmin": false,
    "loyaltyPoints": 500,        // or 1000 if referred
    "profilePhoto": "...",       // base64 or null
    "referralCode": "username",
    "username": "username",
    "referralCount": 0,
    "referralRewardsEarned": 0,
    "referredByUserId": null,
    "creditBalance": 0.0,
    "isDisabled": false
  }
}
```

### 1.2 Login

**Endpoint:** `POST /api/auth/login`
**Rate limit:** 10/minute

**Request body (`UserLogin`):**

| Field | Type | Required | Constraints |
|---|---|---|---|
| `identifier` | string | YES | min 1, max 200 — accepts email OR username |
| `password` | string | YES | min 1 |

**Login logic:**
- If `identifier` contains `@` → look up by `email` (exact, lowercased)
- Otherwise → look up by `username` (case-insensitive regex match)
- Checks `isDisabled` flag — returns 403 if disabled
- Password verified with bcrypt (`passlib`)

**Response:** Same `Token` shape as registration.

### 1.3 Get Current User

**Endpoint:** `GET /api/auth/me`
**Auth:** Bearer token required

**Response:** `UserResponse` shape (same as `user` inside Token).

### 1.4 JWT Token

- Algorithm: `HS256`
- Expiry: 7 days (10080 minutes)
- Payload: `{ "sub": "<user_objectid>", "exp": <unix_timestamp> }`
- Secret: `JWT_SECRET_KEY` env var
- Force logout: if `user.forceLogoutAt > token.iat`, token is rejected

### 1.5 Password Hashing

- Library: `passlib` with `bcrypt` scheme
- `get_password_hash(plain)` → bcrypt hash
- `verify_password(plain, hashed)` → bool

### 1.6 Age Verification

**Frontend age gate (`age-gate.tsx`):**
- Shows a modal on app launch if `cloudDistrictAgeVerified` is not set in AsyncStorage/localStorage
- Single button: "I am 21+ Enter"
- On click: stores `cloudDistrictAgeVerified = "true"` and allows entry
- This is a client-side gate only

**Backend enforcement:**
- `POST /api/auth/register` parses `dateOfBirth`, calculates age as `(now - dob).days / 365.25`
- Returns 400 if age < 21

---

## 2. REFERRAL SYSTEM

### 2.1 How Referral Codes Work

- Every user's referral code IS their username
- Stored as `referralCode` on the user document (set to `username` at registration)
- Case-insensitive matching: `{"username": {"$regex": "^escaped_input$", "$options": "i"}}`
- Stored in `referredBy` field on the referred user

### 2.2 Signup WITHOUT Referral

| Recipient | Amount | Ledger Type | Description |
|---|---|---|---|
| New user | +500 | `signup_bonus` | "Welcome to Cloud District Club!" |

**Total to user: 500 Cloudz**

### 2.3 Signup WITH Referral

| Recipient | Amount | Ledger Type | Description |
|---|---|---|---|
| New user | +500 | `signup_bonus` | "Welcome to Cloud District Club!" |
| New user | +500 | `referral_new_user_bonus` | "Referral bonus — signed up with a referral!" |
| Referrer | +1500 | `referral_signup_bonus` | "Referral signup bonus — {firstName} joined" |

**Total to user: 1000 Cloudz**
**Total to referrer: 1500 Cloudz**

Referrer also gets: `referralCount += 1`, `referralRewardsEarned += 1500`

### 2.4 Admin Assigns Referrer After Signup

**Endpoint:** `PATCH /api/admin/users/{user_id}/referrer`

**Request:** `{ "referrerIdentifier": "username_or_email_or_id" }`

**Lookup order:** `referralCode` → `username` → `email` → `ObjectId` (all case-insensitive)

**Behavior:**
- If user previously had NO referrer (`referredBy` was null/empty):
  - +500 to user (type: `referral_new_user_bonus`)
  - +1500 to referrer (type: `referral_signup_bonus`)
- If user already had a referrer: no rewards issued (only `referredBy` field updated)
- Self-referral blocked (returns 400)
- Removing referrer: send empty/null `referrerIdentifier`

**Idempotency:**
- `referral_new_user_bonus`: checked by `userId + type` (max one per user lifetime)
- `referral_signup_bonus`: checked by `userId + type + referredUserId` (max one per referrer-user pair)

### 2.5 Per-Order Referral Reward

When an order is marked `Paid` (status change from Pending Payment or Awaiting Pickup):
- System checks `order.referralRewardIssued` flag (atomic flip with `find_one_and_update`)
- Looks up `buyer.referredBy` → resolves to referrer user
- Reward = `floor(order.total * 0.5)` Cloudz
- Referrer gets: `loyaltyPoints += reward`, `referralRewardsEarned += reward`
- Ledger type: `referral_reward`
- Idempotent: `referralRewardIssued` flag on order document

### 2.6 Referral Earnings Query

**Endpoint:** `GET /api/me/referral-earnings`
**Response:**
```json
{
  "totalReferralCloudz": 3000,
  "referralOrderCount": 2
}
```
Aggregates `cloudz_ledger` entries where `type = "referral_reward"`.

---

## 3. CLOUDZ / LOYALTY SYSTEM

### 3.1 Complete List of Ledger Types

| Type | Amount Direction | Color (frontend) | Description |
|---|---|---|---|
| `signup_bonus` | + (always +500) | Green `#22c55e` | Welcome bonus on registration |
| `referral_new_user_bonus` | + (always +500) | Green `#22c55e` | Bonus for signing up with a referral |
| `referral_signup_bonus` | + (always +1500) | Green `#22c55e` | Bonus to referrer when someone signs up using their code |
| `referral_reward` | + (variable, 50% of order) | Green `#22c55e` | Per-order referral reward to referrer |
| `purchase_reward` | + (variable, `total * 3`) | Green `#22c55e` | Purchase reward when order is marked Paid |
| `streak_bonus` | + (50–500) | Green `#22c55e` | Weekly streak bonus |
| `tier_redemption` | - (negative) | Red `#ef4444` | Points spent to redeem a tier reward |
| `admin_adjustment` | +/- (any) | Orange `#f59e0b` | Manual admin point adjustment |
| `credit_adjustment` | 0 (Cloudz amount is 0) | Orange `#f59e0b` | Store credit adjustment (tracks credit, not Cloudz) |

### 3.2 Reward Rules

**Signup:** +500 Cloudz (always)
**Referral (signup):** +500 to new user, +1500 to referrer
**Purchase:** `floor(order.total) * 3` Cloudz, issued when order status → `Paid`
**Referral (per-order):** `floor(order.total * 0.5)` Cloudz to referrer, when order → `Paid`
**Streak bonus:**
- 2 consecutive weeks: +50
- 3 consecutive weeks: +100
- 4 consecutive weeks: +200
- 5+ consecutive weeks: +500
- Awarded once per ISO week, on the first `Paid` order of that week

**Admin adjustment:** Any integer amount, positive or negative

### 3.3 Loyalty Tiers

| Tier ID | Name | Points Required | Reward ($ off) | Icon |
|---|---|---|---|---|
| `tier_1` | Bronze Cloud | 1,000 | $5.00 | `cloud-outline` |
| `tier_2` | Silver Storm | 5,000 | $30.00 | `cloud` |
| `tier_3` | Gold Thunder | 10,000 | $75.00 | `thunderstorm-outline` |
| `tier_4` | Platinum Haze | 20,000 | $175.00 | `thunderstorm` |
| `tier_5` | Diamond Sky | 30,000 | $300.00 | `diamond` |

Tier colors: Bronze `#CD7F32`, Silver `#C0C0C0`, Gold `#FFD700`, Platinum `#A8B8D0`, Diamond `#B9F2FF`

**Redemption:** Points are SPENT (deducted). Creates a reward in `loyalty_rewards` collection. User can apply one unused reward at checkout. Cannot redeem same tier if an unused reward for that tier exists.

### 3.4 Ledger Entry Structure

Each entry in `cloudz_ledger`:

```json
{
  "userId": "string (ObjectId)",
  "type": "string (one of the types above)",
  "amount": "int (positive or negative)",
  "balanceAfter": "int (user's Cloudz balance after this tx)",
  "reference": "string (short label)",
  "description": "string (human-readable)",
  "createdAt": "ISO datetime string",
  "orderId": "string (optional, for purchase/referral_reward)",
  "referredUserId": "string (optional, only on referral_signup_bonus)",
  "creditAmount": "float (optional, only on credit_adjustment)",
  "newCreditBalance": "float (optional, only on credit_adjustment)",
  "isoYear": "int (optional, only on streak_bonus)",
  "isoWeek": "int (optional, only on streak_bonus)"
}
```

### 3.5 Balance Calculation

Balance is stored directly on `user.loyaltyPoints` and updated atomically via `$inc`. The `balanceAfter` field on each ledger entry is the snapshot at time of transaction. The user's current balance is the single source of truth from `users.loyaltyPoints`.

---

## 4. API ENDPOINTS (COMPLETE)

### 4.1 Auth

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/auth/check-username?username=x` | None | Check username availability. Returns `{ available: bool }` |
| `POST` | `/api/auth/register` | None | Register new user. See Section 1.1 |
| `POST` | `/api/auth/login` | None | Login. See Section 1.2 |
| `GET` | `/api/auth/me` | Bearer | Get current user profile. Returns `UserResponse` |

### 4.2 User Profile

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `PATCH` | `/api/profile` | Bearer | Update profile (firstName, lastName, email, phone, profilePhoto). Returns `UserResponse` |
| `PATCH` | `/api/me/username` | Bearer | Update username. Body: `{ username: string }`. Returns `UserResponse` |
| `GET` | `/api/me/referral-earnings` | Bearer | Get referral earnings. Returns `{ totalReferralCloudz, referralOrderCount }` |
| `GET` | `/api/me/cloudz-ledger` | Bearer | Get user's Cloudz ledger (max 500 entries, newest first). Returns `LedgerEntry[]` |
| `GET` | `/api/me/coupon` | Bearer | Get active next-order coupon. Returns `{ coupon: object|null }` |
| `POST` | `/api/push/register` | Bearer | Register Expo push token. Body: `{ token: string }` |
| `POST` | `/api/support/tickets` | Bearer | Create support ticket. Body: `{ subject, message }` |

### 4.3 Products & Brands

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/brands?active_only=bool` | None | List brands. Returns `Brand[]` with `productCount` |
| `POST` | `/api/brands` | Admin | Create brand |
| `PATCH` | `/api/brands/{id}` | Admin | Update brand |
| `DELETE` | `/api/brands/{id}` | Admin | Delete brand (fails if has products) |
| `GET` | `/api/products?category=&brand_id=&active_only=true&in_stock_only=false` | None | List products |
| `GET` | `/api/products/{id}` | None | Get single product |
| `POST` | `/api/products` | Admin | Create product |
| `PATCH` | `/api/products/{id}` | Admin | Update product |
| `DELETE` | `/api/products/{id}` | Admin | Delete product |
| `PATCH` | `/api/products/{id}/stock` | Admin | Adjust stock. Body: `{ adjustment: int, reason?: string }` |
| `POST` | `/api/upload/product-image` | Admin | Upload image file (max 5MB). Returns `{ url }` |
| `GET` | `/api/categories` | None | Returns `[{ name, value }]` static list |

### 4.4 Orders

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/orders` | Bearer | Create order. Body: `OrderCreate`. Returns `Order` |
| `GET` | `/api/orders` | Bearer | List user's orders (newest first) |
| `GET` | `/api/orders/{id}` | Bearer | Get single order (user must own it or be admin) |
| `POST` | `/api/orders/{id}/cancel` | Bearer | Cancel order (only if status is `Pending Payment`) |

**`OrderCreate` body:**
```json
{
  "items": [{ "productId": "...", "quantity": 1, "name": "...", "price": 12.99 }],
  "total": 12.99,
  "pickupTime": "Today 2-4 PM",
  "paymentMethod": "Cash on Pickup",
  "loyaltyPointsUsed": 0,
  "rewardId": null,
  "couponApplied": false,
  "storeCreditApplied": 0.0
}
```

**Order statuses:** `Pending Payment` → `Paid` → `Ready for Pickup` → `Completed` | `Cancelled` | `Awaiting Pickup (Cash)`

**Payment methods:** `Cash on Pickup`, `Zelle`, `CashApp`, `Venmo` (manual — no online processing)

**Order expiry:** Pending Payment orders expire after 30 minutes (background task).

### 4.5 Loyalty

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/loyalty/tiers` | Bearer | Get tiers with unlock status. Returns `{ userPoints, tiers[] }` |
| `POST` | `/api/loyalty/redeem` | Bearer | Redeem tier. Body: `{ tierId }`. Returns `{ rewardId, rewardAmount, ... }` |
| `GET` | `/api/loyalty/rewards` | Bearer | Get unused rewards. Returns `Reward[]` |
| `GET` | `/api/loyalty/history` | Bearer | Get all rewards (used + unused) |
| `GET` | `/api/loyalty/ledger` | Bearer | Get Cloudz ledger (max 200 entries) |
| `GET` | `/api/loyalty/streak` | Bearer | Get streak info. Returns `{ streak, currentBonus, nextBonus, daysUntilExpiry, ... }` |
| `GET` | `/api/leaderboard` | Bearer | Returns `{ byPoints[], byReferrals[] }` with rank, tier, movement |

### 4.6 Reviews

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/reviews/check/{productId}` | Bearer | Check if user can review. Returns `{ canReview, hasReviewed, orderId }` |
| `POST` | `/api/reviews` | Bearer | Create review. Body: `{ productId, orderId, rating(1-5), comment? }` |
| `GET` | `/api/reviews/product/{productId}` | None | Get visible reviews for product |

### 4.7 Chat (WebSocket)

| Protocol | Endpoint | Auth |
|---|---|---|
| `WS` | `/api/ws/chat/{chat_id}?token=jwt` | JWT in query param |
| `GET` | `/api/chat/messages/{chat_id}` | Bearer | Get chat history |

**WebSocket message types (send):**
- `{ type: "message", message: "text" }` — send chat message
- `{ type: "typing", isTyping: true/false }` — typing indicator
- `{ type: "read" }` — mark messages as read

**WebSocket message types (receive):**
- `{ type: "message", chatId, senderId, senderName, isAdmin, message, createdAt }`
- `{ type: "typing", senderId, senderName, isTyping }`
- `{ type: "read", readBy, readAt }`

**Chat ID convention:** `chat_{userId}` — one chat session per user.

### 4.8 Admin Endpoints

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/admin/users` | Admin | List all users |
| `PATCH` | `/api/admin/users/{id}` | Admin | Update user fields (name, email, phone, username, isAdmin, isDisabled, loyaltyPoints, creditBalance, profilePhoto) |
| `DELETE` | `/api/admin/users/{id}` | Admin | Delete user (cannot delete other admins) |
| `GET` | `/api/admin/users/{id}/profile` | Admin | Full user profile with orders, reviews, referrer info, totalSpent |
| `PATCH` | `/api/admin/users/{id}/referrer` | Admin | Assign/remove referrer. Body: `{ referrerIdentifier }`. Issues rewards if first-time |
| `GET` | `/api/admin/users/{id}/cloudz-ledger` | Admin | Get user's ledger (max 500) |
| `POST` | `/api/admin/users/{id}/cloudz-adjust` | Admin | Adjust Cloudz. Body: `{ amount: int, description: string }` |
| `POST` | `/api/admin/users/{id}/credit` | Admin | Adjust store credit. Body: `{ amount: float, description: string }` |
| `POST` | `/api/admin/users/{id}/set-password` | Admin | Set password. Body: `{ newPassword }` (min 8) |
| `POST` | `/api/admin/users/{id}/force-logout` | Admin | Force logout (invalidates tokens issued before now) |
| `PATCH` | `/api/admin/users/{id}/username` | Admin | Set username. Body: `{ username }` |
| `PATCH` | `/api/admin/users/{id}/notes` | Admin | Set admin notes. Body: `{ notes: string }` |
| `POST` | `/api/admin/users/merge` | Admin | Merge accounts. Body: `{ sourceUserId, targetUserId }` |
| `GET` | `/api/admin/orders` | Admin | List all orders with customer info |
| `PATCH` | `/api/admin/orders/{id}/status` | Admin | Update order status. Body: `{ status }`. Triggers rewards on Paid |
| `PATCH` | `/api/admin/orders/{id}/edit` | Admin | Edit order items/total/notes/pickupTime/paymentMethod |
| `GET` | `/api/admin/ledger?skip=0&limit=50&userId=&type=` | Admin | Global ledger with pagination + filters. Returns `{ entries[], total, skip, limit }` |
| `GET` | `/api/admin/reviews` | Admin | List all reviews with product names |
| `PATCH` | `/api/admin/reviews/{id}` | Admin | Moderate review (hide/edit comment) |
| `DELETE` | `/api/admin/reviews/{id}` | Admin | Delete review |
| `GET` | `/api/admin/chats` | Admin | List chat sessions with online status |
| `GET` | `/api/admin/support/tickets?skip=0&limit=50&status=` | Admin | List support tickets |
| `GET` | `/api/admin/analytics?startDate=&endDate=` | Admin | Analytics dashboard data |

### 4.9 Static Files

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/uploads/products/{filename}` | Serve uploaded product/brand images |
| `GET` | `/api/health` | Health check |

---

## 5. UI SCREENS

### 5.1 Age Gate (`age-gate.tsx`)
- Full-screen dark modal
- Single button: "I am 21+ Enter"
- Stores `cloudDistrictAgeVerified = "true"` in AsyncStorage/localStorage
- Shown on every app launch until verified
- No date-of-birth input (just a declaration)

### 5.2 Login (`auth/login.tsx`)
- Single `identifier` input (label: "Email or Username")
- Password input
- Sends `{ identifier, password }` to `POST /api/auth/login`
- Inline error display (no Alert.alert)
- Link to Register screen

### 5.3 Register (`auth/register.tsx`)
- Fields in order: First Name, Last Name, Email, Username (with debounced availability check), Phone, Date of Birth, Password, Confirm Password, Referral Code (optional), Avatar upload (optional)
- Username availability: debounced `GET /api/auth/check-username?username=x` (300ms delay)
- Shows green checkmark or red X inline
- Phone: auto-formatted as `(XXX) XXX-XXXX`, stored as digits only
- Avatar: uses `expo-image-picker`, converts to base64 data URI
- All validation inline (red text below fields), no Alert.alert
- Confirm password: client-side match check
- DOB: client-side 21+ check before submit, server also enforces

### 5.4 Home (`(tabs)/home.tsx`)
- Featured products carousel
- Shop by brand section (horizontal scroll)
- Cloudz points badge in header (tappable → navigates to Cloudz dashboard)
- "Order for Local Pickup" CTA

### 5.5 Shop (`(tabs)/shop.tsx`)
- Product grid/list
- Filter by category, brand
- Product cards with image, name, price, brand

### 5.6 Product Detail (`product/[id].tsx`)
- Product images, name, brand, price, puff count, nicotine %, flavor, description
- Add to cart button with quantity selector
- Reviews section
- "Write a Review" (if eligible)

### 5.7 Cart (`cart.tsx`)
- Line items with quantity controls
- Subtotal calculation
- Proceed to checkout button

### 5.8 Checkout (`checkout.tsx`)
- Pickup time selection
- Payment method selection (Cash on Pickup, Zelle, CashApp, Venmo)
- Apply store credit toggle
- Apply coupon toggle (next-order coupon)
- Apply tier reward (if available)
- Order summary with all discounts
- Place order button

### 5.9 Order Confirmation (`order-confirmation.tsx`)
- Order placed confirmation with order ID
- Payment instructions (for non-cash methods)

### 5.10 Payment Instructions (`payment-instructions.tsx`)
- Shows payment details for Zelle/CashApp/Venmo
- Timer for 30-minute payment window

### 5.11 Orders (`(tabs)/orders.tsx`)
- List of user's orders with status badges
- Tappable → order detail

### 5.12 Order Detail (`order-detail.tsx`)
- Full order info: items, total, status, pickup time, payment method
- Cancel button (only for Pending Payment)

### 5.13 Account (`(tabs)/account.tsx`)
- User info display (name, email, username, phone)
- Cloudz balance
- Loyalty tier display
- Referral code display + share
- Navigation to: Profile edit, Cloudz dashboard, Cloudz history, Leaderboard, Support
- Logout button
- Admin panel link (if isAdmin)

### 5.14 Profile (`profile.tsx`)
- Edit first name, last name, email, phone
- Calls `PATCH /api/profile`

### 5.15 Cloudz Dashboard (`cloudz.tsx`)
- Large Cloudz balance display
- Current tier + progress to next
- Streak info
- Ways to Earn section (static cards)
- Recent Activity (last 5 ledger entries with formatted labels)
- "View All History" link → cloudz-history
- Tier redemption cards

### 5.16 Cloudz History (`cloudz-history.tsx`)
- Full ledger list (max 200 entries)
- Fintech-style cards: icon circle, formatted label, description, timestamp, colored amount, balance after
- Color coding: green (rewards), red (redemptions), orange (admin)
- Fade-in animation per row

### 5.17 Leaderboard (`leaderboard.tsx`)
- Two tabs: By Points, By Referrals
- Rank, display name, points, tier badge, tier color
- Rank movement indicator (up/down from yesterday)
- Current user highlighted

### 5.18 Support (`support.tsx`)
- Create support ticket form (subject, message)
- Calls `POST /api/support/tickets`

### 5.19 Admin Layout (`admin/_layout.tsx`)
- Bottom tab navigation: Dashboard, Orders, Products, Brands, Users, Ledger, Chats, Reviews

### 5.20 Admin Dashboard (`admin/dashboard.tsx`)
- Analytics: total orders, revenue, avg order value, top products, top customers
- Revenue trend chart (7 days)
- Low inventory alerts
- Revenue by payment method

### 5.21 Admin Orders (`admin/orders.tsx`)
- All orders list with status filters
- Status update dropdown
- Order editing (items, total, notes, pickup time, payment method)

### 5.22 Admin Products (`admin/products.tsx`)
- Product CRUD: create, edit, delete
- Image upload
- Stock management

### 5.23 Admin Brands (`admin/brands.tsx`)
- Brand CRUD: create, edit, delete
- Brand image upload

### 5.24 Admin Users (`admin/users.tsx`)
- User list with search
- Quick actions: disable, make admin
- Tap → user profile

### 5.25 Admin User Profile (`admin/user-profile.tsx`)
- Full user view: info, orders, reviews, ledger
- Edit user fields
- Assign/change referrer
- Adjust Cloudz balance
- Adjust store credit
- Set password
- Force logout
- Admin notes
- Account merge

### 5.26 Admin Cloudz Ledger (`admin/cloudz-ledger.tsx`)
- Global ledger with pagination (50 per page)
- Filter by ledger type (horizontal scrollable chips)
- Filter by user ID
- Fintech card design: user email, formatted label, colored amount, balance, timestamp

### 5.27 Admin Chats (`admin/chats.tsx`)
- Chat session list with online indicators
- Real-time WebSocket chat with customers

### 5.28 Admin Reviews (`admin/reviews.tsx`)
- All reviews with moderation (hide/delete)

---

## 6. VALIDATION RULES

### 6.1 Username
- Regex: `^[a-zA-Z0-9_]{3,20}$`
- Auto-normalized: lowercased, trimmed, spaces removed
- Reserved words blocked: `admin`, `support`, `api`, `clouddistrict`, `orders`, `root`, `help`
- Unique (case-insensitive)
- Checked in real-time via `GET /api/auth/check-username` with 300ms debounce

### 6.2 Password
- Minimum 8 characters, maximum 128
- No additional complexity rules enforced server-side
- Frontend enforces confirm password match

### 6.3 Phone
- Frontend: auto-formats as `(XXX) XXX-XXXX`
- Stored as raw input (frontend sends formatted, backend stores as-is)
- Max 20 characters
- Optional field

### 6.4 Email
- Pydantic `EmailStr` validation
- Must be unique in database

### 6.5 Date of Birth
- Format: `YYYY-MM-DD` (validated server-side)
- Must be 21+ years old (calculated as `days / 365.25`)

### 6.6 Referral Code
- Optional at registration
- Must match an existing user's username (case-insensitive)
- Self-referral silently nullified (not an error)

---

## 7. SPECIAL LOGIC & NON-OBVIOUS BEHAVIORS

### 7.1 Debounced Username Check
- Frontend sends `GET /api/auth/check-username?username=x` with 300ms debounce
- Backend checks both regex validity AND uniqueness
- Returns `{ available: false }` for reserved words or existing users

### 7.2 Inline Error Handling
- `Alert.alert()` does NOT work on React Native Web
- All form errors are shown as inline red text below the relevant field or above the submit button
- Error state managed with `useState` in each form component

### 7.3 Auth Store (Zustand)
- Token stored in `localStorage` (web) or `AsyncStorage` (native) under key `cloud-district-token`
- On app load: `loadToken()` reads stored token, calls `GET /api/auth/me` to validate
- If token invalid/expired: clears storage, sets unauthenticated
- Login sends `{ identifier, password }` (not `{ email, password }`)

### 7.4 referredBy Storage Inconsistency
- Registration stores `referredBy` as the referrer's **username** string
- Admin assign referrer stores `referredBy` as the referrer's **ObjectId** string
- Order referral reward handler accounts for both: tries `ObjectId` lookup first, then `username` lookup

### 7.5 Order Expiry
- Background task runs every 60 seconds
- Orders with status `Pending Payment` and `expiresAt < now` are auto-cancelled
- Stock is restored on cancellation

### 7.6 Leaderboard Snapshots
- Background task runs daily at midnight UTC
- Saves current rankings to `leaderboard_snapshots` collection
- Used to calculate rank movement (up/down arrows on leaderboard)

### 7.7 Next-Order Coupon
- When order is marked `Paid`, a $5.00 coupon is created on the user (`nextOrderCoupon`)
- Expires in 7 days
- Can be applied at checkout (`couponApplied: true`)
- Marked as used after application

### 7.8 Store Credit
- Separate from Cloudz points
- Stored as `creditBalance` (float) on user document
- Admin can add/deduct via `POST /api/admin/users/{id}/credit`
- User can apply at checkout (`storeCreditApplied: float`)
- Restored on order cancellation

### 7.9 Product Image Handling
- Images can be uploaded as files (`POST /api/upload/product-image`) or as base64 data URIs
- Base64 images in product/brand documents are auto-migrated to files on server startup
- Files stored in `UPLOADS_DIR` and served at `/api/uploads/products/{filename}`
- Allowed types: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` (max 5MB)

### 7.10 Rate Limiting
- Registration: 5/minute
- Login: 10/minute
- Order creation: 5/minute (per user or IP)
- Review creation: 5/hour (per user or IP)
- Library: `slowapi`

### 7.11 Email Service
- **Currently MOCKED** — `is_email_configured()` returns false unless SMTP env vars are set
- Order confirmation emails built but not sent in current deployment
- Email function is non-blocking (failure doesn't affect order creation)

### 7.12 Push Notifications
- Expo push tokens registered via `POST /api/push/register`
- Notifications sent on order status changes
- Web platform: registration silently skipped

### 7.13 Account Merge
- Admin can merge two accounts: `POST /api/admin/users/merge`
- Source user's orders and ledger entries are reassigned to target
- Source user's credit and points are transferred
- Source user is disabled with `mergedInto` reference

### 7.14 Frontend Ledger Label Formatting
Located in `constants/ledger.ts`:
- `formatLedgerType(type)` — maps raw type to display label
- `getLedgerIcon(type)` — returns Ionicons icon name
- `getLedgerColor(type, amount?)` — returns hex color string
- Fallback for unknown types: replace underscores with spaces, capitalize each word

### 7.15 MongoDB Collections Used
- `users` — user accounts
- `products` — product catalog
- `brands` — brand catalog
- `orders` — order records
- `cloudz_ledger` — all Cloudz point transactions
- `loyalty_rewards` — tier redemption rewards
- `reviews` — product reviews
- `chat_messages` — WebSocket chat messages
- `chat_sessions` — chat session metadata
- `push_tokens` — Expo push notification tokens
- `support_tickets` — support ticket submissions
- `inventory_logs` — stock adjustment history
- `leaderboard_snapshots` — daily ranking snapshots

---

## 8. USER DOCUMENT SCHEMA (MongoDB)

```json
{
  "_id": "ObjectId",
  "email": "string (unique)",
  "password": "string (bcrypt hash)",
  "firstName": "string",
  "lastName": "string",
  "dateOfBirth": "string (YYYY-MM-DD)",
  "phone": "string | null",
  "isAdmin": "bool",
  "isDisabled": "bool (default false)",
  "loyaltyPoints": "int",
  "creditBalance": "float (default 0.0)",
  "profilePhoto": "string | null (base64 data URI)",
  "username": "string (unique, lowercase)",
  "referralCode": "string (= username)",
  "referredBy": "string | null (referrer username or ObjectId string)",
  "referralCount": "int",
  "referralRewardsEarned": "int",
  "referralRewardIssued": "bool",
  "adminNotes": "string | null",
  "forceLogoutAt": "float | null (unix timestamp)",
  "mergedInto": "string | null (ObjectId string)",
  "nextOrderCoupon": "object | null { amount, expiresAt, orderId, used, issuedAt }",
  "createdAt": "datetime"
}
```
