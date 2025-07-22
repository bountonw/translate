#!/usr/bin/env python3
"""
Module 1: YAML Header Extraction & Initial Cleanup
Lao Language TeX Preprocessing Pipeline

OVERVIEW:
This is the first module in a multi-stage preprocessing pipeline that converts
Lao language Markdown files into LuaLaTeX format for typesetting. The project
involves processing chapter files with sophisticated Lao typography
requirements including custom line-breaking and penalty systems.

PROJECT STRUCTURE:
├── 03_public/          # Source Markdown files (GC##_lo.md)
├── 04_assets/
│   ├── scripts/        # This preprocessing script
│   ├── temp/           # Intermediate .tmp files
│   └── tex/            # Final .tex output files

WHAT THIS MODULE DOES:
1. Extracts chapter metadata from YAML frontmatter:
   - Chapter number (Arabic numerals)
   - Lao chapter title
   - Source URL for reference
   
2. Cleans up Markdown content:
   - Removes translation alignment lines (## {GC x.y})
   - Converts Lao subheadings (### text) to \\section{text}
   - Converts paragraph references ({GC x.y}) to \\egw{GC x.y}
   
3. Generates TeX header commands:
   - \\laochapter{number}{title}
   - \\source{url}

INPUT FORMAT:
Markdown files with YAML frontmatter containing chapter metadata and Lao text
with embedded reference codes for alignment with source English text.

OUTPUT FORMAT:
Intermediate .tmp files with TeX commands and cleaned Lao text, ready for
subsequent processing modules that will apply dictionary-based line-breaking
and final formatting.

PROCESSING MODES:
- Production: Creates single .tmp file (overwrites between stages)
- Debug: Creates _stage#.tmp files for inspection of each processing step

USAGE:
python3 module1_preprocess.py [files...]           # Process specific files
python3 module1_preprocess.py                      # Process all files in 03_public/
python3 module1_preprocess.py --debug              # Enable debug mode
"""

import os
import sys
import argparse
import re
import json
from pathlib import Path
import unicodedata

def simple_yaml_parse(yaml_content):
    """
    Simple YAML parser for our specific frontmatter structure.
    """
    lines = yaml_content.strip().split('\n')
    data = {}
    stack = [data]  # Stack to track nested levels
    
    for line in lines:
        if not line.strip() or line.strip().startswith('#'):
            continue
        
        # Count leading spaces
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        
        if ':' not in stripped:
            continue
            
        key, value = stripped.split(':', 1)
        key = key.strip()
        value = value.strip()
        
        # Determine nesting level (assuming 2 spaces per level)
        level = indent // 2
        
        # Adjust stack to current level
        while len(stack) > level + 1:
            stack.pop()
        
        # Get current container
        current = stack[-1]
        
        if value:
            # Key with value
            current[key] = value
        else:
            # Key without value (container)
            current[key] = {}
            stack.append(current[key])
    
    return data

def parse_yaml_frontmatter(content):
    """
    Extract YAML frontmatter from markdown content.
    
    Args:
        content (str): Full markdown file content
        
    Returns:
        tuple: (yaml_data, markdown_body)
    """
    # Check if content starts with YAML frontmatter
    if not content.startswith('---\n'):
        raise ValueError("File does not contain YAML frontmatter")
    
    # Find the end of YAML frontmatter
    end_pattern = r'\n---\n'
    match = re.search(end_pattern, content)
    if not match:
        raise ValueError("Invalid YAML frontmatter - no closing ---")
    
    # Extract YAML and body
    yaml_content = content[4:match.start()]  # Skip opening ---
    markdown_body = content[match.end():]    # Skip closing ---
    
    # Parse YAML
    try:
        yaml_data = simple_yaml_parse(yaml_content)
    except Exception as e:
        raise ValueError(f"Invalid YAML: {e}")
    
    return yaml_data, markdown_body

