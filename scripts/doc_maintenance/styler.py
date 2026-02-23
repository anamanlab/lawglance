import re

def check_heading_hierarchy(content):
    headings = re.findall(r'^(#+)\s', content, re.MULTILINE)
    levels = [len(h) for h in headings]
    issues = []
    
    if not levels:
        return issues
        
    if levels[0] != 1:
        issues.append("Document does not start with H1")
        
    for i in range(1, len(levels)):
        if levels[i] > levels[i-1] + 1:
            issues.append(f"Heading skip: H{levels[i-1]} to H{levels[i]}")
            
    return issues

def check_code_blocks(content):
    # Find all lines starting with triple backticks
    # We track opening/closing state to only flag opening blocks without language
    lines = content.split('\n')
    issues = 0
    in_block = False
    
    for line in lines:
        match = re.match(r'^\s*```(.*)', line)
        if match:
            if not in_block:
                # This is an opening block
                lang = match.group(1).strip()
                if not lang:
                    issues += 1
                in_block = True
            else:
                # This is a closing block
                in_block = False
                
    if issues:
        return [f"Found {issues} code blocks without language specification"]
    return []

def validate_style(content, config):
    issues = []
    if config.get('style_rules', {}).get('require_h1'):
        issues.extend(check_heading_hierarchy(content))
    if config.get('style_rules', {}).get('require_code_lang'):
        issues.extend(check_code_blocks(content))
    return issues
