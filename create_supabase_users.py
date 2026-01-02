"""Create test users in Supabase Auth"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Test users to create
TEST_USERS = [
    {"email": "test@example.com", "password": "Test123456!"},
    {"email": "demo@quendoo.com", "password": "Demo123456!"},
    {"email": "admin@quendoo.com", "password": "Admin123456!"},
]

def create_user(email: str, password: str):
    """Create user in Supabase Auth"""
    url = f"{SUPABASE_URL}/auth/v1/admin/users"

    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "email": email,
        "password": password,
        "email_confirm": True,  # Auto-confirm email
        "user_metadata": {
            "full_name": email.split("@")[0].title()
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code in (200, 201):
        user = response.json()
        print(f"[OK] Created user: {email} (ID: {user['id']})")
        return user
    elif response.status_code == 422 and "already registered" in response.text:
        print(f"[WARN] User already exists: {email}")
        return None
    else:
        print(f"[ERROR] Failed to create {email}: {response.status_code} - {response.text}")
        return None

def main():
    print("=" * 60)
    print("Creating Test Users in Supabase Auth")
    print("=" * 60)
    print(f"Supabase URL: {SUPABASE_URL}")
    print()

    for user_data in TEST_USERS:
        create_user(user_data["email"], user_data["password"])

    print()
    print("=" * 60)
    print("Done! Users created in Supabase Auth.")
    print("=" * 60)
    print()
    print("You can now login with:")
    for user_data in TEST_USERS:
        print(f"  - {user_data['email']} / {user_data['password']}")

if __name__ == "__main__":
    main()
