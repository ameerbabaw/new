# نظام الدفع - ServStore

## نظرة عامة
يدعم النظام三种 طرق دفع:
1. **بطاقة الائتمان** (محاكاة)
2. **Stripe** (بوابة دفع حقيقية - تتطلب إعداد)
3. **PayPal** (بوابة دفع حقيقية - تتطلب إعداد)

## وضع التشغيل

### وضع التجربة (Demo Mode) - الافتراضي
- `PAYMENT_MODE=demo` في ملف `.env`
- جميع المعاملات تجريبية، لا توجد خصومات حقيقية
- بطاقات اختبارية متاحة للاختبار

### الوضع الحقيقي (Live Mode)
- `PAYMENT_MODE=live` في ملف `.env`
- يتطلب إعداد حسابات Stripe و PayPal حقيقية
- **تحذير**: تأكد من PCI compliance قبل التفعيل

## بطاقات الاختبار (Demo Mode)

### بطاقات ناجحة:
- **4242 4242 4242 4242** - Visa (أي تاريخ مستقبلي، أي CVV)

### بطاقات مرفوضة:
- **4000 0566 5566 5556** - تحاكي الرفض
- أي رقم ينتهي بـ **0000** - تحاكي الرفض

## متغيرات البيئة (.env)

```bash
# Flask
SECRET_KEY=your-secret-key

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...

# PayPal
PAYPAL_CLIENT_ID=...
PAYPAL_SECRET=...

# Payment Mode: 'demo' أو 'live'
PAYMENT_MODE=demo
```

## هيكل قاعدة البيانات

### جدول `Order`
- `id` - معرف الطلب
- `order_id` - UUID فريد
- `check_id` - رقم الشيك (CHK-XXXXXX)
- `status` - pending/paid/delivered
- `payment_method` - stripe/paypal/card
- `transaction_id` - رقم المعاملة
- `paid_at` - تاريخ ووقت الدفع

## مسارات API

### إنشاء طلب
```
POST /api/create_order
Body: {
  "plan_name": "...",
  "game_type": "...",
  "plan_price": 19.99,
  "buyer_name": "...",
  "buyer_email": "...",
  "discord_id": "..."
}
```

### معالجة الدفع بالبطاقة
```
POST /api/payment/<order_id>/process
Body: {
  "cardholder_name": "...",
  "card_number": "...",
  "expiry": "MM/YY",
  "cvv": "..."
}
```

### Stripe
```
POST /api/payment/stripe/create-intent
POST /api/payment/stripe/confirm
```

### PayPal
```
POST /api/payment/paypal/create-order
POST /api/payment/paypal/capture
```

## التحقق من البطاقة

يدعم النظام خوارزمية **Luhn** للتحقق من صحة رقم البطاقة:
- الطول: 13-19 رقم
- التحقق من checksum
- التحقق من تاريخ الصلاحية (تاريخ مستقبلي)
- التحقق من CVV (3-4 أرقام)
- التحقق من اسم حامل البطاقة

## الأمان

1. **Demo Mode**: لا توجد معاملات حقيقية
2. **Live Mode**: يتطلب SSL/TLS و PCI compliance
3. كلمات المرور مشفرة (bcrypt)
4. session management

## الاستخدام في البيئة الحقيقية

1. احصل على Stripe API keys من https://dashboard.stripe.com
2. احصل على PayPal API credentials من https://developer.paypal.com
3. عدّل `PAYMENT_MODE=live` في `.env`
4. تأكد من وجود SSL/TLS (HTTPS)
5. راجع متطلبات PCI compliance

## استكشاف الأخطاء

### الدفع لا يظهر كحقيقي
تأكد من:
- `PAYMENT_MODE=live` في `.env`
- API keys صحيحة
- SSL/TLS مفعل

### Stripe خطأ
- تحقق من `STRIPE_SECRET_KEY` و `STRIPE_PUBLIC_KEY`
- تأكد من أن المفتاح به الصلاحيات المطلوبة

### PayPal خطأ
- تأكد من `PAYPAL_CLIENT_ID` و `PAYPAL_SECRET`
- تحقق من `PAYPAL_API_BASE` (sandbox أو live)

##ziapycharm note
الملفات:
- `app.py` - الخادم الرئيسي
- `templates/payment.html` - صفحة الدفع
- `templates/success.html` - صفحة النجاح
- `.env` - متغيرات البيئة
- `.env.example` - نموذج متغيرات

## المميزات الجديدة

✅ واض housing payment mode (demo/live)
✅ بطاقات اختبارية موثقة
✅ تحقق من البطاقة (Luhn algorithm)
✅ تنسيق تلقائي لمدخلات البطاقة
✅ رسائل توضيحية للمستخدم
✅ صفحة نجاح مفصلة
✅ demo mode warning indicator
✅ PCI compliance ready architecture
