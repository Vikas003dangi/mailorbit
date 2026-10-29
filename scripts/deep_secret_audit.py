import subprocess
import re

def audit_git_history():
    # Get all commit hashes
    res = subprocess.run(["git", "rev-list", "--all"], cwd=r"B:\mailorbit", capture_output=True, text=True)
    commits = res.stdout.strip().splitlines()
    print(f"Total commits in history: {len(commits)}")

    patterns = {
        "Google App Password": re.compile(r'\b[a-z]{4}\s[a-z]{4}\s[a-z]{4}\s[a-z]{4}\b|[a-z]{16}'),
        "Apps Script Web App URL": re.compile(r'https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec'),
        "Encryption Master Key": re.compile(r'k9\+F2L6qW4mP0sU8yX1zB7cE3gH5jN9rT2vY4aC6eI8='),
        "Brevo Key": re.compile(r'xkeysib-[a-zA-Z0-9]{64}'),
        "Gemini Key": re.compile(r'AIzaSy[A-Za-z0-9_-]{33}'),
        "Cloudinary URL": re.compile(r'cloudinary://[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+'),
        "Database URL": re.compile(r'postgres(?:ql)?://[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+'),
        "Tick Secret Value": re.compile(r'(?:TICK_SECRET|X-Tick-Secret)[=:\s]+["\']?([a-zA-Z0-9_-]{16,})["\']?')
    }

    findings = []

    # Get file list for each commit
    for c in commits:
        diff_res = subprocess.run(["git", "show", "--name-only", "--oneline", c], cwd=r"B:\mailorbit", capture_output=True, text=True)
        # Check diff content
        full_show = subprocess.run(["git", "show", c], cwd=r"B:\mailorbit", capture_output=True, text=True, errors="ignore")
        content = full_show.stdout

        for name, pat in patterns.items():
            matches = pat.findall(content)
            if matches:
                # filter out obvious false positives like test strings, placeholders
                filtered = []
                for m in matches:
                    val = m if isinstance(m, str) else m[0]
                    if any(dummy in val.lower() for dummy in ["placeholder", "example", "my-secret-token", "akfycb_sample", "replace-with", "dummy"]):
                        continue
                    filtered.append(val)
                if filtered:
                    findings.append({
                        "commit": c[:7],
                        "type": name,
                        "count": len(filtered),
                        "sample_masked": filtered[0][:4] + "..." + filtered[0][-4:] if len(filtered[0]) > 8 else "***"
                    })

    print(f"Total findings: {len(findings)}")
    for f in findings:
        print(f"Commit: {f['commit']} | Type: {f['type']} | Count: {f['count']} | Masked: {f['sample_masked']}")

if __name__ == "__main__":
    audit_git_history()
