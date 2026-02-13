# Cloud District Club - Mobile Vape Ordering App

A fast, local pickup mobile ordering app for adults 21+ to purchase disposable vape products with loyalty rewards and manual payment confirmation.

## 🚀 Features

### Core Features
- ✅ **Age Verification** - Mandatory 21+ age gate with DOB verification
- ✅ **JWT Authentication** - Email/password based user accounts
- ✅ **Product Catalog** - Browse vapes by brand (Geek Bar, Lost Mary, RAZ, Meloso, Digiflavor)
- ✅ **Shopping Cart** - Add/remove items, adjust quantities
- ✅ **Checkout Flow** - Select pickup time + payment method
- ✅ **Local Pickup Only** - No shipping, store pickup only
- ✅ **Manual Payment Confirmation** - Zelle, Venmo, Cash App, Chime (3% fee on non-Zelle)
- ✅ **Cloudz Loyalty Points** - Earn 1 point per dollar, redeem for discounts
- ✅ **Order Management** - Track order status (Pending Payment → Paid → Ready → Completed)
- ✅ **Admin Dashboard** - Manage orders, update status, confirm payments
- ✅ **Dark Premium Theme** - Sleek mobile-first design

## 📱 Tech Stack

**Frontend:**
- Expo (React Native)
- React Navigation (tabs + stack)
- Zustand (state management)
- Axios (API calls)
- TypeScript

**Backend:**
- FastAPI (Python)
- MongoDB (database)
- JWT authentication
- Passlib + Bcrypt (password hashing)

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
# Frontend
cd /app/frontend
yarn install

# Backend dependencies already installed
```

### 2. Start Services

Services are already running via supervisor:
- Frontend: http://localhost:3000 (Expo)
- Backend: http://localhost:8001 (FastAPI)
- MongoDB: localhost:27017

### 3. Create Admin User & Seed Products

**Option A: Use Python Script (Recommended)**

```bash
# First, register a user in the app
# Then run:
cd /app/backend
python3 setup_admin.py
# Follow the prompts to make your user an admin and add sample products
```

**Option B: Manual MongoDB Commands**

```bash
# Connect to MongoDB
mongosh

# Switch to database
use cloud_district_club

# Make user admin (replace email with your registered email)
db.users.updateOne(
  {email: "youremail@example.com"}, 
  {$set: {isAdmin: true}}
)

# Add a sample product
db.products.insertOne({
  name: "Geek Bar Pulse X",
  brand: "Geek Bar",
  category: "geek-bar",
  image: "data:image/png;base64,YOUR_BASE64_IMAGE",
  puffCount: 25000,
  flavor: "Watermelon Ice",
  nicotinePercent: 5.0,
  price: 24.99,
  stock: 15
})
```

## 📖 User Guide

### For Customers

1. **Register/Login**
   - Verify you're 21+ on age gate
   - Create account with email/password
   - Must provide date of birth

2. **Browse & Shop**
   - Browse featured products on home
   - Shop by brand or view all products
   - View product details (puff count, nicotine %, flavor)
   - Add items to cart

3. **Checkout**
   - Select pickup time window
   - Choose payment method:
     - Zelle (0% fee)
     - Venmo/Cash App/Chime (3% fee)
   - Use Cloudz Points for discounts (10¢ per point)
   - Submit order

4. **Payment**
   - Follow payment instructions screen
   - Send payment to provided username/email
   - Include order number in payment note
   - Wait for admin to confirm payment

5. **Pickup**
   - Order status updates: Pending → Paid → Ready for Pickup
   - Receive notification when ready
   - Pick up during selected time window

6. **Loyalty Points**
   - Earn 1 point per $1 spent
   - Points added when order marked "Paid"
   - View balance in header and account page
   - Redeem at checkout

### For Admins

1. **Access Admin Dashboard**
   - Login with admin account
   - Tap "Admin Dashboard" button on Home or Account page

2. **Manage Orders**
   - View all orders across all statuses
   - Filter by status: Pending Payment, Paid, Ready for Pickup, Completed
   - See customer info, items, total, payment method, pickup time

3. **Update Order Status**
   - Tap "Update Status" on any order
   - Select new status:
     - **Pending Payment** - Default, awaiting customer payment
     - **Paid** - Payment received and verified (awards loyalty points)
     - **Ready for Pickup** - Order prepared, customer can pickup
     - **Completed** - Order picked up

4. **Payment Verification**
   - Customer submits order → status: "Pending Payment"
   - Check Zelle/Venmo/Cash App/Chime for payment
   - Verify order number matches payment note
   - Mark order as "Paid" → loyalty points automatically added

## 🔧 API Endpoints

### Public
- `GET /api/categories` - Get product categories
- `GET /api/products` - Get all products

### Auth
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user (requires auth)

### Products (Admin only)
- `POST /api/products` - Create product
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product

### Orders
- `POST /api/orders` - Create order (requires auth)
- `GET /api/orders` - Get user orders (requires auth)
- `GET /api/orders/{id}` - Get single order (requires auth)

### Admin
- `GET /api/admin/orders` - Get all orders (requires admin)
- `PATCH /api/admin/orders/{id}/status` - Update order status (requires admin)

## 🎨 Design System

**Colors:**
- Background: `#0c0c0c` (near black)
- Cards: `#1a1a1a` (dark gray)
- Primary: `#6366f1` (indigo)
- Success: `#10b981` (green)
- Warning: `#fbbf24` (yellow)
- Error: `#dc2626` (red)
- Text: `#fff`, `#999`, `#666`

