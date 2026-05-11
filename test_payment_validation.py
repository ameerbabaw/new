#!/usr/bin/env python
"""Test payment validation functions"""

from app import validate_card_number, validate_expiry_date, validate_cvv, validate_cardholder_name
from datetime import date

print("=" * 50)
print("PAYMENT VALIDATION TESTS")
print("=" * 50)

all_pass = True

# Card number tests
print("\n[1] CARD NUMBER VALIDATION (Luhn Algorithm):")
test_cards = [
    ("4242424242424242", True, "Valid Visa test card"),
    ("4111111111111111", True, "Valid Visa"),
    ("4000056655665556", True, "Stripe test decline card (passes Luhn)"),
    ("1234567890123456", False, "Invalid Luhn checksum"),
    ("0000000000000000", True, "All zeros (passes Luhn) - note: real cards reject this"),
]

for card, expected, desc in test_cards:
    result = validate_card_number(card)
    status = "[OK]" if result == expected else "[FAIL]"
    if result != expected:
        all_pass = False
    print(f"  {status}: {desc} -> got {result}, expected {expected}")

# Expiry date tests
print("\n[2] EXPIRY DATE VALIDATION:")
current_year = date.today().year
current_month = date.today().month

expiry_tests = [
    (f"{current_month:02d}/{current_year % 100:02d}", True, "Current month/year"),
    (f"01/{current_year % 100 + 1:02d}", True, "Next year"),
    ("01/20", False, "Expired (2020)"),
    ("13/99", False, "Invalid month (13)"),
    ("00/99", False, "Invalid month (00)"),
    ("12/99", True, "Valid future date"),
]

for expiry, expected, desc in expiry_tests:
    result = validate_expiry_date(expiry)
    status = "[OK]" if result == expected else "[FAIL]"
    if result != expected:
        all_pass = False
    print(f"  {status}: {desc} ('{expiry}') -> got {result}, expected {expected}")

# CVV tests
print("\n[3] CVV VALIDATION:")
cvv_tests = [
    ("123", True, "3 digits (standard)"),
    ("1234", True, "4 digits (Amex)"),
    ("12", False, "Too short (2)"),
    ("12345", False, "Too long (5)"),
    ("abc", False, "Non-numeric"),
]

for cvv, expected, desc in cvv_tests:
    result = validate_cvv(cvv)
    status = "[OK]" if result == expected else "[FAIL]"
    if result != expected:
        all_pass = False
    print(f"  {status}: {desc} -> got {result}, expected {expected}")

# Name tests
print("\n[4] CARDHOLDER NAME VALIDATION:")
name_tests = [
    ("Ahmed Mohamed", True, "Valid full name"),
    ("Ah", False, "Too short (2 chars, need 3+)"),
    ("Ali", True, "Exactly 3 chars - valid"),
    ("123", False, "Numbers only"),
    ("A" * 101, False, "Too long (101 chars)"),
    ("", False, "Empty string"),
]

for name, expected, desc in name_tests:
    result = validate_cardholder_name(name)
    status = "[OK]" if result == expected else "[FAIL]"
    if result != expected:
        all_pass = False
    print(f"  {status}: {desc} (len={len(name)}) -> got {result}, expected {expected}")

print("\n" + "=" * 50)
if all_pass:
    print("ALL TESTS PASSED [OK]")
else:
    print("SOME TESTS FAILED [FAIL] - review above")
print("=" * 50)
