from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone, date
import calendar
import os
from functools import wraps
import stripe
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///serve_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Payment Mode: 'demo' or 'live'
PAYMENT_MODE = os.getenv('PAYMENT_MODE', 'demo')

db = SQLAlchemy(app)

# Stripe Configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_your_key')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', 'pk_test_your_key')

# PayPal Configuration
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', 'your_paypal_client_id')
PAYPAL_SECRET = os.getenv('PAYPAL_SECRET', 'your_paypal_secret')
PAYPAL_API_BASE = 'https://api.sandbox.paypal.com'

# ============= DATABASE MODELS =============

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), unique=True, default=lambda: str(uuid.uuid4()))
    check_id = db.Column(db.String(20), unique=True, default=lambda: 'CHK-' + str(uuid.uuid4())[:8].upper())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_name = db.Column(db.String(120), nullable=False)
    game_type = db.Column(db.String(50), nullable=False)
    plan_price = db.Column(db.Float, nullable=False)
    buyer_name = db.Column(db.String(120), nullable=False)
    buyer_email = db.Column(db.String(120), nullable=False)
    discord_id = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')  # pending, paid, delivered
    payment_method = db.Column(db.String(50))  # stripe, paypal, card
    transaction_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at = db.Column(db.DateTime)
    
class ServerAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    username = db.Column(db.String(120))
    password = db.Column(db.String(120))
    server_ip = db.Column(db.String(50))
    port = db.Column(db.Integer)
    control_panel = db.Column(db.String(255))
    root_password = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# ============= AUTH DECORATORS =============

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ============= AUTH ROUTES =============

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')

        if not all([username, email, password, confirm_password]):
            return jsonify({'success': False, 'message': 'جميع الحقول مطلوبة'}), 400

        if password != confirm_password:
            return jsonify({'success': False, 'message': 'كلمات المرور غير متطابقة'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'اسم المستخدم موجود بالفعل'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'البريد الإلكتروني موجود بالفعل'}), 400

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return jsonify({'success': True, 'message': 'تم التسجيل بنجاح، يمكنك تسجيل الدخول الآن'})

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return jsonify({'success': True, 'redirect': '/admin' if user.is_admin else '/'})
        
        return jsonify({'success': False, 'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'}), 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ============= SHOP ROUTES =============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    
    order = Order(
        plan_name=data.get('plan_name'),
        game_type=data.get('game_type'),
        plan_price=data.get('plan_price'),
        buyer_name=data.get('buyer_name'),
        buyer_email=data.get('buyer_email'),
        discord_id=data.get('discord_id'),
        user_id=session.get('user_id', 1)  # Default to user 1 if not logged in
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({
        'success': True,
        'order_id': order.id,
        'check_id': order.check_id
    })

# ============= PAYMENT ROUTES =============

@app.route('/payment/<int:order_id>')
def payment_page(order_id):
    order = Order.query.get(order_id)
    if not order:
        return redirect('/')
    
    return render_template('payment.html', 
                          order=order, 
                          stripe_key=STRIPE_PUBLIC_KEY,
                          payment_mode=PAYMENT_MODE)

# ============= STRIPE PAYMENT =============

@app.route('/api/payment/stripe/create-intent', methods=['POST'])
def stripe_create_intent():
    data = request.get_json()
    order = Order.query.get(data.get('order_id'))
    
    if not order:
        return jsonify({'success': False}), 404

    try:
        intent = stripe.PaymentIntent.create(
            amount=int(order.plan_price * 100),
            currency='usd',
            metadata={'order_id': order.id, 'check_id': order.check_id}
        )
        
        return jsonify({
            'success': True,
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/payment/stripe/confirm', methods=['POST'])
def stripe_confirm():
    data = request.get_json()
    order_id = data.get('order_id')
    intent_id = data.get('intent_id')
    
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False}), 404

    try:
        intent = stripe.PaymentIntent.retrieve(intent_id)
        
        if intent.status == 'succeeded':
            order.status = 'paid'
            order.payment_method = 'stripe'
            order.transaction_id = intent_id
            order.paid_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'فشل الدفع'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= PAYPAL PAYMENT =============

def get_paypal_access_token():
    auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
    headers = {'Accept': 'application/json', 'Accept-Language': 'en_US'}
    data = {'grant_type': 'client_credentials'}
    
    response = requests.post(
        f'{PAYPAL_API_BASE}/v1/oauth2/token',
        auth=auth,
        headers=headers,
        data=data
    )
    
    if response.status_code == 200:
        return response.json()['access_token']
    return None

@app.route('/api/payment/paypal/create-order', methods=['POST'])
def paypal_create_order():
    data = request.get_json()
    order = Order.query.get(data.get('order_id'))
    
    if not order:
        return jsonify({'success': False}), 404

    access_token = get_paypal_access_token()
    if not access_token:
        return jsonify({'success': False, 'message': 'خطأ في الاتصال بـ PayPal'}), 500

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'amount': {
                'currency_code': 'USD',
                'value': str(order.plan_price)
            },
            'custom_id': str(order.id)
        }],
        'return_url': f'http://localhost:5000/api/payment/paypal/return',
        'cancel_url': f'http://localhost:5000/payment/{order.id}'
    }

    response = requests.post(
        f'{PAYPAL_API_BASE}/v1/checkout/orders',
        headers=headers,
        json=payload
    )

    if response.status_code == 201:
        paypal_order = response.json()
        return jsonify({
            'success': True,
            'id': paypal_order['id'],
            'approve_link': next(
                (link['href'] for link in paypal_order['links'] if link['rel'] == 'approve'),
                None
            )
        })
    
    return jsonify({'success': False}), 400

