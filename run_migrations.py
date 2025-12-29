"""
Run database migrations.
"""
import os
import sys

def run_migrations():
    """Run all database migrations."""
    try:
        import psycopg2
        from dotenv import load_dotenv

        load_dotenv()

        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print("[WARNING] No DATABASE_URL set, skipping migrations", file=sys.stderr)
            return

        print("[INFO] Connecting to database for migrations...", file=sys.stderr)
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Read and execute migration
        migration_file = 'migrations/002_oauth_tables.sql'
        if os.path.exists(migration_file):
            print(f"[INFO] Applying migration: {migration_file}", file=sys.stderr)
            with open(migration_file, 'r') as f:
                sql = f.read()

            cur.execute(sql)
            conn.commit()
            print(f"[INFO] Migration applied successfully!", file=sys.stderr)
        else:
            print(f"[WARNING] Migration file not found: {migration_file}", file=sys.stderr)

        cur.close()
        conn.close()

    except ImportError:
        print("[WARNING] psycopg2 not installed, skipping migrations", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

if __name__ == "__main__":
    run_migrations()
