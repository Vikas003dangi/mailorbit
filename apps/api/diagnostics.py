from datetime import datetime, timezone
import socket
import ssl
import urllib.error
import urllib.request
from typing import Dict, Tuple

from packages.shared.models import DiagnosticItem, EgressReport


def check_tcp(host: str, port: int, timeout: float = 5.0) -> Tuple[bool, str]:
    """Test standard TCP connectivity to a host and port."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True, "Connected successfully"
    except socket.timeout:
        return False, f"Connection timed out ({timeout}s)"
    except Exception as e:
        return False, str(e)


def check_https_get(url: str, timeout: float = 5.0) -> Tuple[bool, str]:
    """
    Test real HTTPS GET request.
    Any HTTP status code proves network connectivity, TLS handshake,
    and HTTP layer negotiation succeeded.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MailOrbit-Egress-Check/1.0"},
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            return True, f"HTTP {response.getcode()} ({response.reason})"
    except urllib.error.HTTPError as e:
        return True, f"HTTP {e.code} ({e.reason}) - Connection succeeded"
    except urllib.error.URLError as e:
        return False, f"URL error: {e.reason}"
    except socket.timeout:
        return False, f"Request timed out ({timeout}s)"
    except Exception as e:
        return False, str(e)


def run_egress_check() -> EgressReport:
    """Run all 3 network egress checks and return a structured report."""
    # 1. TCP smtp.gmail.com:587
    ok_587, msg_587 = check_tcp("smtp.gmail.com", 587)
    item_587 = DiagnosticItem(
        status="PASS" if ok_587 else "FAIL",
        detail=msg_587,
    )

    # 2. TCP script.google.com:443
    ok_443, msg_443 = check_tcp("script.google.com", 443)
    item_443 = DiagnosticItem(
        status="PASS" if ok_443 else "FAIL",
        detail=msg_443,
    )

    # 3. HTTPS GET https://script.google.com
    ok_https, msg_https = check_https_get("https://script.google.com")
    item_https = DiagnosticItem(
        status="PASS" if ok_https else "FAIL",
        detail=msg_https,
    )

    relay_ready = (item_443.status == "PASS" and item_https.status == "PASS")
    note = (
        "Render Free Tier blocks outbound TCP on port 587 (expected FAIL). "
        "Outbound email relies on Google Apps Script relay over port 443 (must PASS)."
    )

    return EgressReport(
        server_time=datetime.now(timezone.utc),
        smtp_587=item_587,
        script_tcp_443=item_443,
        script_https_get=item_https,
        relay_ready=relay_ready,
        note=note,
    )