def extract_chapter_info(yaml_data, debug=False):
    """
    Extract chapter information from YAML data.
    
    Args:
        yaml_data (dict): Parsed YAML data
        debug (bool): Print debug info
        
    Returns:
        dict: Chapter information (number, title_lo, url)
    """
    if debug:
        print("DEBUG: Parsed YAML structure:")
        print(yaml_data)
        
    try:
        chapter_info = {
            'number': yaml_data['chapter']['number'],
            'title_lo': yaml_data['chapter']['title']['lo'],
            'url': yaml_data['chapter'].get('url', '')  # Optional field, default to empty
        }
        return chapter_info
    except KeyError as e:
        if debug:
            print(f"DEBUG: KeyError accessing {e}")
            print(f"DEBUG: Available keys at root: {list(yaml_data.keys())}")
            if 'chapter' in yaml_data:
                print(f"DEBUG: Available keys in chapter: {list(yaml_data['chapter'].keys())}")
        raise ValueError(f"Missing required YAML field: {e}")

def normalize_lao_text(text):
    """Simple AM vowel standardization without Unicode normalization."""
    # Handle AM vowel combinations
    text = text.replace('ໍາ', 'ຳ')
    text = text.replace('ໍ່າ', '່ຳ')  # mai ek + AM
    text = text.replace('ໍ້າ', '້ຳ')  # mai to + AM  
    text = text.replace('ໍ໊າ', '໊ຳ')  # mai tri + AM
    text = text.replace('ໍ໋າ', '໋ຳ')  # mai chattawa + AM
    return text

def clean_markdown_body(markdown_body):
    """
    Clean up markdown body by removing unwanted elements and converting others.
    Now includes Unicode normalization for Lao text.
    
    Args:
        markdown_body (str): Raw markdown content
        
    Returns:
        str: Cleaned markdown content
    """
    # Apply Unicode normalization first
    markdown_body = normalize_lao_text(markdown_body)
    
    # Protect Bible books BEFORE other processing
    markdown_body = protect_numbered_bible_books(markdown_body)
    markdown_body = protect_scripture_spacing(markdown_body)
    markdown_body = protect_scripture_references(markdown_body)

    lines = markdown_body.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip ## {GC <page>.<paragraph>} lines
        if re.match(r'^## \{GC \d+\.\d+\}$', line.strip()):
            continue
            
        # Convert ### <lao text> to \section{<lao text>}
        section_match = re.match(r'^### (.+)$', line.strip())
        if section_match:
            lao_text = section_match.group(1)
            # Apply normalization to the section text as well
            lao_text = normalize_lao_text(lao_text)
            cleaned_lines.append(f'\\section{{{lao_text}}}')
            continue
            
        # Convert {GC <page>.<paragraph>} to \egw{GC <page>.<paragraph>}
        # This handles references at the end of paragraphs
        egw_pattern = r'\{(GC) (\d+\.\d+)\}'
        line = re.sub(egw_pattern, r'\\egw{\1\\nbsp \2}', line)
        
        # Apply normalization to the processed line
        line = normalize_lao_text(line)
        cleaned_lines.append(line)
    
    # Join lines and normalize whitespace
    content = '\n'.join(cleaned_lines)
    
    # Remove excessive blank lines (more than 2 consecutive)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Clean up leading/trailing whitespace
    content = content.strip()
    
    return content

def generate_tex_header(chapter_info):
    """
    Generate TeX header commands from chapter information.
    
    Args:
        chapter_info (dict): Chapter information
        
    Returns:
        str: TeX header content
    """
    header_lines = [
        f"\\laochapter{{{chapter_info['number']}}}{{{chapter_info['title_lo']}}}"
    ]
    
    # Only add source if URL is provided
    if chapter_info['url']:
        header_lines.append(f"\\source{{{chapter_info['url']}}}")
    
    return '\n'.join(header_lines)
    
