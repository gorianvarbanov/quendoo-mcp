"""Drop all existing tables from the database."""
from database.connection import engine
from database.models import Base

def drop_all_tables():
    """Drop all tables in the database."""
    print("WARNING: This will drop ALL tables in the database!")
    print("Dropping tables...")

    Base.metadata.drop_all(bind=engine)

    print("All tables dropped successfully!")

if __name__ == "__main__":
    drop_all_tables()
