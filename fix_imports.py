import os, re

def replace_in_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = re.sub(r"import google\.generativeai as genai", "from google import genai", content)
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[fix_imports] Updated {path}")

def main():
    root = r"c:/Users/thora/.gemini/antigravity/scratch/IP Prime"
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith('.py'):
                replace_in_file(os.path.join(dirpath, fn))

if __name__ == '__main__':
    main()
