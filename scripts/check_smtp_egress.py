#!/usr/bin/env python3
"""
MailOrbit Network Egress Diagnostic Script

Performs 3 critical network egress checks:
1. TCP connectivity to smtp.gmail.com:587 (standard submission port)
2. TCP connectivity to script.google.com:443 (Google Apps Script HTTPS port)
3. HTTPS GET to https://script.google.com (testing TLS handshake and HTTP layer)

Note: A local PASS on port 587 does NOT prove anything for Render Free Tier,
which silently blocks outbound port 587 traffic. Render free tier relies on
the Google Apps Script relay over port 443.
"""

import socket
import ssl
import sys
import urllib.error
import urllib.request


def check_tcp(host: str, port: int, timeout: float = 5.0) -> tuple[bool, str]:
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


def check_https_get(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """
    Test real HTTPS GET request.
    Any HTTP response code (including 200, 302, 401, 404, 405) proves the HTTPS
    connection was established and handled by the remote server.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MailOrbit-Egress-Check/1.0"},
    )
    # Default ssl context verifies certificates
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            return True, f"HTTP {response.getcode()} ({response.reason})"
    except urllib.error.HTTPError as e:
        # HTTP response received, connection succeeded!
        return True, f"HTTP {e.code} ({e.reason}) - Connection succeeded"
    except urllib.error.URLError as e:
        return False, f"URL error: {e.reason}"
    except socket.timeout:
        return False, f"Request timed out ({timeout}s)"
    except Exception as e:
        return False, str(e)


def run_all_checks() -> dict:
    results = {}

    print("==================================================")
    print("           MailOrbit Egress Diagnostics           ")
    print("==================================================")
    print("NOTE: Local PASS on port 587 does NOT mean Render Free will pass.")
    print("Render Free Tier blocks outbound port 587 (silent drop/timeout).")
    print("Google Apps Script relay over port 443 is required on Render Free.")
    print("--------------------------------------------------")

    # 1. TCP smtp.gmail.com:587
    ok_587, msg_587 = check_tcp("smtp.gmail.com", 587)
    res_587 = "PASS" if ok_587 else "FAIL"
    print(f"1. TCP smtp.gmail.com:587         : [{res_587}] - {msg_587}")
    results["smtp_587"] = {"status": res_587, "detail": msg_587}

    # 2. TCP script.google.com:443
    ok_443, msg_443 = check_tcp("script.google.com", 443)
    res_443 = "PASS" if ok_443 else "FAIL"
    print(f"2. TCP script.google.com:443       : [{res_443}] - {msg_443}")
    results["script_tcp_443"] = {"status": res_443, "detail": msg_443}

    # 3. HTTPS GET https://script.google.com
    ok_https, msg_https = check_https_get("https://script.google.com")
    res_https = "PASS" if ok_https else "FAIL"
    print(f"3. HTTPS GET script.google.com    : [{res_https}] - {msg_https}")
    results["script_https_get"] = {"status": res_https, "detail": msg_https}

    print("==================================================")
    return results


if __name__ == "__main__":
    results = run_all_checks()
    # Exit 0 if script.google.com works (relay dependency)
    relay_ok = (results["script_tcp_443"]["status"] == "PASS" and 
                results["script_https_get"]["status"] == "PASS")
    sys.exit(0 if relay_ok else 1)

