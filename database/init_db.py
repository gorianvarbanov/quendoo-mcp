"""Database initialization script - creates all tables."""
from database.connection import engine
from database.models import Base

def init_database():
    """Create all tables in the database."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    print("\nCreated tables:")
    for table in Base.metadata.tables.keys():
        print(f"  - {table}")

if __name__ == "__main__":
    init_database()
