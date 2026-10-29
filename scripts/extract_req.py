import json

with open(r'C:\Users\vikas\.gemini\antigravity\brain\8bd5c406-decd-4db5-8f71-45e112ebe67c\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if '"step_index": 3212' in line or '"step_index":3212' in line:
            obj = json.loads(line)
            content = obj.get('content', '')
            with open('B:/mailorbit/scripts/original_full_requirements_prompt.txt', 'w', encoding='utf-8') as out:
                out.write(content)
            print('Extracted full prompt, length:', len(content))
            break
