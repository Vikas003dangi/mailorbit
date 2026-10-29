#!/usr/bin/env python3
"""
MailOrbit Staged File Secret Scanner.
Checks git staged changes for API keys, passwords, and tokens.
Exits with 1 if potential secrets are found.
"""
import subprocess
import sys
import re

PATTERNS = [
    ("Google API / Gemini Key", re.compile(r"AIza[0-9A-Za-z-_]{35}")),
    ("Brevo API Key", re.compile(r"xkeysib-[a-zA-Z0-9]{64,}")),
    ("Generic Private Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS Access Key", re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}")),
    ("High-Entropy Secret / Password Pattern", re.compile(r"""(?:api[_-]?key|secret|token|password|auth_token)\s*[:=]\s*['\"][a-zA-Z0-9_\-+=/]{20,}['\"]""", re.IGNORECASE)),
]

def main():
    try:
        diff_proc = subprocess.run(
            ["git", "diff", "--cached", "-U0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as e:
        print(f"Failed to inspect git diff: {e}")
        return 0

    findings = []
    current_file = "unknown"

    for line in diff_proc.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:].strip()
            # Ignore test mock tokens and example configs
            if "test_" in current_file or "example" in current_file.lower():
                continue
            for name, pattern in PATTERNS:
                if pattern.search(added_content):
                    findings.append((current_file, name))

    if findings:
        print("\n" + "!" * 70)
        print("SECURITY ALERT: Potential secrets detected in staged commit:")
        for file_path, secret_type in findings:
            print(f"  - [{secret_type}] in {file_path}")
        print("Commit aborted. Remove or mask the credentials before proceeding.")
        print("!" * 70 + "\n")
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
