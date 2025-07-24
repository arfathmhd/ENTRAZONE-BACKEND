import os
import django

# 🔁 Replace 'your_project_name' with your actual Django project name (folder that contains settings.py)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ENTRAZONE.settings')  # update this if different

# Setup Django environment
django.setup()

from dashboard.models import CustomUser, Otp
from random import randint

# Config
name = "cybernox"
phone = "9876543210"
request_id = "test-request-id"
otp_code = 5555

# Create or get user
user, created = CustomUser.objects.get_or_create(
    phone_number=phone,
    defaults={"username": name, "name": name, "email": ""}
)

if created:
    print("✅ Created user:", user.username)
else:
    print("ℹ️  User already exists:", user.username)

# Create OTP
otp = Otp.objects.create(
    requested_by=user,
    code=otp_code,
    request_id=request_id,
    verified=False
)

print(f"✅ OTP saved: {otp.code} for user {user.phone_number} (verified={otp.verified})")