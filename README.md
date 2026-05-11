# ServStore - Gaming Server Store

A Flask-based web application for selling game servers (Minecraft, FiveM, RedM) with integrated payment processing.

## Features

### Payment System
- **Card Payment** (simulated/demo mode) with proper validation
- **Stripe Integration** (ready for live deployment)
- **PayPal Integration** (ready for live deployment)
- **Demo Mode** - safe testing with test cards
- **Live Mode** - real payment processing

### Key Features
- User registration and authentication
- Order management system
- Admin dashboard for order management
- Server account delivery system
- Arabic RTL interface
- Responsive modern UI

## Quick Start

### 1. Clone and Setup
```bash
cd C:\Users\ameer\Desktop\web2
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
cp .env.example .env
# Edit .env with your settings
```

**Minimum .env configuration:**
```bash
SECRET_KEY=your-secret-key-here
PAYMENT_MODE=demo  # Change to 'live' for real payments
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
PAYPAL_CLIENT_ID=...
PAYPAL_SECRET=...
```

### 3. Initialize Database
```bash
python app.py
# Admin user created: admin / admin123
```

### 4. Run Application
```bash
python app.py
# Server runs at http://localhost:5000
```

## Payment System Details

### Demo Mode (Default)
All payments are simulated - **no real charges**.

**Test Cards:**
| Card Number | Result |
|-------------|--------|
| `4242 4242 4242 4242` | ✅ Success |
| `4000 0566 5566 5556` | ❌ Declined |
| Any card ending `0000` | ❌ Declined |

**Features in Demo Mode:**
- Full card validation (Luhn algorithm)
- Expiry date checking
- CVV validation
- Demo transaction IDs (starts with `DEMO-`)
- Clear visual indicators that it's demo mode

### Live Mode
For production use with real payments:
1. Get Stripe keys from [Stripe Dashboard](https://dashboard.stripe.com)
2. Get PayPal keys from [PayPal Developer](https://developer.paypal.com)
3. Set `PAYMENT_MODE=live` in `.env`
4. **Requirement:** HTTPS + PCI compliance

### Card Validation
The system implements:
- **Luhn Algorithm** - verifies card number checksum
- **Expiry Date** - checks if date is in the future
- **CVV** - validates 3 or 4 digit codes
- **Cardholder Name** - validates proper name format

### Transaction Flow
```
User selects plan → Enters buyer info → Chooses payment method
→ Validates card data → Processes payment → Updates order status
→ Generates transaction ID → Shows success page
```

## Project Structure

```
web2/
├── app.py                     # Main Flask application
├── requirements.txt            # Python dependencies
├── .env                       # Environment variables (gitignored)
├── .env.example               # Environment template
├── .gitignore                 # Git ignore file
├── serve_store.db             # SQLite database (auto-created)
├── PAYMENTS.md                # Payment system documentation
├── CHANGES_SUMMARY.md         # Change log
├── test_payment_validation.py # Validation unit tests
├── integration_test.py         # End-to-end tests
├── templates/
│   ├── index.html             # Home page with plans
│   ├── login.html             # User login/register
│   ├── payment.html           # Payment processing page
│   ├── success.html           # Payment success page
│   ├── admin.html             # Admin dashboard
│   └── user_orders.html       # User orders history
└── static/                    # CSS, JS, images (if any)
```

## Admin Panel

Access at: `http://localhost:5000/admin/login`

Default credentials:
- Username: `admin`
- Password: `admin123`

**Admin Features:**
- View all orders
- Update order status (pending → paid → delivered)
- Add server accounts to orders
- View revenue statistics
- Manage users

## Database Models

### User
- `id`, `username`, `email`, `password`, `is_admin`
- Created timestamp

### Order
- `id`, `order_id` (UUID), `check_id` (CHK-XXXXXX)
- `plan_name`, `game_type`, `plan_price`
- `buyer_name`, `buyer_email`, `discord_id`
- `status` (pending/paid/delivered)
- `payment_method` (card/stripe/paypal)
- `transaction_id`, `paid_at`

### ServerAccount
- `order_id` (foreign key)
- `username`, `password`, `server_ip`, `port`
- `control_panel`, `root_password`

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - User login
- `GET /register` - Registration page
- `POST /register` - Create user
- `GET /logout` - Logout

### Shop
- `GET /` - Home page with plans
- `POST /api/create_order` - Create new order

### Payment
- `GET /payment/<order_id>` - Payment page
- `POST /api/payment/card/validate` - Validate card
- `POST /api/payment/<order_id>/process` - Process card payment
- `POST /api/payment/stripe/create-intent` - Create Stripe intent
- `POST /api/payment/stripe/confirm` - Confirm Stripe payment
- `POST /api/payment/paypal/create-order` - Create PayPal order
- `POST /api/payment/paypal/capture` - Capture PayPal payment
- `GET /payment/<order_id>/success` - Success page

### Admin (Requires admin)
- `GET /admin` - Admin dashboard
- `GET /admin/login` - Admin login
- `POST /api/admin/order/<id>/update-status` - Update order status
- `POST /api/admin/order/<id>/add-server` - Add server account
- `GET /api/admin/orders` - List all orders

### User
- `GET /user/orders` - User's orders
- `GET /api/user/orders` - API for user orders

## Testing

Run unit tests:
```bash
python test_payment_validation.py
```

Run integration test:
```bash
python integration_test.py
```

## Security

- Passwords hashed with bcrypt
- Session-based authentication
- SQLAlchemy ORM (SQL injection protected)
- CSRF protection recommended for production
- `.env` file excluded from git
- Input validation on all endpoints
- Test mode prevents accidental real charges

## For Production Deployment

1. **Change SECRET_KEY** to a strong random value
2. **Set PAYMENT_MODE=live**
3. **Configure Stripe** with live API keys
4. **Configure PayPal** with live credentials
5. **Enable HTTPS** (required for PCI compliance)
6. **Use a production WSGI server** (Gunicorn, uWSGI)
7. **Use PostgreSQL** instead of SQLite
8. **Set up proper logging**
9. **Configure email service** for notifications
10. **Review PCI DSS requirements** for card handling

## Troubleshooting

### "Payment doesn't show real vs demo"
✅ **Fixed** - Demo mode now has clear visual indicators and documentation.

### "Card validation not working"
✅ **Fixed** - Full Luhn algorithm implementation added.

### "Stripe/PayPal not configured"
Ensure `.env` has correct API keys. In demo mode, Stripe/PayPal tabs show appropriate messages.

### Database errors
Delete `serve_store.db` and restart app to recreate fresh database.

## Recent Changes

See `CHANGES_SUMMARY.md` for detailed list of improvements.

**Version 1.1 (Payment Fix Release):**
- ✅ Clear demo/live mode distinction
- ✅ Proper card validation (Luhn)
- ✅ Test card documentation
- ✅ Demo mode warning banners
- ✅ Enhanced success page with transaction details
- ✅ Input formatting (auto-spacing)
- ✅ Timezone-aware datetime handling
- ✅ Comprehensive test suite

## License

Educational/Demo Project

## Support

For issues, check `PAYMENTS.md` documentation or create an issue in the repository.

---

**Note:** This system is designed for educational/demo purposes. For production e-commerce, additional security measures and PCI compliance are required.
