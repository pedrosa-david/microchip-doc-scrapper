import os
import json
from datetime import datetime

def generate_section_markdown(section, level=1, parent_num=''):
    """Generate Markdown for a section and its subsections recursively."""
    md = []
    
    # Get section number if available
    section_num = ''
    if parent_num and section.get('heading', '').endswith('Function'):
        # This is a function subsection
        function_name = section['heading'].replace(' Function', '')
        section_num = f"{parent_num}.{function_name}"
    
    # Add section heading with number if available
    heading = section['heading']
    if section_num:
        md.append(f"{'#' * level} {section_num}\n")
    else:
        md.append(f"{'#' * level} {heading}\n")
    
    # Add function signature if available
    if section.get('function_info', {}).get('signature'):
        md.append("```C")
        md.append(section['function_info']['signature'])
        md.append("```\n")
    
    # Add section content
    for content in section.get('content', []):
        md.append(f"{content}\n\n")
    
    # Add function information if available
    function_info = section.get('function_info', {})
    if function_info:
        if function_info.get('description'):
            md.append("### Description\n")
            md.append(f"{function_info['description']}\n\n")
        
        if function_info.get('precondition'):
            md.append("### Precondition\n")
            md.append(f"{function_info['precondition']}\n\n")
        
        if function_info.get('parameters'):
            md.append("### Parameters\n")
            md.append("| Parameter | Description |")
            md.append("|-----------|-------------|")
            for param in function_info['parameters']:
                md.append(f"| {param['name']} | {param['description']} |")
            md.append("\n")
        
        if function_info.get('returns'):
            md.append("### Returns\n")
            md.append(f"{function_info['returns']}\n\n")
        
        if function_info.get('example'):
            md.append("### Example\n")
            md.append("```C")
            md.append(function_info['example'])
            md.append("```\n")
        
        if function_info.get('remarks'):
            md.append("### Remarks\n")
            md.append(f"{function_info['remarks']}\n\n")
    
    # Add section code blocks
    for code_block in section.get('code', []):
        md.append(f"```{code_block.get('language', 'C')}")
        md.append(code_block['code'])
        md.append("```\n")
    
    # Add section tables
    for table in section.get('tables', []):
        if table.get('headers'):
            # Add headers
            md.append('| ' + ' | '.join(table['headers']) + ' |')
            # Add separator
            md.append('| ' + ' | '.join(['---' for _ in table['headers']]) + ' |')
        # Add rows
        for row in table.get('rows', []):
            md.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')
        md.append('\n')
    
    # Add section lists
    for list_items in section.get('lists', []):
        for item in list_items:
            md.append(f"- {item}")
        md.append('\n')
    
    # Add subsections recursively
    for i, subsection in enumerate(section.get('subsections', []), 1):
        # If this is a main section (level 1), pass its number to subsections
        if level == 1 and heading.startswith('2.'):
            section_base = heading.split(' ')[0]  # Get the "2.X" part
            md.append(generate_section_markdown(subsection, level + 1, section_base))
        else:
            md.append(generate_section_markdown(subsection, level + 1, section_num))
    
    return '\n'.join(md)

def convert_json_to_markdown(json_file, output_md):
    """Convert a JSON file to Markdown."""
    # Read JSON content
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # Generate markdown content
    md_content = []
    
    # Add title and metadata
    title = json_data.get('title') or json_data.get('content', {}).get('title') or os.path.splitext(os.path.basename(json_file))[0]
    md_content.append(f"# {title}\n")
    md_content.append(f"_Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
    md_content.append(f"_Source: {json_data.get('url', 'Not specified')}_\n\n")
    
    # Add content sections
    for section in json_data.get('content', {}).get('sections', []):
        md_content.append(generate_section_markdown(section))
    
    # Write to file
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_content))
    print(f"Markdown file created successfully: {output_md}")

def convert_all_json_to_markdown(input_dir, output_dir):
    """Convert all JSON files in a directory to Markdown."""
    os.makedirs(output_dir, exist_ok=True)
    
    for filename in os.listdir(input_dir):
        if filename.endswith('.json') and filename != 'requests_log.json':
            json_path = os.path.join(input_dir, filename)
            md_name = filename.replace('.json', '.md')
            md_path = os.path.join(output_dir, md_name)
            
            print(f"Converting {filename} to Markdown...")
            convert_json_to_markdown(json_path, md_path)

if __name__ == "__main__":
    # Convert all JSON files in scraped_content to Markdown
    convert_all_json_to_markdown('scraped_content', 'markdown_output') 