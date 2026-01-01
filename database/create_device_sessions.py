"""Create device_sessions table for Claude Desktop authentication."""
import sys
from database.connection import engine
from database.models import Base, DeviceSession

def create_device_sessions_table():
    """Create the device_sessions table if it doesn't exist."""

    print("Creating device_sessions table...")

    # Create only the DeviceSession table
    DeviceSession.__table__.create(engine, checkfirst=True)

    print("[OK] device_sessions table created successfully")
    print("\nTable structure:")
    print("  - id (UUID, primary key)")
    print("  - user_id (UUID, foreign key to users)")
    print("  - device_name (VARCHAR)")
    print("  - is_active (BOOLEAN)")
    print("  - created_at (TIMESTAMP)")
    print("  - last_used_at (TIMESTAMP)")

if __name__ == "__main__":
    try:
        create_device_sessions_table()
    except Exception as e:
        print(f"Error creating table: {e}", file=sys.stderr)
        sys.exit(1)
