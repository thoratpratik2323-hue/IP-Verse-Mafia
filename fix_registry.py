import re

def fix_tool_registry():
    with open('core/tool_registry.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    def repl(m):
        old_type = m.group(1)
        if '|' in old_type:
            return f'"type": "STRING", "description": "Action: {old_type}"'
        return m.group(0)
        
    new_content = re.sub(r'"type":\s*"([^"]+)"', repl, content)
    
    with open('core/tool_registry.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print("Fixed!")

if __name__ == '__main__':
    fix_tool_registry()
