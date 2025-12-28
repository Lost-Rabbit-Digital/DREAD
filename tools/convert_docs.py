#!/usr/bin/env python3
"""
Convert Zero Sievert modding HTML documentation to clean Markdown.
Preserves structure, tables, code blocks, and headers.
"""

import os
import html2text
from pathlib import Path
from bs4 import BeautifulSoup
import re

# Configuration
SOURCE_DIR = Path("/home/user/DREAD/Modding Documentation")
OUTPUT_DIR = Path("/home/user/DREAD/docs/api")
SKIP_DIRS = {"lib", "Images For Reference"}

def setup_html2text():
    """Configure html2text for optimal markdown output."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.ignore_emphasis = False
    h.body_width = 0  # No line wrapping
    h.unicode_snob = True
    h.skip_internal_links = True
    h.inline_links = True
    h.protect_links = True
    h.wrap_links = False
    h.wrap_list_items = False
    h.pad_tables = True
    return h

def clean_markdown(md_text):
    """Clean up the markdown output."""
    # Remove excessive blank lines (more than 2 in a row)
    md_text = re.sub(r'\n{4,}', '\n\n\n', md_text)

    # Fix code blocks - ensure they have language hints where possible
    md_text = re.sub(r'```\n(--.*?Catspeak|.*?func\()', r'```catspeak\n\1', md_text)

    # Remove any remaining HTML entities
    md_text = md_text.replace('&gt;', '>')
    md_text = md_text.replace('&lt;', '<')
    md_text = md_text.replace('&amp;', '&')
    md_text = md_text.replace('&nbsp;', ' ')

    # Clean up table formatting
    md_text = re.sub(r'\|\s+\|', '| |', md_text)

    # Remove navigation/boilerplate if present
    lines = md_text.split('\n')
    cleaned_lines = []
    skip_until_content = True

    for line in lines:
        # Skip empty lines at the start
        if skip_until_content and not line.strip():
            continue
        # Found content
        if line.strip():
            skip_until_content = False
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines).strip()

def extract_title(soup):
    """Extract the document title."""
    title_tag = soup.find('title')
    if title_tag:
        return title_tag.get_text().strip()
    h1 = soup.find('h1')
    if h1:
        return h1.get_text().strip()
    return None

def convert_file(html_path, output_path, converter):
    """Convert a single HTML file to Markdown."""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Parse with BeautifulSoup first for preprocessing
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract title
        title = extract_title(soup)

        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()

        # Get the main content (usually in body or a main div)
        body = soup.find('body')
        if body:
            html_content = str(body)
        else:
            html_content = str(soup)

        # Convert to markdown
        md_content = converter.handle(html_content)
        md_content = clean_markdown(md_content)

        # Add title as H1 if not already present
        if title and not md_content.startswith('# '):
            md_content = f"# {title}\n\n{md_content}"

        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def main():
    """Main conversion process."""
    converter = setup_html2text()

    print("=" * 60)
    print("Zero Sievert Modding Documentation Converter")
    print("=" * 60)
    print(f"Source: {SOURCE_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Skipping: {SKIP_DIRS}")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Track statistics
    converted = 0
    failed = 0
    skipped = 0

    # Walk through source directory
    for root, dirs, files in os.walk(SOURCE_DIR):
        # Skip specified directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        rel_path = Path(root).relative_to(SOURCE_DIR)

        for file in files:
            if not file.endswith('.html'):
                skipped += 1
                continue

            html_path = Path(root) / file
            md_filename = file.replace('.html', '.md')
            output_path = OUTPUT_DIR / rel_path / md_filename

            print(f"Converting: {rel_path / file}")

            if convert_file(html_path, output_path, converter):
                converted += 1
            else:
                failed += 1

    # Also copy the exposed_values.txt file
    exposed_values_src = SOURCE_DIR / "exposed_values.txt"
    if exposed_values_src.exists():
        exposed_values_dst = OUTPUT_DIR / "exposed_values.txt"
        with open(exposed_values_src, 'r') as f:
            content = f.read()
        with open(exposed_values_dst, 'w') as f:
            f.write(content)
        print(f"Copied: exposed_values.txt")
        converted += 1

    print("=" * 60)
    print(f"Conversion complete!")
    print(f"  Converted: {converted}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped} (non-HTML files)")
    print("=" * 60)

    # Print directory structure
    print("\nOutput structure:")
    for root, dirs, files in os.walk(OUTPUT_DIR):
        level = len(Path(root).relative_to(OUTPUT_DIR).parts)
        indent = "  " * level
        print(f"{indent}{Path(root).name}/")
        for file in sorted(files)[:5]:  # Show first 5 files per dir
            print(f"{indent}  {file}")
        if len(files) > 5:
            print(f"{indent}  ... and {len(files) - 5} more")

if __name__ == "__main__":
    main()
