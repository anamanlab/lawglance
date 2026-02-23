import re
import os
import requests

def extract_links(content):
    # Markdown link pattern [text](url)
    md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    # Generic URLs http/https
    raw_urls = re.findall(r'https?://[^\s)\]]+', content)
    return md_links, raw_urls

def validate_relative_link(base_path, rel_link):
    if rel_link.startswith(('http', 'mailto:', '#')):
        return True
    
    # Clean up anchors
    clean_link = rel_link.split('#')[0]
    if not clean_link:
        return True
        
    abs_path = os.path.normpath(os.path.join(os.path.dirname(base_path), clean_link))
    return os.path.exists(abs_path)

def validate_external_link(url, timeout=5):
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code < 400
    except Exception:
        return False

def check_images(content, base_path):
    img_refs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)
    results = []
    for alt, src in img_refs:
        if not alt:
            results.append(f"Missing alt text for image: {src}")
        if not src.startswith('http'):
            abs_path = os.path.normpath(os.path.join(os.path.dirname(base_path), src))
            if not os.path.exists(abs_path):
                results.append(f"Broken local image reference: {src}")
    return results

if __name__ == "__main__":
    # Test stub
    sample = "Check [this](broken.md) and ![img](missing.png) and http://google.com"
    md_l, raw_u = extract_links(sample)
    print(f"MD Links: {md_l}")
    print(f"Raw URLs: {raw_u}")
