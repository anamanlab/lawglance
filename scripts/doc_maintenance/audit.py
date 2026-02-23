import os
import subprocess
from datetime import datetime
import re

def get_git_last_commit_date(file_path):
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ai', file_path],
            capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            return datetime.fromisoformat(result.stdout.strip())
    except Exception:
        pass
    return None

def analyze_file(file_path, config):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    word_count = len(re.findall(r'\w+', content))
    last_commit = get_git_last_commit_date(file_path)
    
    issues = []
    if word_count < config.get('quality_thresholds', {}).get('min_word_count', 50):
        issues.append(f"Low word count: {word_count}")

    if last_commit:
        days_since = (datetime.now().astimezone() - last_commit).days
        if days_since > config.get('quality_thresholds', {}).get('max_freshness_days', 90):
            issues.append(f"Content is stale: {days_since} days old")

    todos = re.findall(r'(TODO|FIXME):?\s*(.*)', content, re.IGNORECASE)
    
    return {
        'file': file_path,
        'word_count': word_count,
        'last_commit': last_commit,
        'issues': issues,
        'todos': [t[1] for t in todos]
    }

def discover_files(root_dir, exclude_dirs):
    docs = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith(('.md', '.mdx')):
                docs.append(os.path.join(root, file))
    return docs

if __name__ == "__main__":
    # Internal test or minimal CLI
    import yaml
    with open('scripts/doc_maintenance/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    files = discover_files(config['root_docs'], config['exclude_dirs'])
    for f in files:
        print(analyze_file(f, config))
