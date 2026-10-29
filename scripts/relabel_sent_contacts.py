import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import text
from apps.api.config import settings
from packages.shared.db import create_db_engine

engine = create_db_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    res = conn.execute(
        text("UPDATE contacts SET status = 'PENDING', sent_at = NULL, error = NULL WHERE status IN ('SENT', 'DELIVERED')")
    )
    conn.commit()
    print(f"Relabeled {res.rowcount} contacts to PENDING (reset sent_at).")

    check = conn.execute(
        text("SELECT count(id) FROM contacts WHERE status IN ('SENT', 'DELIVERED')")
    ).scalar()
    print(f"VERIFICATION QUERY: Contacts marked SENT or DELIVERED in production DB = {check}")

