import os
import shutil
from datetime import datetime
import re

def cleanup_directories():
    """Clean up the output directories."""
    directories = ['scraped_content', 'markdown_output']
    for directory in directories:
        if os.path.exists(directory):
            print(f"Cleaning up {directory}...")
            shutil.rmtree(directory)
        os.makedirs(directory)
    print("Directories cleaned and recreated.")

def sanitize_filename(filename):
    """Create a clean, GitHub-friendly filename."""
    # Remove spaces and special characters
    clean = filename.replace(' ', '-')
    clean = re.sub(r'[<>:"/\\|?*\n\r\t()]', '', clean)
    return clean

def create_github_links(sections_by_number):
    """Create GitHub-friendly links for each section."""
    links = {}
    for section_num, section in sections_by_number.items():
        clean_filename = section['clean_filename']  # Use clean filename for link
        title = section['title']
        # Create GitHub-friendly link
        links[section_num] = f"[{section_num} {title}]({clean_filename})"
    return links

def merge_markdown_files():
    """Create hierarchical markdown files for GitHub gist."""
    sections_by_number = {}
    
    # First pass: collect all sections and organize them hierarchically
    for filename in sorted(os.listdir('markdown_output')):
        if filename.endswith('.md') and filename != 'main.md':
            # Extract section number and title
            clean_name = filename.replace('.md', '')
            section_parts = clean_name.split('_', 1)
            if len(section_parts) > 1:
                section_num = section_parts[0]
                section_title = section_parts[1]
                
                # Create clean filename
                clean_filename = sanitize_filename(f"{section_num}_{section_title}.md")
                
                # Split section number into parts (e.g., "2.1" -> ["2", "1"])
                num_parts = section_num.split('.')
                
                # Store section info
                sections_by_number[section_num] = {
                    'title': section_title,
                    'level': len(num_parts),
                    'parent': '.'.join(num_parts[:-1]) if len(num_parts) > 1 else None,
                    'filename': filename,
                    'clean_filename': clean_filename,  # Store clean filename
                    'subsections': []
                }
    
    # Build parent-child relationships
    for section_num, section in sections_by_number.items():
        if section['parent'] in sections_by_number:
            sections_by_number[section['parent']]['subsections'].append(section_num)
    
    # Create GitHub-friendly links
    github_links = create_github_links(sections_by_number)
    
    # Create main.md with hierarchical links
    main_content = []
    main_content.append("# Microchip API Documentation")
    main_content.append(f"_Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
    main_content.append("## Table of Contents\n")
    
    def add_to_main_toc(section_num, indent=0):
        if section_num in sections_by_number:
            section = sections_by_number[section_num]
            # Add newline before each top-level section
            if indent == 0:
                main_content.append("")
            # Add indented link with proper markdown list formatting
            main_content.append(f"{'  ' * indent}* {github_links[section_num]}")
            
            # Add subsections with proper indentation
            if section['subsections']:
                # Add a newline before subsections if there are many
                if len(section['subsections']) > 5:
                    main_content.append("")
                for subsection in sorted(section['subsections']):
                    add_to_main_toc(subsection, indent + 1)
                # Add a newline after subsections if there are many
                if len(section['subsections']) > 5:
                    main_content.append("")
    
    # Add top-level sections to main.md
    top_level_sections = sorted([num for num in sections_by_number.keys() 
                               if len(num.split('.')) == 2])  # e.g., "2.1", "2.2", etc.
    
    for section in top_level_sections:
        add_to_main_toc(section)
    
    # Write main.md
    with open(os.path.join('markdown_output', 'main.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(main_content))
    
    # Update individual markdown files with navigation links and rename to clean filenames
    for section_num, section in sections_by_number.items():
        old_filepath = os.path.join('markdown_output', section['filename'])
        new_filepath = os.path.join('markdown_output', section['clean_filename'])
        
        if os.path.exists(old_filepath):
            with open(old_filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                content_lines = content.split('\n')
            
            # Add navigation links at the top
            nav_links = []
            nav_links.append("← [Back to main](main.md)")
            
            # Add parent link if exists
            if section['parent'] in sections_by_number:
                parent = sections_by_number[section['parent']]
                nav_links.append(f"↑ [Up to {section['parent']}]({parent['clean_filename']})")
            
            # Add subsection links if any
            if section['subsections']:
                nav_links.append("\nSubsections:")
                for subsection in sorted(section['subsections']):
                    nav_links.append(f"- {github_links[subsection]}")
            
            # Combine navigation and content
            new_content = []
            new_content.extend(nav_links)
            new_content.append("\n---\n")
            
            # Add original content (skipping original metadata)
            content_start = False
            for line in content_lines:
                if line.startswith('# '):
                    content_start = True
                if content_start:
                    new_content.append(line)
            
            # Write updated content to new clean filename
            with open(new_filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_content))
            
            # Remove old file if it's different from the new one
            if old_filepath != new_filepath:
                os.remove(old_filepath)
    
    print("Created GitHub-friendly markdown files with navigation links")

def main():
    # Clean up directories
    cleanup_directories()
    
    # Run the scraper
    print("Running scraper...")
    os.system('python microchip_scraper.py')
    
    # Run the markdown converter
    print("\nConverting to markdown...")
    os.system('python json_to_markdown.py')
    
    # Create GitHub-friendly markdown files
    print("\nCreating GitHub-friendly markdown files...")
    merge_markdown_files()
    
    print("\nProcess completed successfully!")

if __name__ == "__main__":
    main() 