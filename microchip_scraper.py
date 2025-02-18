import os
from datetime import datetime
import logging
from playwright.sync_api import sync_playwright, Route, Request
from bs4 import BeautifulSoup
import json
import re
import traceback
import asyncio
from playwright.async_api import async_playwright

class MicrochipScraper:
    def __init__(self):
        self.base_url = "https://onlinedocs.microchip.com/oxy/GUID-450989FA-38E4-4D68-AB61-15ADB29AD718-en-US-5"
        self.target_page = "GUID-D5DEA95C-53C5-4FE8-BEF6-4379A8FE53C6.html"
        self.output_dir = "scraped_content"
        self.requests_log = []
        self.setup_logging()  # Set up logging first
        self.cleanup_output_dir()  # Then clean up
        os.makedirs(self.output_dir, exist_ok=True)
        self.max_concurrent_pages = 20  # Increased from 5 to 20

    def sanitize_filename(self, filename):
        """Convert a string into a valid filename."""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', filename)
        # Remove any leading/trailing periods or spaces
        filename = filename.strip('. ')
        # Ensure it's not empty
        if not filename:
            filename = 'unnamed'
        return filename

    def cleanup_output_dir(self):
        """Remove all files from the output directory if it exists."""
        if os.path.exists(self.output_dir):
            self.logger.info(f"Cleaning up {self.output_dir} directory...")
            for filename in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        os.rmdir(file_path)
                except Exception as e:
                    self.logger.error(f"Error deleting {file_path}: {str(e)}")
            self.logger.info("Cleanup completed")

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    async def log_request(self, route, request):
        self.requests_log.append({
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "timestamp": datetime.now().isoformat()
        })
        await route.continue_()

    def save_requests_log(self):
        with open(os.path.join(self.output_dir, "requests_log.json"), "w") as f:
            json.dump(self.requests_log, f, indent=4)

    def extract_peripheral_links(self, page):
        links = page.query_selector_all('div[data-tocid] a')
        peripheral_links = []
        for link in links:
            href = link.get_attribute('href')
            if href and not href.startswith('http'):
                title = link.text_content().strip()
                if title.startswith('2.'):  # Only get peripheral documentation links
                    peripheral_links.append({
                        'href': href,
                        'title': title
                    })
        return peripheral_links

    def clean_text(self, text):
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_table_data(self, table):
        table_data = []
        headers = []
        
        # Extract headers
        header_row = table.find('tr')
        if header_row:
            headers = [self.clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
            
        # Extract rows
        rows = table.find_all('tr')[1:] if headers else table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = [self.clean_text(cell.get_text()) for cell in cells]
            if any(row_data):  # Only add non-empty rows
                if headers:
                    # Create a dictionary if we have headers
                    row_dict = dict(zip(headers, row_data))
                    table_data.append(row_dict)
                else:
                    # Otherwise just add the row data as a list
                    table_data.append(row_data)
                    
        return table_data

    async def scrape_peripheral_page(self, url, title, context):
        """Scrape a single peripheral page using the provided context."""
        try:
            page = await context.new_page()
            await page.goto(url, timeout=10000)  # 10 second timeout
            await page.wait_for_selector('div.body', timeout=5000)  # 5 second timeout
            
            # Extract content from the main topic body
            content = await page.evaluate(r'''() => {
                const content = {};
                
                // Get the main content div
                const mainDiv = document.querySelector('div.body');
                if (!mainDiv) return content;
                
                // Extract title
                const titleElem = document.querySelector('title');
                content.title = titleElem ? titleElem.textContent.trim() : '';
                
                // Extract sections
                content.sections = [];
                const sections = mainDiv.querySelectorAll('*');
                let sectionStack = []; // Stack to track nested sections
                let currentSection = null;
                let functionCounter = 1; // Counter for function sections
                
                function getHeadingLevel(tagName) {
                    return parseInt(tagName.substring(1));
                }
                
                function createSection(heading, level, isFunction = false) {
                    return {
                        heading: heading,
                        level: level,
                        section_number: isFunction ? functionCounter++ : '',
                        content: [],
                        tables: [],
                        lists: [],
                        code: [],
                        function_info: {  // New field for function details
                            signature: '',
                            parameters: [],
                            returns: '',
                            example: '',
                            precondition: '',
                            remarks: '',
                            description: ''
                        },
                        subsections: []
                    };
                }
                
                function isFunctionSignature(text) {
                    // Check if text looks like a C function signature
                    return /^[a-zA-Z_][a-zA-Z0-9_]*\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^{]*\)\s*;?\s*$/.test(text);
                }
                
                function isFunctionSection(heading) {
                    return heading.endsWith('Function') || 
                           heading.includes('Initialize') || 
                           heading.includes('Callback') ||
                           /^[A-Z][a-zA-Z0-9_]*$/.test(heading);
                }
                
                let currentSubsection = '';
                
                for (const elem of sections) {
                    if (elem.tagName.startsWith('H')) {
                        const headingLevel = getHeadingLevel(elem.tagName);
                        const headingText = elem.textContent.trim();
                        
                        if (headingLevel === 3) {
                            // This is a subsection heading (like Description, Parameters, etc.)
                            currentSubsection = headingText.toLowerCase();
                        } else {
                            const isFunction = isFunctionSection(headingText);
                            const newSection = createSection(headingText, headingLevel, isFunction);
                            
                            // Pop sections from stack if they're at the same or higher level
                            while (sectionStack.length > 0 && sectionStack[sectionStack.length - 1].level >= headingLevel) {
                                sectionStack.pop();
                            }
                            
                            if (sectionStack.length === 0) {
                                content.sections.push(newSection);
                            } else {
                                sectionStack[sectionStack.length - 1].subsections.push(newSection);
                            }
                            
                            sectionStack.push(newSection);
                            currentSection = newSection;
                            currentSubsection = '';
                        }
                    } else if (currentSection) {
                        // Add content to current section
                        if (elem.tagName === 'P') {
                            const text = elem.textContent.trim();
                            if (text) {
                                if (currentSubsection === 'description') {
                                    currentSection.function_info.description = text;
                                } else if (currentSubsection === 'precondition') {
                                    currentSection.function_info.precondition = text;
                                } else if (currentSubsection === 'returns') {
                                    currentSection.function_info.returns = text;
                                } else if (currentSubsection === 'remarks') {
                                    currentSection.function_info.remarks = text;
                                } else if (isFunctionSignature(text)) {
                                    currentSection.function_info.signature = text;
                                } else {
                                    currentSection.content.push(text);
                                }
                            }
                        } else if (elem.tagName === 'TABLE') {
                            const table = {
                                headers: [],
                                rows: []
                            };
                            
                            // Get headers
                            const headers = elem.querySelectorAll('th');
                            headers.forEach(th => {
                                const text = th.textContent.trim();
                                if (text) {
                                    table.headers.push(text);
                                }
                            });
                            
                            // Get rows
                            const rows = elem.querySelectorAll('tr');
                            rows.forEach(row => {
                                const cells = row.querySelectorAll('td');
                                if (cells.length > 0) {
                                    const rowData = [];
                                    cells.forEach(cell => {
                                        const text = cell.textContent.trim();
                                        if (text) {
                                            rowData.push(text);
                                        }
                                    });
                                    if (rowData.length > 0) {
                                        table.rows.push(rowData);
                                        // Check if this is a parameters table
                                        if (currentSubsection === 'parameters' || 
                                            (table.headers.length > 0 && 
                                             (table.headers.includes('Param') || table.headers.includes('Parameter')))) {
                                            currentSection.function_info.parameters.push({
                                                name: rowData[0],
                                                description: rowData[1] || ''
                                            });
                                        }
                                    }
                                }
                            });
                            
                            if (table.headers.length > 0 || table.rows.length > 0) {
                                currentSection.tables.push(table);
                            }
                        } else if (elem.tagName === 'UL' || elem.tagName === 'OL') {
                            const items = [];
                            elem.querySelectorAll('li').forEach(li => {
                                const text = li.textContent.trim();
                                if (text) {
                                    items.push(text);
                                }
                            });
                            if (items.length > 0) {
                                currentSection.lists.push(items);
                            }
                        } else if (elem.tagName === 'PRE' || elem.classList.contains('programlisting')) {
                            // Extract code blocks
                            const code = elem.textContent.trim();
                            if (code) {
                                // Check if this is a function signature
                                if (isFunctionSignature(code)) {
                                    currentSection.function_info.signature = code;
                                } else {
                                    const codeBlock = {
                                        language: elem.querySelector('.language') ? elem.querySelector('.language').textContent : 'C',
                                        code: code
                                    };
                                    currentSection.code.push(codeBlock);
                                    if (currentSubsection === 'example') {
                                        currentSection.function_info.example = code;
                                    }
                                }
                            }
                        }
                    }
                }
                
                return content;
            }''')

            # Save the extracted content
            output_file = os.path.join(self.output_dir, f'{self.sanitize_filename(title)}.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'title': title,
                    'content': content
                }, f, indent=2)
            
            await page.close()

        except Exception as e:
            print(f"Error scraping peripheral page {title}: {str(e)}")
            traceback.print_exc()

    async def expand_level(self, level, page):
        """Expand all items at a specific level in the navigation tree."""
        print(f"Expanding level {level} items...")
        
        # Find all expand buttons at the current level
        expand_buttons = await page.evaluate(f'''
            () => {{
                const buttons = Array.from(document.querySelectorAll('.wh-expand-btn:not(.expanded)'));
                return buttons
                    .filter(btn => {{
                        // Count parent expand buttons to determine level
                        let el = btn;
                        let level_count = 0;
                        while (el) {{
                            el = el.closest('div').parentElement.closest('div');
                            if (el && el.querySelector('.wh-expand-btn.expanded')) {{
                                level_count++;
                            }}
                        }}
                        return level_count === {level - 1};
                    }})
                    .map(btn => {{
                        const link = btn.closest('div').querySelector('a');
                        return {{
                            title: link ? link.textContent.trim() : '',
                            hasExpandBtn: true
                        }};
                    }});
            }}
        ''')
        
        if not expand_buttons:
            print(f"No more items to expand at level {level}")
            return False
            
        # Click each expand button at this level
        for item in expand_buttons:
            if item['hasExpandBtn']:
                print(f"Expanding: {item['title']}")
                await page.evaluate(f'''
                    (title) => {{
                        const buttons = Array.from(document.querySelectorAll('.wh-expand-btn:not(.expanded)'));
                        const button = buttons.find(btn => {{
                            const link = btn.closest('div').querySelector('a');
                            return link && link.textContent.trim() === title;
                        }});
                        if (button) button.click();
                        return !!button;
                    }}
                ''', item['title'])
                # Wait for DOM update after each click
                await page.wait_for_timeout(100)  # Small wait between clicks
        
        return True

    async def scrape_pages_in_parallel(self, links, context):
        """Scrape pages in parallel using asyncio tasks with improved concurrency."""
        total_links = len(links)
        tasks = []
        completed = 0

        # Create a semaphore to limit concurrent connections
        sem = asyncio.Semaphore(self.max_concurrent_pages)

        async def scrape_with_semaphore(link):
            async with sem:
                nonlocal completed
                peripheral_url = f"{self.base_url}/{link['href']}"
                try:
                    await self.scrape_peripheral_page(peripheral_url, link['title'], context)
                    completed += 1
                    if completed % 10 == 0:  # Print progress every 10 pages
                        print(f"Progress: {completed}/{total_links} pages scraped")
                except Exception as e:
                    print(f"Error scraping {link['title']}: {str(e)}")

        # Create tasks for all links
        for link in links:
            task = asyncio.create_task(scrape_with_semaphore(link))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

    async def scrape_page(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                java_script_enabled=True
            )
            
            # Create main page for navigation
            main_page = await context.new_page()
            
            try:
                # First navigate to main documentation page
                main_url = f"{self.base_url}/{self.target_page}"
                print(f"Navigating to {main_url}...")
                await main_page.goto(main_url, timeout=10000)
                await main_page.wait_for_selector('div.wh_content_area', timeout=5000)
                
                # Expand navigation tree level by level
                print("\nExpanding navigation tree...")
                current_level = 1
                while True:
                    has_more = await self.expand_level(current_level, main_page)
                    if not has_more:
                        break
                    current_level += 1
                    # Small wait between levels
                    await main_page.wait_for_timeout(200)
                
                print("\nCollecting all peripheral links...")
                peripheral_links = await main_page.evaluate('''
                    () => {
                        const links = [];
                        document.querySelectorAll('div[data-tocid] a').forEach(link => {
                            const title = link.textContent.trim();
                            const href = link.getAttribute('href');
                            if (href && !href.startsWith('http') && title.startsWith('2.')) {
                                links.push({
                                    href: href,
                                    title: title
                                });
                            }
                        });
                        return links;
                    }
                ''')
                
                # Save main page content
                main_content = {
                    'url': main_url,
                    'timestamp': datetime.now().isoformat(),
                    'content': {
                        'title': await main_page.title(),
                        'sections': [{
                            'heading': "2 API Documentation",
                            'level': 1,
                            'content': [
                                await (await main_page.query_selector('div.body p')).text_content()
                            ],
                            'tables': [],
                            'lists': []
                        }],
                        'images': []
                    }
                }
                
                with open(os.path.join(self.output_dir, "main.json"), "w", encoding="utf-8") as f:
                    json.dump(main_content, f, indent=4)
                
                # Close main page as we don't need it anymore
                await main_page.close()
                
                # Scrape peripheral pages in parallel with improved concurrency
                print(f"\nFound {len(peripheral_links)} peripheral pages to scrape...")
                await self.scrape_pages_in_parallel(peripheral_links, context)
                
            except Exception as e:
                print(f"Error during scraping: {str(e)}")
                traceback.print_exc()
            finally:
                await browser.close()

if __name__ == "__main__":
    scraper = MicrochipScraper()
    asyncio.run(scraper.scrape_page()) 