# Microchip Documentation Scraper and Processor

A tool suite for scraping, processing, and organizing Microchip's online documentation into a navigable, hierarchical markdown structure suitable for GitHub hosting. Version 0.0.1.
This project has been completely coded using cursor and sonnet, including this readme.


## Features

- Asynchronous web scraping using Playwright
- Hierarchical documentation structure
- GitHub-friendly markdown formatting
- Cross-linked navigation between documents
- Clean, SEO-friendly URLs and filenames
- AI-friendly documentation structure

## Components

### 1. Scraper (`microchip_scraper.py`)
- Uses Playwright for async web scraping
- Handles dynamic content expansion
- Extracts structured content including:
  - Function signatures
  - Parameters
  - Return values
  - Code examples
  - Tables and lists
- Parallel processing with controlled concurrency (20 pages at a time)

### 2. JSON to Markdown Converter (`json_to_markdown.py`)
- Converts scraped JSON content to markdown format
- Preserves document structure and hierarchy
- Handles code blocks, tables, and function documentation
- Maintains metadata and relationships

### 3. Documentation Processor (`process_docs.py`)
- Creates hierarchical documentation structure
- Generates clean, GitHub-friendly filenames
- Builds navigation links between documents
- Creates main index with table of contents

## Technical Details

### Scraping Process
1. **Navigation Tree Expansion**
   - Sequential level-by-level expansion
   - DOM state management with timeouts
   - Progress tracking and error handling

2. **Content Extraction**
   - Async page processing with semaphore control
   - Structured JSON output
   - Error resilient with exception handling

3. **Parallel Processing**
   ```python
   async def scrape_pages_in_parallel(self, links, context):
       sem = asyncio.Semaphore(self.max_concurrent_pages)
       tasks = [
           asyncio.create_task(scrape_with_semaphore(link))
           for link in links
       ]
       await asyncio.gather(*tasks)
   ```

### Document Processing

1. **File Organization**
   ```
   markdown_output/
   ├── main.md                     # Main index
   ├── 2.1-Analog-Comparators.md   # Section file
   ├── 2.1.1-Function.md          # Subsection
   └── ...
   ```

2. **Navigation Structure**
   - Back to main index
   - Up to parent section
   - Down to subsections
   - Cross-section references

3. **Clean URLs**
   - Spaces replaced with hyphens
   - Special characters removed
   - SEO-friendly naming

## Usage

1. **Setup**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate # Unix

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Run the Process**
   ```bash
   python process_docs.py
   ```
   This will:
   - Clean up output directories
   - Run the scraper
   - Convert to markdown
   - Generate hierarchical structure

3. **Output**
   - Check `markdown_output/` for the generated files
   - `main.md` is your entry point
   - All files are cross-linked and GitHub-ready

## Requirements

- Python 3.6+
- Playwright
- BeautifulSoup4
- See `requirements.txt` for full list

## Technical Notes

- Uses asyncio for concurrent processing
- Implements rate limiting to prevent server overload
- Handles DOM state management for dynamic content
- Creates AI-friendly documentation structure
- Maintains document hierarchy through clean file naming
- Implements proper error handling and logging

## Output Format

Each markdown file follows this structure:
```markdown
← [Back to main](main.md)
↑ [Up to parent](parent.md)

Subsections:
- [Subsection 1](subsection1.md)
- [Subsection 2](subsection2.md)

---

# Section Title
Content...
```

## Contributing

Feel free to submit issues and enhancement requests! 