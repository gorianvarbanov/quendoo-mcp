"""Database connection and session management."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=10,              # Number of permanent connections
    max_overflow=20,           # Max additional connections when pool is full
    pool_pre_ping=True,        # Verify connections before using (handle stale connections)
    echo=False                 # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Session:
    """
    Provide a transactional scope for database operations.

    Usage:
        with get_db_session() as session:
            user = session.query(User).filter_by(email='test@example.com').first()
            session.commit()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """
    Dependency injection for Flask/FastAPI routes.

    Usage (Flask):
        @app.route('/api/users')
        def get_users():
            db = next(get_db())
            users = db.query(User).all()
            return jsonify(users)

    Usage (FastAPI):
        @app.get('/api/users')
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
