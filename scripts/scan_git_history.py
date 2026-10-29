import subprocess
import re

cmd = ["git", "log", "-p", "--all"]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")

patterns = [
    ("Gmail App Password", re.compile(r"zohatqiavvwvygko")),
    ("Postgres Password / DB URL", re.compile(r"postgresql://[^:]+:([^@]+)@")),
    ("Master Encryption Key", re.compile(r"ENCRYPTION_MASTER_KEY\s*=\s*['\"][^'\"]+['\"]")),
    ("Tick Secret", re.compile(r"sec_orbit_[a-zA-Z0-9_]+")),
    ("Google API / Gemini Key", re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}")),
    ("Brevo API Key", re.compile(r"xkeysib-[a-zA-Z0-9]+")),
    ("General High-Entropy Secret / Token", re.compile(r"(secret|token|password)\s*[:=]\s*['\"][a-zA-Z0-9_\-+=/]{16,}['\"]", re.IGNORECASE)),
]

findings = []
current_commit = "unknown"
current_file = "unknown"

for line in proc.stdout:
    if line.startswith("commit "):
        current_commit = line.split()[1]
    elif line.startswith("diff --git "):
        parts = line.split()
        if len(parts) >= 4:
            current_file = parts[3].lstrip("b/")
    elif line.startswith("+") and not line.startswith("+++"):
        # Exclude doc/comment lines that are clearly documentation of removal
        for secret_type, pat in patterns:
            if pat.search(line):
                findings.append((current_commit[:8], current_file, secret_type))

unique_findings = sorted(list(set(findings)))
print(f"Total secret occurrences found in git history: {len(unique_findings)}")
for commit, filepath, stype in unique_findings:
    print(f"Commit {commit} | File: {filepath} | Type: {stype}")