@app.route('/api/payment/paypal/capture', methods=['POST'])
def paypal_capture():
    data = request.get_json()
    order_id = data.get('order_id')
    paypal_order_id = data.get('paypal_order_id')
    
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False}), 404

    access_token = get_paypal_access_token()
    if not access_token:
        return jsonify({'success': False}), 500

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.post(
        f'{PAYPAL_API_BASE}/v1/checkout/orders/{paypal_order_id}/capture',
        headers=headers
    )

    if response.status_code == 201:
        result = response.json()
        if result['status'] == 'COMPLETED':
            order.status = 'paid'
            order.payment_method = 'paypal'
            order.transaction_id = paypal_order_id
            order.paid_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return jsonify({'success': True})
    
    return jsonify({'success': False}), 400

# ============= CARD PAYMENT VALIDATION =============

def validate_card_number(card_number):
    """تحقق من رقم البطاقة باستخدام خوارزمية Luhn"""
    # Remove spaces and non-digits
    card_number = ''.join(filter(str.isdigit, card_number))
    
    if not card_number or len(card_number) < 13 or len(card_number) > 19:
        return False
    
    # Luhn algorithm
    total = 0
    reverse_digits = card_number[::-1]
    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    
    return total % 10 == 0

def validate_expiry_date(expiry):
    """تحقق من تاريخ الصلاحية (MM/YY)"""
    try:
        if not '/' in expiry:
            return False
        
        month_str, year_str = expiry.split('/')
        month = int(month_str)
        year = int(year_str) + 2000  # Convert YY to YYYY
        
        if month < 1 or month > 12:
            return False
        
        from datetime import date
        now = date.today()
        expiry_date = date(year, month, 1)
        
        # Check if expiry is in the future
        # Return last day of month for comparison
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        expiry_date = date(year, month, last_day)
        
        return expiry_date >= now
    except:
        return False

def validate_cvv(cvv):
    """تحقق من رمز CVV"""
    cvv = ''.join(filter(str.isdigit, cvv))
    return len(cvv) in [3, 4]

def validate_cardholder_name(name):
    """تحقق من اسم حامل البطاقة"""
    # Remove extra spaces and check length
    name = name.strip()
    return len(name) >= 3 and len(name) <= 100 and any(c.isalpha() for c in name)

# ============= CARD PAYMENT ENDPOINT =============

@app.route('/api/payment/card/validate', methods=['POST'])
def validate_card():
    """التحقق من بيانات البطاقة"""
    data = request.get_json()
    
    cardholder_name = data.get('cardholder_name', '').strip()
    card_number = data.get('card_number', '').strip()
    expiry = data.get('expiry', '').strip()
    cvv = data.get('cvv', '').strip()
    
    errors = []
    
    if not validate_cardholder_name(cardholder_name):
        errors.append('اسم حامل البطاقة غير صحيح')
    
    if not validate_card_number(card_number):
        errors.append('رقم البطاقة غير صحيح')
    
    if not validate_expiry_date(expiry):
        errors.append('تاريخ الصلاحية غير صحيح أو منتهي')
    
    if not validate_cvv(cvv):
        errors.append('CVV غير صحيح')
    
    if errors:
        return jsonify({'success': False, 'errors': errors}), 400
    
    return jsonify({'success': True, 'message': 'البطاقة صحيحة'})

