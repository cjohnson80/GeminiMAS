with open('bin/atlas_core.py', 'r') as f:
    lines = f.readlines()

with open('bin/atlas_core.py', 'w') as f:
    for line in lines:
        if "yield chunk['candidates'][0]['content']['parts'][0]['text']" in line:
            indent = line[:len(line) - len(line.lstrip())]
            f.write(indent + "candidates = chunk.get('candidates', [])\n")
            f.write(indent + "if not candidates: continue\n")
            f.write(indent + "content_dict = candidates[0].get('content', {})\n")
            f.write(indent + "parts = content_dict.get('parts', [])\n")
            f.write(indent + "if not parts: continue\n")
            f.write(indent + "yield parts[0].get('text', '')\n")
        else:
            f.write(line)
print('Defensive parsing patch applied successfully.')
