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
├── 04-assets/
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
from pathlib import Path

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

def clean_markdown_body(markdown_body):
    """
    Clean up markdown body by removing unwanted elements and converting others.
    
    Args:
        markdown_body (str): Raw markdown content
        
    Returns:
        str: Cleaned markdown content
    """
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
            cleaned_lines.append(f'\\section{{{lao_text}}}')
            continue
            
        # Convert {GC <page>.<paragraph>} to \egw{GC <page>.<paragraph>}
        # This handles references at the end of paragraphs
        egw_pattern = r'\{(GC \d+\.\d+)\}'
        line = re.sub(egw_pattern, r'\\egw{\1}', line)
        
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
    Script is in 04-assets/scripts/, so project root is two levels up.
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
    
    return str(project_root / "04-assets" / "temp" / output_name)

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