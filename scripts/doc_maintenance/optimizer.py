import re

def generate_toc(content):
    headings = re.findall(r'^(##+)\s+(.*)', content, re.MULTILINE)
    if not headings:
        return ""
        
    toc = ["## Table of Contents\n"]
    for level_str, title in headings:
        level = len(level_str) - 2 # Start from H2
        indent = "  " * level
        anchor = title.lower().replace(" ", "-").replace(".", "")
        toc.append(f"{indent}- [{title}](#{anchor})")
        
    return "\n".join(toc) + "\n"

def inject_toc(content):
    if "## Table of Contents" in content:
        # Replace existing TOC
        new_toc = generate_toc(content)
        return re.sub(r'## Table of Contents.*?\n\n', new_toc + "\n", content, flags=re.DOTALL)
    
    # Inject after H1
    h1_match = re.search(r'^#\s+.*?\n', content, re.MULTILINE)
    if h1_match:
        toc = generate_toc(content)
        insert_point = h1_match.end()
        return content[:insert_point] + "\n" + toc + content[insert_point:]
    
    return content

if __name__ == "__main__":
    sample = "# Title\n\n## Section 1\n### Sub 1\n## Section 2"
    print(inject_toc(sample))
