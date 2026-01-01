"""Reset database by dropping ALL tables in public schema."""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def reset_database():
    """Drop ALL tables in public schema with CASCADE."""
    print("WARNING: This will drop ALL tables in the public schema!")
    print("Dropping all tables...")

    with engine.connect() as conn:
        # Get all table names
        result = conn.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result]

        if not tables:
            print("No tables found in public schema.")
            return

        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")

        # Drop each table with CASCADE
        for table in tables:
            print(f"Dropping table: {table}")
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
            conn.commit()

        print("All tables dropped successfully!")

if __name__ == "__main__":
    reset_database()