def load_numbered_bible_books():
    """Load numbered Bible books from JSON file."""
    try:
        script_dir = Path(__file__).parent
        json_path = script_dir / ".." / ".." / ".." / "assets" / "data" / "bible" / "bible_books.json"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [book['lao_name'] for book in data['books'] if book.get('numbered', False)]
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not load numbered Bible books: {e}")
        return []

def protect_numbered_bible_books(text):
    """
    Protect numbered Bible book names by converting spaces to \\nbsp.
    
    Args:
        text (str): Input text that may contain numbered Bible books
        
    Returns:
        str: Text with numbered Bible books protected
    """
    numbered_books = load_numbered_bible_books()
    
    if not numbered_books:
        return text  # Return unchanged if books couldn't be loaded
    
    protected_text = text
    
    # Process each numbered book
    for book in numbered_books:
        # Convert "1 ຊາມູເອນ" to "1\\nbsp ຊາມູເອນ"
        protected_book = book.replace(" ", "\\nbsp ", 1)  # Only replace first space
        protected_text = protected_text.replace(book, protected_book)
    
    return protected_text

def load_all_bible_books():
    """Load all Bible books data from JSON file."""
    try:
        script_dir = Path(__file__).parent
        json_path = script_dir / ".." / ".." / ".." / "assets" / "data" / "bible" / "bible_books.json"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get all book names
        all_books = [book['lao_name'] for book in data['books']]
        
        # Get numbered books mapping
        numbered_mapping = {}
        for book in data['books']:
            if book.get('numbered', False):
                nbsp_form = book['lao_name'].replace(' ', '\\nbsp ', 1)
                numbered_mapping[book['lao_name']] = nbsp_form
        
        # Reference pattern
        reference_pattern = re.compile(r'\d+:\d+(?:[,-]\d+)*(?:\s*[,-]\s*\d+(?::\d+)?)*')
        
        return all_books, numbered_mapping, reference_pattern
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not load Bible books: {e}")
        return [], {}, None

def protect_scripture_spacing(text):
    """Add \\scrspace between Bible book names and scripture references."""
    bible_books, numbered_mapping, reference_pattern = load_all_bible_books()
    
    if not bible_books or not reference_pattern:
        return text
    
    import re
    protected_text = text
    
    # Process each Bible book
    for book in bible_books:
        # Handle both original form and nbsp form (if it's a numbered book)
        book_forms = [book]
        if book in numbered_mapping:
            book_forms.append(numbered_mapping[book])
        
        for book_form in book_forms:
            pattern = rf'({re.escape(book_form)})\s+({reference_pattern.pattern})'
            protected_text = re.sub(pattern, rf'\1\\scrspace \2', protected_text)
    
    return protected_text

def split_reference_components(reference_text):
    """Split scripture reference text into components and separators."""
    # Split on commas and semicolons, preserving separators
    parts = re.split(r'([,;])', reference_text)
    components = []
    separators = []
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        elif part in [',', ';']:
            separators.append(part)
        else:
            components.append(part)
    
    return components, separators

def format_reference_components(components, separators):
    """Format reference components with proper TeX markup."""
    formatted_parts = []
    
    for i, component in enumerate(components):
        formatted_parts.append(f'\\scrref{{{component}}}')
        
        # Add separator if not the last component
        if i < len(separators):
            separator = separators[i]
            formatted_parts.append(f'{separator}\\scrspace')  # Removed \nobreak
    
    return ''.join(formatted_parts)

def protect_scripture_references(text):
    """Wrap individual scripture reference components with \\scrref{}."""
    # Pattern: \scrspace + space + reference that ends at specific boundaries
    # Reference ends at: space, period, comma, semicolon, closing paren, quotes (regular and smart), or line end
    # Note: colon is NOT a boundary since it's part of chapter:verse format
    pattern = r'\\scrspace\s+(\d+:\d+(?:[,–-]\d+)*(?:\s*[,;]\s*\d+(?::\d+)?(?:[,–-]\d+)*)*)(?=\s|[\.;,)\'"”’]|$)'
    
    matches = list(re.finditer(pattern, text))
    
    # Process matches in reverse order to avoid position shifts
    for match in reversed(matches):
        reference_content = match.group(1).strip()
        components, separators = split_reference_components(reference_content)
        formatted = format_reference_components(components, separators)
        replacement = f'\\scrspace{formatted}'
        text = text[:match.start()] + replacement + text[match.end():]
    
    return text

