"""
Migration script: Convert Alert.status from Chinese text to numeric dictionary
Run this script ONCE to migrate existing data.
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Alert, AlertStatus
from sqlalchemy import text

def migrate_status_to_int():
    """Convert Chinese status strings to integers in the database."""
    app = create_app()

    with app.app_context():
        # Check current status values
        print("=== Before Migration ===")
        result = db.session.query(Alert.status, db.func.count(Alert.alert_id)).group_by(Alert.status).all()
        for r in result:
            print(f"Status: {r[0]!r} (type: {type(r[0]).__name__}), Count: {r[1]}")

        # Mapping from Chinese text to integer
        status_map = {
            '待分析': AlertStatus.PENDING.value,      # 1
            '分析中': AlertStatus.ANALYZING.value,    # 2
            '已分析': AlertStatus.ANALYZED.value,     # 3
            '处置中': AlertStatus.PROCESSING.value,   # 4
            '已处置': AlertStatus.PROCESSED.value     # 5
        }

        # Check if migration is needed
        needs_migration = False
        for status_val, _ in result:
            if isinstance(status_val, str):
                needs_migration = True
                break

        if not needs_migration:
            print("\n=== No Migration Needed ===")
            print("All status values are already integers.")
            return

        # Perform migration
        print("\n=== Migrating Status Values ===")
        for chinese_text, int_value in status_map.items():
            # Use raw SQL for type-safe update
            updated = db.session.execute(
                text("UPDATE alerts SET status = :int_val WHERE status = :chinese_val"),
                {"int_val": int_value, "chinese_val": chinese_text}
            )
            if updated.rowcount > 0:
                print(f"Updated {updated.rowcount} rows: '{chinese_text}' -> {int_value}")

        db.session.commit()

        # Verify migration
        print("\n=== After Migration ===")
        result = db.session.query(Alert.status, db.func.count(Alert.alert_id)).group_by(Alert.status).all()
        for r in result:
            label = AlertStatus.get_label(r[0])
            print(f"Status: {r[0]} ({label}), Count: {r[1]}")

        print("\n=== Migration Complete ===")

if __name__ == '__main__':
    migrate_status_to_int()
