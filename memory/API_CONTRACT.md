```
Cloud District Club API
Version: v1.0
Status: Frozen API Contract
Date: 2026-03-10

Rules:
* This document represents the authoritative backend API contract.
* No breaking changes are permitted without incrementing the API version.
* All future clients (mobile, web, admin) must follow this specification exactly.
```

# Cloud District Club — API Contract
**Version:** 1.0  
**Frozen from:** `/app/openapi.json` + source validation (iteration_32, 107/112 tests passing)  
**Base URL:** `https://<host>/api`  
**OpenAPI version:** 3.1.0  

> This document is the authoritative reference for the upcoming web frontend project.  
> Do not implement against anything not listed here.

---

## Table of Contents
1. [Global Rules](#1-global-rules)
2. [Authentication](#2-authentication)
3. [Error Codes](#3-error-codes)
4. [Rate Limits](#4-rate-limits)
5. [Schemas](#5-schemas)
6. [Auth Endpoints](#6-auth-endpoints)
7. [Users & Profile Endpoints](#7-users--profile-endpoints)
8. [Products Endpoints](#8-products-endpoints)
9. [Orders Endpoints](#9-orders-endpoints)
10. [Loyalty Endpoints](#10-loyalty-endpoints)
11. [Leaderboard Endpoint](#11-leaderboard-endpoint)
12. [Admin Endpoints](#12-admin-endpoints)
13. [Support & Push Endpoints](#13-support--push-endpoints)
14. [Business Logic Reference](#14-business-logic-reference)

---

## 1. Global Rules

### Request Headers
Every request to a protected endpoint must include:
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

For file upload endpoints use `multipart/form-data` instead of `application/json`.

### Response Format
All responses are `application/json`. Successful responses return the schema defined per endpoint.  
All error responses follow:
```json
{ "detail": "<human-readable message>" }
```
Validation errors (422) return:
```json
{
  "detail": [
    { "loc": ["body", "fieldName"], "msg": "...", "type": "..." }
  ]
}
```

### ID Format
All IDs are MongoDB ObjectId strings (24-character hex). Example: `"698f8be2f3e9a3d6ac40fb67"`.

---

## 2. Authentication

### Scheme
`HTTPBearer` — JWT token in `Authorization: Bearer <token>` header.

### Token Lifecycle
- Tokens are issued on `POST /api/auth/register` and `POST /api/auth/login`.
- Token lifetime: **7 days**.
- Token is invalidated server-side by the admin `force-logout` action. A token issued before the `forceLogoutAt` timestamp will be rejected even if not expired.

### Auth Status Codes
| Condition | Status | Detail |
|---|---|---|
| No `Authorization` header | `401` | `"Not authenticated"` |
| Malformed or invalid JWT signature | `401` | `"Invalid authentication credentials"` |
| JWT is expired | `401` | `"Token expired"` |
| Account is disabled | `401` | `"Account has been disabled"` |
| Session force-invalidated | `401` | `"Session has been invalidated"` |
| Authenticated but not admin | `403` | `"Admin access required"` |

### Public Endpoints (no token required)
```
GET  /api/health
GET  /api/products
GET  /api/products/{product_id}
GET  /api/brands
GET  /api/categories
GET  /api/reviews/product/{product_id}
POST /api/auth/register
POST /api/auth/login
```

### Admin-Only Endpoints
All endpoints under `/api/admin/*` require `user.isAdmin === true`.  
`PATCH /api/products/*`, `POST /api/products`, `DELETE /api/products/*`, `PATCH /api/brands/*`, `POST /api/brands`, `DELETE /api/brands/*`, and `POST /api/upload/product-image` also require admin.  
Non-admin callers with a valid token receive `403 "Admin access required"`.

---

## 3. Error Codes

| Status | When |
|---|---|
| `400` | Business rule violation (duplicate username, invalid referral code, oversell attempt, etc.) |
| `401` | Authentication failure — see table above |
| `403` | Authenticated but insufficient permissions (non-admin on admin route; accessing another user's order) |
| `404` | Resource not found |
| `409` | Conflict — resource already exists (duplicate email on register) |
| `422` | Request schema validation failure (missing required field, wrong type, value out of range) |
| `429` | Rate limit exceeded |

---

## 4. Rate Limits

Rate limiting is enforced by `slowapi`. Exceeded requests return `429` with a `Retry-After` header.

| Endpoint | Limit | Key |
|---|---|---|
| `POST /api/auth/register` | 5 / minute | IP address |
| `POST /api/auth/login` | 10 / minute | IP address |
| `POST /api/orders` | 5 / minute | User ID (falls back to IP) |
| `POST /api/reviews` | 5 / hour | User ID (falls back to IP) |

---

## 5. Schemas

### UserResponse
Returned by login, register, `GET /api/auth/me`, and profile updates.
```typescript
{
  id:                   string          // MongoDB ObjectId
  email:                string
  firstName:            string
  lastName:             string
  dateOfBirth:          string          // "YYYY-MM-DD"
  isAdmin:              boolean
  loyaltyPoints:        number          // Cloudz balance
  phone:                string | null
  profilePhoto:         string | null   // URL or base64
  referralCode:         string | null   // auto-generated, immutable by user
  referralCount:        number          // default 0
  referralRewardsEarned: number         // default 0
  username:             string | null
  referredByUserId:     string | null   // ObjectId of referrer
  creditBalance:        number          // store credit, default 0.0
  isDisabled:           boolean         // default false
}
```

### Token
Returned by register and login.
```typescript
{
  access_token: string
  token_type:   "bearer"
  user:         UserResponse
}
```

### Product
```typescript
{
  id:               string | null
  name:             string
  brandId:          string
  brandName:        string
  model:            string | null
  category:         string
  image:            string              // primary image URL
  images:           string[]            // additional images, default []
  puffCount:        number
  flavor:           string
  nicotinePercent:  number              // default 5.0
  nicotineStrength: string | null
  deviceType:       string | null
  slug:             string | null
  price:            number
  stock:            number
  lowStockThreshold: number             // default 5
  description:      string | null
  isActive:         boolean             // default true
  isFeatured:       boolean             // default false
  loyaltyEarnRate:  number | null
  cloudzReward:     number | null
  displayOrder:     number              // default 0
}
```

### Brand
```typescript
{
  id:           string | null
  name:         string
  image:        string | null
  isActive:     boolean        // default true
  displayOrder: number         // default 0
  productCount: number         // default 0
}
```

### CartItem
Used inside OrderCreate and Order.
```typescript
{
  productId: string    // min length 1
  quantity:  number    // integer, 1–100
  name:      string    // max 200 chars
  price:     number    // >= 0
}
```

### OrderCreate (request)
```typescript
{
  items:               CartItem[]   // min 1 item — REQUIRED
  total:               number       // >= 0 — REQUIRED
  pickupTime:          string       // 1–100 chars — REQUIRED
  paymentMethod:       string       // 1–50 chars — REQUIRED
  loyaltyPointsUsed:   number       // integer >= 0, default 0
  rewardId:            string | null // active reward ObjectId
  couponApplied:       boolean       // default false
  storeCreditApplied:  number        // >= 0, default 0.0 — capped at user's creditBalance
}
```

### Order (response)
```typescript
{
  id:                  string | null
  userId:              string
  items:               CartItem[]
  total:               number        // after all discounts
  pickupTime:          string
  paymentMethod:       string
  status:              OrderStatus   // see below
  loyaltyPointsEarned: number        // default 0
  loyaltyPointsUsed:   number        // default 0
  createdAt:           string        // ISO 8601
  expiresAt:           string | null // ISO 8601; set 30 min after creation for "Pending Payment" orders
  customerName:        string | null
  customerEmail:       string | null
  adminNotes:          string | null
  storeCreditApplied:  number        // default 0.0
  rewardDiscount:      number        // reward dollar discount applied
  couponDiscount:      number        // next-order coupon discount applied
}
```

### OrderStatus values
```
"Pending Payment"   — initial status; expires after 30 minutes if unpaid
"Paid"              — triggers Cloudz earn + referral reward
"Ready for Pickup"
"Completed"
"Cancelled"         — stock and store credit are restored
"Expired"           — auto-set by background job after 30-minute window
```

### ReviewCreate (request)
```typescript
{
  productId: string   // min 1
  orderId:   string   // min 1 — must be a Paid order belonging to the caller
  rating:    number   // integer 1–5
  comment:   string | null  // max 1000 chars
}
```

### ReviewResponse
```typescript
{
  id:        string
  productId: string
  userId:    string
  orderId:   string
  rating:    number
  comment:   string | null
  createdAt: string
  userName:  string
  isHidden:  boolean   // default false
}
```

### LoyaltyTier
```typescript
{
  id:             string   // "tier_1" … "tier_5"
  name:           string
  pointsRequired: number
  reward:         number   // dollar value of reward
  icon:           string   // Ionicons name
  color:          string   // hex color
}
```

### LeaderboardEntry
```typescript
{
  rank:          number
  displayName:   string       // "First L." format
  points:        number
  referralCount: number
  tier:          string | null
  tierColor:     string
  isCurrentUser: boolean
  movement:      number | null  // null = no prior snapshot; +N = moved up N; -N = moved down N
}
```

---

## 6. Auth Endpoints

### `POST /api/auth/register`
**Auth:** Public  
**Rate limit:** 5/min per IP

**Request body:** `UserRegister`
```typescript
{
  email:        string   // valid email — REQUIRED
  password:     string   // 8–128 chars — REQUIRED
  firstName:    string   // 1–50 chars — REQUIRED
  lastName:     string   // 1–50 chars — REQUIRED
  dateOfBirth:  string   // "YYYY-MM-DD", exactly 10 chars — REQUIRED; must be 21+ years ago
  phone:        string | null  // max 20 chars
  referralCode: string | null  // another user's referralCode or username, max 50 chars
}
```

**Response 200:** `Token`

**Side effects on success:**
- New user receives **+500 Cloudz** signup bonus (logged as `signup_bonus`)
- If valid `referralCode` provided: referrer receives **+500 Cloudz** (logged as `referral_signup_bonus`) and their `referralCount` increments by 1

**Errors:**
| Status | Condition |
|---|---|
| `409` | Email already registered |
| `400` | User is under 21 years old |
| `400` | Invalid referral code (not found by referralCode or username) |
| `422` | Any required field missing or schema violation |

---

### `POST /api/auth/login`
**Auth:** Public  
**Rate limit:** 10/min per IP

**Request body:** `UserLogin`
```typescript
{
  email:    string   // REQUIRED
  password: string   // REQUIRED
}
```

**Response 200:** `Token`

**Errors:**
| Status | Condition |
|---|---|
| `401` | Email not found or wrong password |
| `403` | Account is disabled |
| `422` | Missing fields |

---

### `GET /api/auth/me`
**Auth:** JWT required

**Response 200:** `UserResponse`

---

## 7. Users & Profile Endpoints

### `PATCH /api/profile`
**Auth:** JWT required

**Request body:** `UserProfileUpdate` (all fields optional)
```typescript
{
  firstName:    string | null
  lastName:     string | null
  email:        string | null   // valid email format
  phone:        string | null
  profilePhoto: string | null   // URL or base64
}
```

**Response 200:** `UserResponse`

---

### `PATCH /api/me/username`
**Auth:** JWT required

**Request body:**
```typescript
{ username: string }
```

**Validation rules:**
- Pattern: `^[a-zA-Z0-9_]{3,20}$` (3–20 chars, alphanumeric + underscore)
- Reserved words (case-insensitive): `admin`, `support`, `api`, `clouddistrict`, `orders`, `root`, `help`
- Must be globally unique

**Response 200:** `UserResponse`

**Errors:**
| Status | Condition |
|---|---|
| `400` | Pattern violation, reserved word, or already taken |

---

### `GET /api/me/referral-earnings`
**Auth:** JWT required

**Response 200:**
```typescript
{
  totalReferralCloudz: number   // lifetime Cloudz earned from referrals
  referralOrderCount:  number   // count of referred users who placed a Paid order
}
```

---

### `GET /api/me/cloudz-ledger`
**Auth:** JWT required

**Response 200:** Array of ledger entries
```typescript
[{
  type:         string    // e.g. "signup_bonus", "purchase_reward", "referral_signup_bonus", "streak_bonus", "redemption", "admin_adjustment"
  amount:       number    // positive = credit, negative = debit
  balanceAfter: number
  description:  string
  createdAt:    string    // ISO 8601
}]
```

---

### `GET /api/me/coupon`
**Auth:** JWT required

**Response 200:**
```typescript
{
  coupon: {
    amount:    number   // dollar value of the coupon
    expiresAt: string   // ISO 8601
    used:      boolean
  } | null
}
```
Returns `{ coupon: null }` if no active coupon, or if coupon is expired/used.

---

### `POST /api/push/register`
**Auth:** JWT required

**Request body:**
```typescript
{ token: string }  // Expo push notification token
```
Token must match the Expo token format (starts with `ExponentPushToken[`). Accepts any non-empty string — validation is lenient.

**Response 200:** `{ "message": "Push token registered" }`

**Errors:**
| Status | Condition |
|---|---|
| `400` | Empty or invalid token format |

---

## 8. Products Endpoints

### `GET /api/products`
**Auth:** Public

**Query parameters:**
```
category       string   optional  filter by category name
brand_id       string   optional  filter by brand ObjectId
active_only    boolean  default=true
in_stock_only  boolean  default=false
```

**Response 200:** `Product[]`

---

### `GET /api/products/{product_id}`
**Auth:** Public

**Response 200:** `Product`

**Errors:**
| Status | Condition |
|---|---|
| `404` | Product not found |

---

### `POST /api/products`
**Auth:** Admin JWT required

**Request body:** `ProductCreate`
```typescript
{
  name:             string   // 1–200 chars — REQUIRED
  brandId:          string   // min 1 — REQUIRED
  category:         string   // 1–100 chars — REQUIRED
  image:            string   // URL or path, min 1 — REQUIRED
  images:           string[] | null   // default []
  puffCount:        number   // integer > 0, max 100,000 — REQUIRED
  flavor:           string   // 1–100 chars — REQUIRED
  nicotinePercent:  number   // 0–20 — REQUIRED
  price:            number   // > 0, max 10,000 — REQUIRED
  stock:            number   // integer >= 0 — REQUIRED
  lowStockThreshold: number  // integer >= 0, default 5
  description:      string | null  // max 2,000 chars
  isActive:         boolean  // default true
  isFeatured:       boolean  // default false
  loyaltyEarnRate:  number | null   // >= 0
  displayOrder:     number   // integer >= 0, default 0
}
```

**Response 200:** `Product`

---

### `PATCH /api/products/{product_id}`
**Auth:** Admin JWT required

**Request body:** `ProductUpdate` — all fields optional, same constraints as `ProductCreate`

**Response 200:** `Product`

---

### `DELETE /api/products/{product_id}`
**Auth:** Admin JWT required

**Response 200:** `{ "message": "Product deleted" }`

**Errors:**
| Status | Condition |
|---|---|
| `404` | Product not found |

---

### `PATCH /api/products/{product_id}/stock`
**Auth:** Admin JWT required

**Request body:** `StockAdjustment`
```typescript
{
  adjustment: number   // integer, positive or negative — REQUIRED
  reason:     string | null
}
```

**Response 200:**
```typescript
{ "newStock": number, "productId": string }
```

---

### `POST /api/upload/product-image`
**Auth:** Admin JWT required  
**Content-Type:** `multipart/form-data`

**Request body:**
```
file: binary   // image file — REQUIRED
```

**Response 200:**
```typescript
{ "imageUrl": string }   // relative URL e.g. "/uploads/products/<filename>"
```

---

### `GET /api/brands`
**Auth:** Public

**Query parameters:**
```
active_only  boolean  default=false
```

**Response 200:** `Brand[]`

---

### `POST /api/brands`
**Auth:** Admin JWT required

**Request body:** `BrandCreate`
```typescript
{
  name:         string   // REQUIRED
  image:        string | null
  isActive:     boolean  // default true
  displayOrder: number   // default 0
}
```

**Response 200:** `Brand`

---

### `PATCH /api/brands/{brand_id}`
**Auth:** Admin JWT required

**Request body:** `BrandUpdate` — all fields optional

**Response 200:** `Brand`

---

### `DELETE /api/brands/{brand_id}`
**Auth:** Admin JWT required

**Response 200:** `{ "message": "Brand deleted" }`

---

### `GET /api/categories`
**Auth:** Public

**Response 200:** `string[]` — list of unique category names from active products

---

### `GET /api/reviews/product/{product_id}`
**Auth:** Public

**Response 200:** `ReviewResponse[]` — hidden reviews are excluded for public callers

---

### `POST /api/reviews`
**Auth:** JWT required  
**Rate limit:** 5/hour per user

**Request body:** `ReviewCreate`

**Requirements:**
- `orderId` must belong to the caller
- The order must have status `Paid`, `Ready for Pickup`, or `Completed`
- Caller must not have already reviewed this product via the same order

**Response 200:** `ReviewResponse`

**Errors:**
| Status | Condition |
|---|---|
| `400` | Already reviewed / no qualifying purchase / order does not belong to caller |

---

### `GET /api/reviews/check/{product_id}`
**Auth:** JWT required

**Response 200:**
```typescript
{
  canReview:   boolean
  hasReviewed: boolean
  orderId:     string | null   // qualifying order ID if canReview = true
}
```

---

## 9. Orders Endpoints

### `POST /api/orders`
**Auth:** JWT required  
**Rate limit:** 5/min per user

**Request body:** `OrderCreate`

**Side effects on success:**
- Stock is atomically decremented for each item
- If `storeCreditApplied > 0`: the lower of `storeCreditApplied` and `user.creditBalance` is deducted from `user.creditBalance`
- If `rewardId` provided: the active reward is consumed
- If `couponApplied = true`: the user's `nextOrderCoupon` is consumed if valid and unexpired
- Order gets `status = "Pending Payment"` and `expiresAt = createdAt + 30 minutes`

**Cloudz earn:** `floor(total) * 3` points — awarded when order status transitions to `Paid` (not at creation)

**Response 200:** `Order`

**Errors:**
| Status | Condition |
|---|---|
| `404` | One or more products not found |
| `409` | Insufficient stock for one or more items (atomic check) |
| `400` | `storeCreditApplied` exceeds current `creditBalance` (server clamps silently — see note) |
| `422` | Schema validation failure |

> **Note:** The server clamps `storeCreditApplied` to `min(requested, creditBalance, total)` rather than returning an error. The clamped value is stored in the order.

---

### `GET /api/orders`
**Auth:** JWT required

**Response 200:** `Order[]` — only the caller's own orders, newest first

---

### `GET /api/orders/{order_id}`
**Auth:** JWT required

**Response 200:** `Order`

**Errors:**
| Status | Condition |
|---|---|
| `404` | Order not found |
| `403` | Order belongs to a different user |

---

### `POST /api/orders/{order_id}/cancel`
**Auth:** JWT required

**No request body.**

**Cancellable statuses:** `"Pending Payment"` only (user-initiated). Admin can cancel any non-final status.

**Side effects on cancel:**
- All item quantities are restored to product stock
- `storeCreditApplied` is returned to `user.creditBalance`
- Order status set to `"Cancelled"`

**Response 200:** `{ "message": "Order cancelled" }`

**Errors:**
| Status | Condition |
|---|---|
| `400` | Order is already cancelled, completed, or expired |
| `403` | Order belongs to a different user |
| `404` | Order not found |

---

## 10. Loyalty Endpoints

### `GET /api/loyalty/tiers`
**Auth:** JWT required

**Response 200:**
```typescript
{
  tiers: LoyaltyTier[]
  userPoints: number   // caller's current Cloudz balance
}
```

**Tier definitions (frozen):**
| ID | Name | Points Required | Reward Value | Color |
|---|---|---|---|---|
| `tier_1` | Bronze Cloud | 1,000 | $5.00 | `#CD7F32` |
| `tier_2` | Silver Storm | 5,000 | $30.00 | `#C0C0C0` |
| `tier_3` | Gold Thunder | 10,000 | $75.00 | `#FFD700` |
| `tier_4` | Platinum Haze | 20,000 | $175.00 | `#A8B8D0` |
| `tier_5` | Diamond Sky | 30,000 | $300.00 | `#B9F2FF` |

---

### `POST /api/loyalty/redeem`
**Auth:** JWT required

**Request body:** `TierRedeemRequest`
```typescript
{ tierId: string }   // e.g. "tier_1"
```

**Requirements:**
- Caller must have `loyaltyPoints >= tier.pointsRequired`
- Caller must not already have an active (unused) reward for the same tier

**Response 200:**
```typescript
{
  rewardId:     string   // ObjectId to pass as `rewardId` in OrderCreate
  rewardAmount: number   // dollar value
  message:      string
}
```

**Side effects:** Points are deducted immediately on redemption, not at order placement.

**Errors:**
| Status | Condition |
|---|---|
| `400` | Insufficient points |
| `400` | Reward for this tier already active (not yet used) |
| `404` | Unknown tierId |

---

### `GET /api/loyalty/rewards`
**Auth:** JWT required

**Response 200:** Array of active (unused) rewards
```typescript
[{
  id:           string
  tierId:       string
  rewardAmount: number
  createdAt:    string
  isUsed:       boolean
}]
```

---

### `GET /api/loyalty/history`
**Auth:** JWT required

**Response 200:** Array of redemption history records (includes used and unused)

---

### `GET /api/loyalty/ledger`
**Auth:** JWT required

**Response 200:** Array of Cloudz ledger entries (same shape as `GET /api/me/cloudz-ledger`)

---

### `GET /api/loyalty/streak`
**Auth:** JWT required

**Response 200:**
```typescript
{
  streak:      number   // consecutive ISO weeks with at least one order
  currentBonus: number  // Cloudz bonus for this week's streak level (0 if streak < 2)
  nextBonus:   number   // Cloudz bonus if streak continues next week
}
```

**Streak bonus table:**
| Streak (weeks) | Bonus (Cloudz) |
|---|---|
| < 2 | 0 |
| 2 | 50 |
| 3 | 100 |
| 4 | 200 |
| 5+ | 500 |

Streak bonus is awarded **once per ISO week** on the first order marked `Paid` that week.

---

## 11. Leaderboard Endpoint

### `GET /api/leaderboard`
**Auth:** JWT required

**Response 200:**
```typescript
{
  byPoints: LeaderboardEntry[]      // top 20 by loyaltyPoints
  byReferrals: LeaderboardEntry[]   // top 20 by referralCount
}
```

**`movement` field behavior:**
- `null` — no snapshot exists for yesterday (first day of operation, or gap in snapshots)
- `0` — same rank as yesterday
- `+N` — moved up N positions since yesterday
- `-N` — moved down N positions since yesterday

Snapshots are taken once per day at midnight UTC by a background job. Movement is calculated by comparing today's rank to yesterday's snapshot.

---

## 12. Admin Endpoints

> All endpoints in this section require a valid JWT for a user with `isAdmin = true`.  
> Non-admin callers receive `403 "Admin access required"`.

---

### `GET /api/admin/users`
**Response 200:** `UserResponse[]` — all users

---

### `GET /api/admin/users/{user_id}/profile`
**Response 200:**
```typescript
{
  user:       UserResponse
  orders:     Order[]
  totalSpent: number
  reviews:    ReviewResponse[]
}
```

---

### `PATCH /api/admin/users/{user_id}`
**Request body:** `AdminUserUpdate` — all fields optional
```typescript
{
  firstName:    string | null
  lastName:     string | null
  email:        string | null   // valid email
  phone:        string | null
  username:     string | null
  isAdmin:      boolean | null
  isDisabled:   boolean | null
  loyaltyPoints: number | null  // setting this creates a cloudz_ledger entry
  creditBalance: number | null
  profilePhoto:  string | null
}
```

**Response 200:** Updated `UserResponse`

---

### `POST /api/admin/users/{user_id}/cloudz-adjust`
**Request body:** `CloudzAdjust`
```typescript
{
  amount:      number   // integer, positive or negative — REQUIRED
  description: string   // REQUIRED
}
```

**Response 200:**
```typescript
{ "message": "Balance updated", "newBalance": number }
```
Creates a `cloudz_ledger` entry of type `admin_adjustment`.

---

### `GET /api/admin/users/{user_id}/cloudz-ledger`
**Response 200:** `cloudz_ledger` entries for the specified user (same shape as `GET /api/me/cloudz-ledger`)

---

### `POST /api/admin/users/{user_id}/credit`
**Request body:** `CreditAdjust`
```typescript
{
  amount:      number   // float, positive = add, negative = deduct — REQUIRED
  description: string   // REQUIRED
}
```

**Response 200:**
```typescript
{ "newCreditBalance": number, "adjustment": number }
```

---

### `POST /api/admin/users/{user_id}/force-logout`
**No request body.**

**Response 200:** `{ "success": true }`

Sets a `forceLogoutAt` timestamp on the user. Any token issued before this timestamp is rejected with `401 "Session has been invalidated"`.

---

### `POST /api/admin/users/{user_id}/set-password`
**Request body:** `AdminSetPassword`
```typescript
{ newPassword: string }   // min 8 chars — REQUIRED
```

**Response 200:** `{ "message": "Password updated" }`

**Errors:**
| Status | Condition |
|---|---|
| `400` | Password shorter than 8 characters |
| `404` | User not found |

---

### `PATCH /api/admin/users/{user_id}/notes`
**Request body:** `AdminUserNotes`
```typescript
{ notes: string }   // REQUIRED
```

**Response 200:** `{ "message": "Notes updated" }`

---

### `PATCH /api/admin/users/{user_id}/referrer`
**Request body:** `AdminReferrerUpdate`
```typescript
{ referrerIdentifier: string | null }   // referralCode or username of the new referrer; null to clear
```

**Response 200:** `{ "message": "Referrer updated", "warning": string | null }`

> **Warning** field is non-null when the user already has paid orders — referral earnings are not retroactive.

**Errors:**
| Status | Condition |
|---|---|
| `400` | Cannot set user as their own referrer |
| `404` | Referrer identifier not found |

---

### `PATCH /api/admin/users/{user_id}/username`
**Request body:**
```typescript
{ username: string }
```
Same pattern rules as `PATCH /api/me/username` (`^[a-zA-Z0-9_]{3,20}$`), but bypasses the reserved-word check.

**Response 200:** `{ "message": "Username updated" }`

**Errors:**
| Status | Condition |
|---|---|
| `400` | Pattern violation or username already taken |
| `404` | User not found |

---

### `POST /api/admin/users/merge`
**Request body:** `MergeRequest`
```typescript
{
  sourceUserId: string   // account to be deactivated — REQUIRED
  targetUserId: string   // account to receive merged data — REQUIRED
}
```

**Merge behavior:**
- Source's `loyaltyPoints` and `creditBalance` are added to target
- Source is disabled and flagged with `mergedInto: targetUserId`
- Source points and credit are zeroed out

**Response 200:** `{ "success": true, "message": "Accounts merged successfully" }`

**Errors:**
| Status | Condition |
|---|---|
| `400` | `sourceUserId === targetUserId` |
| `404` | One or both users not found |

---

### `DELETE /api/admin/users/{user_id}`
**Response 200:** `{ "message": "User deleted" }`

**Errors:**
| Status | Condition |
|---|---|
| `404` | User not found |

---

### `GET /api/admin/orders`
**Response 200:** `Order[]` — all orders across all users, newest first

---

### `PATCH /api/admin/orders/{order_id}/status`
**Request body:** `OrderStatusUpdate`
```typescript
{ status: string }   // REQUIRED
```

**Valid status values:** `"Pending Payment"`, `"Paid"`, `"Ready for Pickup"`, `"Completed"`, `"Cancelled"`, `"Expired"`

**Side effects when status transitions to `"Paid"`:**
1. **Loyalty points earned:** `order.loyaltyPointsEarned` is added to `user.loyaltyPoints`, logged as `purchase_reward`
2. **Referral reward:** If `order.referralRewardIssued = false` and the order's user was referred by someone, the referrer receives `floor(order.total * 0.5)` Cloudz, logged as `referral_reward`. `referralRewardIssued` is then set to `true` (idempotent — reward fires exactly once per order).
3. **Streak bonus:** If this is the user's first `Paid` order in the current ISO week, a streak bonus is calculated and awarded.

**Response 200:** `{ "message": "Status updated" }`

**Errors:**
| Status | Condition |
|---|---|
| `404` | Order not found |

---

### `PATCH /api/admin/orders/{order_id}/edit`
**Request body:** `OrderEdit`
```typescript
{
  items:         OrderEditItem[]   // REQUIRED
  total:         number            // REQUIRED
  adminNotes:    string | null
  pickupTime:    string | null
  paymentMethod: string | null
}
```

**Response 200:** Updated `Order`

---

### `GET /api/admin/analytics`
**Response 200:**
```typescript
{
  totalOrders:          number
  totalRevenue:         number
  totalUsers:           number
  avgOrderValue:        number
  repeatRate:           number   // % of users with >1 order
  avgCLV:               number   // average customer lifetime value
  repeatPurchaseRate:   number   // % of users who placed a 2nd order (cohort-based)
  revenueByDay:         { date: string, revenue: number }[]
  topProducts:          { name: string, count: number, revenue: number }[]
  ordersByStatus:       { status: string, count: number }[]
}
```

---

### `GET /api/admin/ledger`
**Query parameters:**
```
skip   integer  default=0
limit  integer  default=50
```

**Response 200:**
```typescript
{
  entries: cloudz_ledger[]
  total:   number
  skip:    number
  limit:   number
}
```

---

### `GET /api/admin/chats`
**Response 200:** Array of chat session summaries with recent messages

---

### `GET /api/chat/messages/{chat_id}`
**Auth:** JWT required (any authenticated user)

**Response 200:** Array of chat messages for the given session

---

### `GET /api/admin/reviews`
**Response 200:** All reviews (including hidden)

---

### `PATCH /api/admin/reviews/{review_id}`
**Request body:** `ReviewModerationUpdate`
```typescript
{
  isHidden: boolean | null
  comment:  string | null
}
```

**Response 200:** `{ "message": "Review updated" }`

**Errors:**
| Status | Condition |
|---|---|
| `400` | No fields to update |
| `404` | Review not found |

---

### `DELETE /api/admin/reviews/{review_id}`
**Response 200:** `{ "message": "Review deleted" }`

**Errors:**
| Status | Condition |
|---|---|
| `404` | Review not found |

---

### `GET /api/admin/support/tickets`
**Response 200:**
```typescript
{ tickets: SupportTicket[], total: number }
```

---

## 13. Support & Push Endpoints

### `POST /api/support/tickets`
**Auth:** JWT required

**Request body:** `SupportTicketCreate`
```typescript
{
  subject: string   // REQUIRED
  message: string   // REQUIRED
}
```

**Response 200:** `{ "id": string }`

---

### `GET /api/health`
**Auth:** Public

**Response 200:** `{ "status": "ok" }`

---

## 14. Business Logic Reference

### Cloudz (Loyalty Points) Earn Events

| Event | Amount | Trigger |
|---|---|---|
| Account signup | +500 | On `POST /api/auth/register` |
| Referral signup bonus | +500 to referrer | When a referred user completes registration |
| Purchase | `floor(order.total) * 3` | When order status → `Paid` |
| Referral purchase reward | `floor(order.total * 0.5)` to referrer | When referred user's order → `Paid` (once per order) |
| Streak bonus | 50 / 100 / 200 / 500 | First `Paid` order each ISO week, based on consecutive-week streak |
| Admin adjustment | any integer | Admin-initiated via `/api/admin/users/{id}/cloudz-adjust` |

### Store Credit
- Stored as `creditBalance` (float) on the user document
- Awarded by admins via `POST /api/admin/users/{id}/credit`
- Applied at checkout via `storeCreditApplied` in `OrderCreate`
- Deducted atomically when order is created
- Fully restored when order is cancelled

### Referral Code
- Auto-generated on registration (unique 8-character alphanumeric string)
- **Immutable** — users cannot change their own referral code
- Can be used as the `referralCode` field at registration (case-insensitive)
- A user's `username` is also accepted as a referral code input at registration
- A user cannot refer themselves

### Order Expiry
- Orders created with status `"Pending Payment"` automatically expire after **30 minutes**
- A background job runs every 5 minutes and sets expired orders to status `"Expired"`
- On expiry, product stock is restored (same as cancellation)
- Store credit is **not** restored on expiry (only on explicit cancellation)

### Payment Methods
Accepted values for `paymentMethod` in `OrderCreate`:
- `"Zelle"`
- `"Venmo"`
- `"CashApp"`

(The API does not validate this field beyond length — frontend should enforce the list.)

### Next-Order Coupon
- Issued by the system after certain order milestones
- Retrieved via `GET /api/me/coupon`
- Applied at checkout with `couponApplied: true` in `OrderCreate`
- Automatically expired server-side if past `expiresAt` date

---

*Document frozen: 2026-03-10 | Source: /app/openapi.json + /app/backend/routes/ + validation suite iteration_32*
