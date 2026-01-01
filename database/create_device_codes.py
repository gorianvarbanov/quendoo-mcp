"""Create device_codes table for OAuth Device Flow authentication."""
import sys
from database.connection import engine
from database.models import Base, DeviceCode

def create_device_codes_table():
    """Create the device_codes table if it doesn't exist."""

    print("Creating device_codes table...")

    # Create only the DeviceCode table
    DeviceCode.__table__.create(engine, checkfirst=True)

    print("[OK] device_codes table created successfully")
    print("\nTable structure:")
    print("  - id (UUID, primary key)")
    print("  - device_code (VARCHAR, unique)")
    print("  - user_code (VARCHAR, unique)")
    print("  - user_id (UUID, nullable, foreign key to users)")
    print("  - device_name (VARCHAR, nullable)")
    print("  - is_activated (BOOLEAN)")
    print("  - expires_at (TIMESTAMP)")
    print("  - created_at (TIMESTAMP)")
    print("  - activated_at (TIMESTAMP, nullable)")

if __name__ == "__main__":
    try:
        create_device_codes_table()
    except Exception as e:
        print(f"Error creating table: {e}", file=sys.stderr)
        sys.exit(1)
