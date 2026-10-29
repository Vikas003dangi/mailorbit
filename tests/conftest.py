import base64
import os
import secrets
import urllib.parse
import pytest

if not os.environ.get("ENCRYPTION_MASTER_KEY"):
    os.environ["ENCRYPTION_MASTER_KEY"] = base64.b64encode(secrets.token_bytes(32)).decode()
if not os.environ.get("TICK_SECRET"):
    os.environ["TICK_SECRET"] = "pytest-mock-tick-secret-9999"
if not os.environ.get("ADMIN_EMAILS"):
    os.environ["ADMIN_EMAILS"] = '["admin@test.local"]'

from apps.api.config import settings
from apps.api.services.rate_limiter import rate_limiter


@pytest.fixture(scope="session", autouse=True)
def guard_against_production_database():
    """
    STRICT SAFETY GUARD:
    Refuses to execute the test suite unless DATABASE_URL points strictly
    to a local or isolated test database. Aborts if host is external (e.g. Neon, AWS).
    """
    db_url = (settings.DATABASE_URL or "").lower()
    parsed = urllib.parse.urlparse(db_url)
    hostname = (parsed.hostname or "").lower()

    # Explicit blacklisted production keywords
    if any(bad in hostname for bad in ("neon.tech", "aws", "rds", "pooler")):
        raise RuntimeError(
            f"FATAL SAFETY ABORT: Test suite attempted to run against remote/production database!\n"
            f"Host detected: '{hostname}'.\n"
            f"Refusing to execute tests to protect production data."
        )

    # Allowed local hosts
    is_local = (
        db_url.startswith("sqlite")
        or hostname in ("localhost", "127.0.0.1", "::1", "test-postgres")
        or "test" in hostname
        or "test" in (parsed.path or "").lower()
    )

    if not is_local:
        raise RuntimeError(
            f"FATAL SAFETY ABORT: Test suite attempted to run against non-local host: '{hostname}'.\n"
            f"Tests must run strictly against localhost, 127.0.0.1, or a local test database."
        )

    from packages.shared.schema import Base
    import apps.api.dependencies
    from sqlalchemy import text
    Base.metadata.create_all(bind=apps.api.dependencies.engine)
    with apps.api.dependencies.engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))


@pytest.fixture(autouse=True)
def reset_rate_limiter_fixture():
    """Resets in-memory rate limiter history before each test to maintain test isolation."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture(autouse=True)
def clean_database_between_tests():
    """Cleans database tables between tests to ensure test isolation."""
    yield
    from packages.shared.schema import Base
    import apps.api.dependencies
    try:
        with apps.api.dependencies.engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
    except Exception:
        pass