**Components:**
- Bottom tab navigation (Home, Shop, Orders, Account)
- Stack navigation for details/modals
- Dark themed cards with rounded corners
- Touch-optimized buttons (44px+ height)

## 🔐 Security

- Passwords hashed with bcrypt
- JWT tokens with 7-day expiration
- Age verification stored locally
- Admin-only routes protected
- CORS enabled for development

## 📝 Payment Confirmation Flow

1. Customer places order → status: **Pending Payment**
2. Customer sees payment instructions (amount, username, order #)
3. Customer sends payment via chosen method (Zelle/Venmo/etc.)
4. Admin receives payment notification
5. Admin verifies payment matches order
6. Admin marks order **Paid** → loyalty points awarded
7. Admin prepares order
8. Admin marks **Ready for Pickup** → customer notified
9. Customer picks up order
10. Admin marks **Completed**

## 🎯 Loyalty Program (Cloudz Points)

- **Earn:** 1 point per $1 spent (rounded down)
- **Awarded:** When order status changes to "Paid"
- **Redeem:** At checkout ($0.10 per point value)
- **Max Discount:** Can discount up to 100% of order
- **Points Deducted:** When order is submitted (immediately)
- **View Balance:** Header, Account page, Checkout page

## ⚠️ Important Notes

- **Local Pickup Only** - No shipping functionality
- **Manual Payment Confirmation** - Admin must verify and confirm payments
- **21+ Only** - Age gate required, DOB verified on registration
- **Nicotine Warning** - Displayed throughout app
- **Payment Usernames** - Update in `/app/frontend/app/payment-instructions.tsx`
  - Zelle: clouddistrictclub@email.com
  - Venmo: @CloudDistrictClub
  - Cash App: $CloudDistrictClub
  - Chime: clouddistrictclub@email.com

## 📦 Project Structure

```
/app
├── backend/
│   ├── server.py           # FastAPI app with all endpoints
│   ├── setup_admin.py      # Admin setup script
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── (tabs)/         # Tab navigation screens
│   │   │   ├── home.tsx
│   │   │   ├── shop.tsx
│   │   │   ├── orders.tsx
│   │   │   └── account.tsx
│   │   ├── admin/
│   │   │   └── dashboard.tsx
│   │   ├── auth/
│   │   │   ├── login.tsx
│   │   │   └── register.tsx
│   │   ├── product/
│   │   │   └── [id].tsx
│   │   ├── age-gate.tsx
│   │   ├── cart.tsx
│   │   ├── checkout.tsx
│   │   ├── payment-instructions.tsx
│   │   ├── _layout.tsx
│   │   └── index.tsx
│   ├── store/
│   │   ├── authStore.ts    # Auth state (Zustand)
│   │   └── cartStore.ts    # Cart state (Zustand)
│   └── package.json
```

## 🚀 Next Steps

### Immediate (MVP Complete)
- [x] Age verification
- [x] User authentication
- [x] Product catalog
- [x] Shopping cart
- [x] Checkout flow
- [x] Payment instructions
- [x] Loyalty points
- [x] Order management
- [x] Admin dashboard

### Future Enhancements
- [ ] Real product images (replace placeholders)
- [ ] Email notifications (order confirmations)
- [ ] Push notifications (via Firebase)
- [ ] Live chat (Socket.io)
- [ ] QR codes for payments
- [ ] Product search & filters
- [ ] Customer reviews
- [ ] Promotional codes
- [ ] Admin product management UI
- [ ] Sales analytics

## 📄 License

Proprietary - Cloud District Club

## 👥 Support

For issues or questions, contact the development team.

---

**Built with ❤️ for Cloud District Club**
