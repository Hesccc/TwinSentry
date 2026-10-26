"""
Migration script: Change Alert.status column type from TEXT to INTEGER
Run this script ONCE to alter the database schema.
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def alter_status_column():
    """Change the status column type from TEXT to INTEGER."""
    app = create_app()

    with app.app_context():
        try:
            # First, ensure all values are numeric
            result = db.session.execute(text("SELECT DISTINCT status FROM alerts")).all()
            non_numeric = [r[0] for r in result if not str(r[0]).isdigit()]
            if non_numeric:
                print(f"ERROR: Found non-numeric status values: {non_numeric}")
                print("Please run migrate_status.py first to convert text values to integers.")
                return

            # Change column type using ALTER TABLE with USING clause for type conversion
            print("Changing status column type from TEXT to INTEGER...")
            db.session.execute(text("ALTER TABLE alerts ALTER COLUMN status TYPE INTEGER USING status::INTEGER"))
            db.session.commit()
            print("Column type changed successfully!")

            # Verify the change
            result = db.session.execute(text("SELECT status FROM alerts LIMIT 1")).first()
            print(f"Verified: status value is now {result[0]!r} (type: {type(result[0]).__name__})")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR: {e}")
            raise

if __name__ == '__main__':
    alter_status_column()