def process_file(input_path, output_path, debug_mode=False):
    """
    Process a single markdown file.
    
    Args:
        input_path (str): Path to input .md file
        output_path (str): Path to output .tmp file
        debug_mode (bool): Whether to use debug mode
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read input file
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse YAML frontmatter
        yaml_data, markdown_body = parse_yaml_frontmatter(content)
        
        # Extract chapter information
        chapter_info = extract_chapter_info(yaml_data, debug_mode)
        
        # Clean markdown body
        cleaned_body = clean_markdown_body(markdown_body)
        
        # Generate TeX header
        tex_header = generate_tex_header(chapter_info)
        
        # Combine header and body
        final_content = tex_header + '\n\n' + cleaned_body
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        if debug_mode:
            print(f"✓ Processed: {input_path} → {output_path}")
            print(f"  Chapter {chapter_info['number']}: {chapter_info['title_lo']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error processing {input_path}: {e}")
        return False

def get_project_root():
    """
    Get the project root directory based on script location.
    Script is in 04_assets/scripts/, so project root is two levels up.
    """
    script_dir = Path(__file__).parent
    return script_dir.parent.parent

def resolve_input_path(filename):
    """
    Resolve input filename to full path in 03_public/ directory.
    
    Args:
        filename (str): Just the filename (e.g., 'GC01_lo.md')
        
    Returns:
        Path: Full path to the file
    """
    project_root = get_project_root()
    
    # If it's already a full path, use as-is
    if '/' in filename or '\\' in filename:
        return Path(filename)
    
    # Otherwise, assume it's in 03_public/
    return project_root / '03_public' / filename

def get_output_path(input_path, debug_mode=False, stage=1):
    """
    Generate output path based on input path and mode.
    
    Args:
        input_path (str): Input file path
        debug_mode (bool): Whether in debug mode
        stage (int): Stage number for debug mode
        
    Returns:
        str: Output file path
    """
    project_root = get_project_root()
    input_file = Path(input_path)
    base_name = input_file.stem  # filename without extension
    
    if debug_mode:
        output_name = f"{base_name}_stage{stage}.tmp"
    else:
        output_name = f"{base_name}.tmp"
    
    return str(project_root / "04_assets" / "temp" / output_name)

def main():
    parser = argparse.ArgumentParser(
        description="Module 1: YAML Header Extraction & Initial Cleanup"
    )
    parser.add_argument(
        'files', 
        nargs='*', 
        help='Markdown files to process (default: all .md files in 03_public/)'
    )
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='Enable debug mode (keep stage files)'
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Determine input files
    if args.files:
        # Resolve each filename to full path
        input_files = [resolve_input_path(f) for f in args.files]
    else:
        # Process all .md files in 03_public/
        project_root = get_project_root()
        public_dir = project_root / '03_public'
        if not public_dir.exists():
            print(f"Error: {public_dir} directory not found")
            sys.exit(1)
        input_files = list(public_dir.glob('*.md'))
        if not input_files:
            print(f"No .md files found in {public_dir}")
            sys.exit(1)
    
    # Process files
    success_count = 0
    total_count = len(input_files)
    
    print(f"Processing {total_count} file(s) in {'debug' if args.debug else 'production'} mode...")
    
    for input_file in input_files:
        input_path = str(input_file)
        output_path = get_output_path(input_path, args.debug, stage=1)
        
        if process_file(input_path, output_path, args.verbose or args.debug):
            success_count += 1
    
    print(f"\nCompleted: {success_count}/{total_count} files processed successfully")
    
    if success_count < total_count:
        sys.exit(1)

if __name__ == "__main__":
    main()