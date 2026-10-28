import logging
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger("mailorbit.db")

# Fallback DNS resolution for local environments where ISP DNS blocks/refuses cloud subdomains
try:
    import dns.resolver
    _orig_getaddrinfo = socket.getaddrinfo

    def _safe_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        try:
            return _orig_getaddrinfo(host, port, family, type, proto, flags)
        except Exception:
            if isinstance(host, str) and ("neon.tech" in host or "onrender.com" in host):
                try:
                    res = dns.resolver.Resolver()
                    res.nameservers = ["8.8.8.8", "1.1.1.1"]
                    ans = res.resolve(host, "A")
                    return _orig_getaddrinfo(ans[0].address, port, family, type, proto, flags)
                except Exception:
                    pass
            raise

    socket.getaddrinfo = _safe_getaddrinfo
except ImportError:
    pass

Base = declarative_base()


def get_db_url(raw_url: str) -> str:
    """Ensures psycopg (v3) driver prefix for standard postgresql URLs."""
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    return raw_url


def create_db_engine(db_url: str):
    """
    Creates SQLAlchemy engine configured for serverless PostgreSQL (Neon)
    with pre-ping validation and short connection recycle time to support auto-suspend.
    """
    normalized_url = get_db_url(db_url)
    return create_engine(
        normalized_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
    )


def create_session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