@app.route('/api/payment/<int:order_id>/process', methods=['POST'])
def process_payment(order_id):
    """معالجة الدفع بالبطاقة"""
    data = request.get_json()

    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404

    # التحقق من بيانات البطاقة
    cardholder_name = data.get('cardholder_name', '').strip()
    card_number = data.get('card_number', '').strip()
    expiry = data.get('expiry', '').strip()
    cvv = data.get('cvv', '').strip()
    
    # Clean card number for validation
    card_number_clean = ''.join(filter(str.isdigit, card_number))

    errors = []

    if not validate_cardholder_name(cardholder_name):
        errors.append('اسم حامل البطاقة غير صحيح')

    if not validate_card_number(card_number):
        errors.append('رقم البطاقة غير صحيح أو غير صالح')

    if not validate_expiry_date(expiry):
        errors.append('تاريخ الصلاحية غير صحيح أو منتهي')

    if not validate_cvv(cvv):
        errors.append('CVV غير صحيح')

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    try:
        # ============ DEMO MODE ============
        if PAYMENT_MODE == 'demo':
            # Test card numbers that work in demo mode
            test_cards = [
                '4242424242424242',  # Visa (success)
                '4000056655665556',  # Visa (declined)
            ]
            
            # Check if it's a test card
            is_test_card = card_number_clean in test_cards or card_number_clean.endswith('0000')
            
            if card_number_clean.endswith('0000') or card_number_clean == '4000056655665556':
                # Simulate declined card
                return jsonify({
                    'success': False, 
                    'message': 'تم رفض البطاقة من قبل البنك (بطاقة اختبارية)',
                    'demo_mode': True
                }), 400
            
            # Generate demo transaction ID
            transaction_id = f'DEMO-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}-{str(uuid.uuid4())[:8]}'

            # Update order as paid
            order.status = 'paid'
            order.payment_method = 'card (demo)'
            order.transaction_id = transaction_id
            order.paid_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'تم الدفع بنجاح (وضع التجربة - لا يوجد خصم حقيقي)',
                'demo_mode': True,
                'transaction_id': transaction_id
            })

        # ============ LIVE MODE ============
        else:
            # In live mode, you would integrate with a real payment processor
            # For now, we'll simulate for safety (never process real cards without proper PCI compliance)
            return jsonify({
                'success': False, 
                'message': 'نظام الدفع الحقيقي غير مفعل حالياً. يرجى استخدام وضع التجربة.',
                'live_mode_required': True
            }), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'خطأ: {str(e)}'}), 500

@app.route('/payment/<int:order_id>/success')
def payment_success(order_id):
    order = Order.query.get(order_id)
    if not order or order.status != 'paid':
        return redirect('/')
    
    return render_template('success.html', order=order)

# ============= ADMIN PANEL =============

@app.route('/admin/login')
def admin_login():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.is_admin:
            return redirect('/admin')
    return render_template('login.html', is_admin=True)

@app.route('/admin')
@admin_required
def admin_dashboard():
    orders = Order.query.all()
    users = User.query.all()
    total_revenue = sum(o.plan_price for o in orders if o.status == 'paid')
    
    return render_template('admin.html', 
        orders=orders, 
        users=users, 
        total_revenue=total_revenue
    )

@app.route('/api/admin/orders')
@admin_required
def admin_orders_api():
    orders = Order.query.all()
    return jsonify([{
        'id': o.id,
        'check_id': o.check_id,
        'plan_name': o.plan_name,
        'buyer_name': o.buyer_name,
        'price': o.plan_price,
        'status': o.status,
        'payment_method': o.payment_method,
        'created_at': o.created_at.isoformat()
    } for o in orders])

@app.route('/api/admin/order/<int:order_id>/update-status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    data = request.get_json()
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'success': False}), 404

    order.status = data.get('status')
    db.session.commit()

    return jsonify({'success': True})

@app.route('/api/admin/order/<int:order_id>/add-server', methods=['POST'])
@admin_required
def add_server_account(order_id):
    data = request.get_json()
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'success': False}), 404

    server = ServerAccount(
        order_id=order_id,
        username=data.get('username'),
        password=data.get('password'),
        server_ip=data.get('server_ip'),
        port=data.get('port'),
        control_panel=data.get('control_panel'),
        root_password=data.get('root_password')
    )
    
    db.session.add(server)
    order.status = 'delivered'
    db.session.commit()

    return jsonify({'success': True})

@app.route('/user/orders')
@login_required
def user_orders():
    user = User.query.get(session['user_id'])
    return render_template('user_orders.html', user=user)

@app.route('/api/user/orders')
@login_required
def user_orders_api():
    user_id = session['user_id']
    orders = Order.query.filter_by(user_id=user_id).all()
    
    return jsonify([{
        'id': o.id,
        'check_id': o.check_id,
        'plan_name': o.plan_name,
        'price': o.plan_price,
        'status': o.status,
        'created_at': o.created_at.isoformat()
    } for o in orders])

# ============= DATABASE INITIALIZATION =============

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@servstore.com', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✓ Admin user created: admin / admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='localhost', port=5000)
