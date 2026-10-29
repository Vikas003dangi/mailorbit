import re

with open('B:/mailorbit/scripts/original_full_requirements_prompt.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Pattern for requirement IDs like A1, B2, K3, etc.
# Requirements start with [A-Z][0-9]+ followed by whitespace and description
lines = text.splitlines()
reqs = []
current_id = None
current_desc = []

pattern = re.compile(r'^([A-Z][0-9]+)\s+(.*)')

for line in lines:
    m = pattern.match(line.strip())
    if m:
        if current_id:
            reqs.append((current_id, " ".join(current_desc).strip()))
        current_id = m.group(1)
        current_desc = [m.group(2)]
    elif current_id:
        if line.strip().startswith('===') or line.strip().startswith('---'):
            reqs.append((current_id, " ".join(current_desc).strip()))
            current_id = None
            current_desc = []
        elif line.strip():
            current_desc.append(line.strip())

if current_id:
    reqs.append((current_id, " ".join(current_desc).strip()))

print(f"Total extracted requirement IDs: {len(reqs)}")
for r in reqs:
    print(f"{r[0]}: {r[1][:80]}")
