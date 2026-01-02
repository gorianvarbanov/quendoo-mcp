"""Sync Supabase Auth users to public.users and tenants tables"""
import os
import uuid
import bcrypt
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection
conn = psycopg2.connect(
    host='aws-1-eu-west-1.pooler.supabase.com',
    port=6543,
    database='postgres',
    user='postgres.tjrtbhemajqwzzdzyjtc',
    password='Newestate2019@'
)

# Users from Supabase Auth (created by previous script)
AUTH_USERS = [
    {
        "id": "e27fe8a8-afba-45ff-9db5-75ae0f4e0b18",
        "email": "test@example.com",
        "full_name": "Test User"
    },
    {
        "id": "ff56938d-3ef3-4c68-aab2-190083e914c8",
        "email": "demo@quendoo.com",
        "full_name": "Demo User"
    },
    {
        "id": "4a9d7c9a-ed3c-44b8-96f1-2e1941a1c77b",
        "email": "admin@quendoo.com",
        "full_name": "Admin User"
    },
]

def sync_user(user_id: str, email: str, full_name: str):
    """Create user in public.users and corresponding tenant"""
    cur = conn.cursor()

    # Check if user already exists in public.users
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    existing = cur.fetchone()

    if existing:
        print(f"[SKIP] User already exists in public.users: {email}")
        cur.close()
        return

    # Create dummy password hash (user will authenticate via Supabase Auth)
    dummy_password = bcrypt.hashpw(b"dummy_password", bcrypt.gensalt()).decode('utf-8')

    # Insert into public.users
    cur.execute("""
        INSERT INTO users (id, email, password_hash, full_name, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    """, (user_id, email, dummy_password, full_name, True))

    print(f"[OK] Created user in public.users: {email}")

    # Create tenant
    tenant_id = str(uuid.uuid4())
    tenant_name = f"{full_name}'s Tenant"

    cur.execute("""
        INSERT INTO tenants (id, user_id, tenant_name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
    """, (tenant_id, user_id, tenant_name))

    print(f"[OK] Created tenant: {tenant_name} (ID: {tenant_id})")

    conn.commit()
    cur.close()

def main():
    print("=" * 60)
    print("Syncing Supabase Auth Users to Public Schema")
    print("=" * 60)
    print()

    for user in AUTH_USERS:
        sync_user(user["id"], user["email"], user["full_name"])

    print()
    print("=" * 60)
    print("Sync Complete!")
    print("=" * 60)

    conn.close()

if __name__ == "__main__":
    main()
