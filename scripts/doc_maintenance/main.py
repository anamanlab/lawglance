import yaml
import os
import argparse
from audit import discover_files, analyze_file
from validator import extract_links, validate_relative_link, validate_external_link, check_images
from styler import validate_style
from optimizer import inject_toc

def run_main(config_path, dry_run=False, fix=False):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    docs = discover_files(config['root_docs'], config['exclude_dirs'])
    all_results = []
    
    for doc in docs:
        print(f"Auditing: {doc}")
        result = analyze_file(doc, config)
        
        with open(doc, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Link & Reference Validation
        md_links, raw_urls = extract_links(content)
        link_issues = []
        for text, link in md_links:
            if not validate_relative_link(doc, link):
                link_issues.append(f"Broken relative link: {link}")
        
        # Image Validation
        img_issues = check_images(content, doc)
        
        # Style Validation
        style_issues = validate_style(content, config)
        
        result['issues'].extend(link_issues)
        result['issues'].extend(img_issues)
        result['issues'].extend(style_issues)
        
        all_results.append(result)
        
        if fix and not dry_run:
            new_content = inject_toc(content)
            if new_content != content:
                with open(doc, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  [FIXED] Updated TOC in {doc}")

    generate_report(all_results, config['report_file'])

def generate_report(results, report_path):
    report = ["# Documentation Quality Audit Report\n"]
    report.append(f"Generated on: {os.uname().nodename} at {os.popen('date').read().strip()}\n")
    
    total_files = len(results)
    files_with_issues = len([r for r in results if r['issues']])
    
    report.append("## Summary\n")
    report.append(f"- Total Documentation Files: {total_files}")
    report.append(f"- Files with Issues: {files_with_issues}")
    report.append(f"- Documentation Health Score: {int((1 - files_with_issues/total_files)*100) if total_files > 0 else 100}%\n")
    
    report.append("## Detailed Findings\n")
    for r in results:
        status = "❌" if r['issues'] else "✅"
        report.append(f"### {status} {os.path.basename(r['file'])}\n")
        report.append(f"- Path: `{r['file']}`")
        report.append(f"- Word Count: {r['word_count']}")
        
        if r['issues']:
            report.append("- Issues:")
            for issue in r['issues']:
                report.append(f"  - {issue}")
        
        if r['todos']:
            report.append("- TODOs:")
            for todo in r['todos']:
                report.append(f"  - {todo}")
        report.append("\n")
        
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    print(f"Report generated: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Documentation Maintenance System")
    parser.add_argument("--config", default="scripts/doc_maintenance/config.yaml", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Don't make any changes")
    parser.add_argument("--fix", action="store_true", help="Automatically fix issues (e.g., TOC)")
    
    args = parser.parse_args()
    run_main(args.config, args.dry_run, args.fix)
