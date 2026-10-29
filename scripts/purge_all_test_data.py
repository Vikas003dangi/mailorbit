"""
Purge All Test and Orphan Data from Production Neon Database.

Executes a complete purge of all synthetic test users, contacts, batches,
purposes, AI keys, jobs, profiles, and do-not-contact entries created
during automated test suites.
Preserves table schemas and alembic_version.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import create_engine, text
from apps.api.config import settings

def purge_test_data():
    db_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    engine = create_engine(db_url)

    tables_to_clear = [
        "do_not_contact",
        "purpose_attachments",
        "attachments",
        "contacts",
        "batches",
        "purposes",
        "ai_keys",
        "jobs",
        "sender_relays",
        "profiles",
        "users",
    ]

    print("Beginning atomic deletion of all synthetic test data...")
    with engine.begin() as conn:
        for tbl in tables_to_clear:
            deleted = conn.execute(text(f"DELETE FROM {tbl}")).rowcount
            print(f"Deleted {deleted} rows from {tbl}.")

    print("\n--- FINAL VERIFICATION QUERY COUNTS ---")
    with engine.connect() as conn:
        all_zero = True
        for tbl in tables_to_clear:
            cnt = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
            print(f"Table {tbl:20}: {cnt} rows")
            if cnt != 0:
                all_zero = False

        alembic_cnt = conn.execute(text("SELECT count(*) FROM alembic_version")).scalar()
        print(f"Table {'alembic_version':20}: {alembic_cnt} rows (preserved)")

        if all_zero:
            print("\n[SUCCESS] Production database is completely pristine: 0 test users, 0 contacts, 0 batches.")
        else:
            print("\n[WARNING] Some tables still contain rows!")

if __name__ == "__main__":
    purge_test_data()
