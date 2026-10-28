from sqlalchemy import inspect
from apps.api.config import settings
from packages.shared.db import create_db_engine

def test_database_tables_exist():
    engine = create_db_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_tables = ["users", "profiles", "sender_relays", "ai_keys", "jobs", "alembic_version"]
    for table in expected_tables:
        assert table in tables, f"Expected table '{table}' not found in database. Found: {tables}"
