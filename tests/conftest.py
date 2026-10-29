import pytest
from apps.api.services.rate_limiter import rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter_fixture():
    """Resets in-memory rate limiter history before each test to maintain test isolation."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()
