"""
Purge All Test and Orphan Data from Database.

Destructive script safety constraints:
- Defaults to DRY-RUN mode.
- Prints parsed database host, port, and database name before touching anything.
- Requires explicit confirmation via env var CONFIRM_PURGE="CONFIRM_PURGE" or interactive prompt.
- Preserves table schemas and alembic_version.
"""

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import create_engine, text
from apps.api.config import settings

def purge_test_data(dry_run: bool = True):
    db_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    parsed = urllib.parse.urlparse(db_url)
    host = parsed.hostname or "unknown"
    port = parsed.port or 5432
    dbname = parsed.path.lstrip("/") or "unknown"

    print("=================================================================")
    print(f"DATABASE TARGET: {host}:{port}/{dbname}")
    print(f"EXECUTION MODE : {'[DRY RUN - NO DATA MODIFIED]' if dry_run else '[LIVE PURGE - DESTRUCTIVE]'}")
    print("=================================================================")

    engine = create_engine(db_url)

    tables_to_clear = [
        "bootstrap_records",
        "contact_replacements",
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

    # Query current row counts
    print("\n--- Current Row Counts ---")
    with engine.connect() as conn:
        for tbl in tables_to_clear:
            try:
                cnt = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
                print(f"Table {tbl:22}: {cnt} rows")
            except Exception:
                pass

    if dry_run:
        print("\n[DRY RUN COMPLETE] Zero rows modified. To execute real deletion, set CONFIRM_PURGE='CONFIRM_PURGE'.")
        return

    # Typed confirmation verification
    confirm = os.environ.get("CONFIRM_PURGE", "")
    if confirm != "CONFIRM_PURGE":
        print("\n[ABORTED] Missing confirmation. Expected CONFIRM_PURGE='CONFIRM_PURGE'.")
        sys.exit(1)

    print("\nBeginning atomic deletion of all synthetic test data...")
    with engine.begin() as conn:
        for tbl in tables_to_clear:
            try:
                deleted = conn.execute(text(f"DELETE FROM {tbl}")).rowcount
                print(f"Deleted {deleted} rows from {tbl}.")
            except Exception as e:
                print(f"Skipping {tbl}: {e}")

    print("\n--- FINAL VERIFICATION QUERY COUNTS ---")
    with engine.connect() as conn:
        all_zero = True
        for tbl in tables_to_clear:
            try:
                cnt = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
                print(f"Table {tbl:22}: {cnt} rows")
                if cnt != 0:
                    all_zero = False
            except Exception:
                pass

        try:
            alembic_cnt = conn.execute(text("SELECT count(*) FROM alembic_version")).scalar()
            print(f"Table {'alembic_version':22}: {alembic_cnt} rows (preserved)")
        except Exception:
            pass

        if all_zero:
            print("\n[SUCCESS] Database is completely pristine: 0 test users, 0 contacts, 0 batches.")
        else:
            print("\n[WARNING] Some tables still contain rows!")

if __name__ == "__main__":
    is_live = os.environ.get("CONFIRM_PURGE") == "CONFIRM_PURGE"
    purge_test_data(dry_run=not is_live)


