#!/usr/bin/env python3
"""
Module 3: TeX Document Assembly
Combines docclass, headers, and processed body content into final .tex files

Usage:
    python3 04_assets/scripts/module3_preprocess.py GC01
    python3 04_assets/scripts/module3_preprocess.py GC[01..05]
    python3 04_assets/scripts/module3_preprocess.py --debug
"""

import os
import sys
import glob
import argparse
from pathlib import Path

def resolve_file_spec(file_spec, temp_dir):
    """
    Resolve file specification to actual stage2.tmp files
    Supports: GC01, GC01_lo, GC[01..05] format
    """
    files = []
    
    if '[' in file_spec and '..' in file_spec and ']' in file_spec:
        # Range expansion: GC[01..05] -> GC01, GC02, GC03, GC04, GC05
        start_idx = file_spec.index('[') + 1
        end_idx = file_spec.index(']')
        range_part = file_spec[start_idx:end_idx]
        prefix = file_spec[:start_idx-1]
        
        if '..' in range_part:
            start_num, end_num = range_part.split('..')
            start_val = int(start_num)
            end_val = int(end_num)
            
            for num in range(start_val, end_val + 1):
                chapter_spec = f"{prefix}{num:02d}"
                resolved = resolve_single_file(chapter_spec, temp_dir)
                if resolved:
                    files.append(resolved)
    else:
        # Single file
        resolved = resolve_single_file(file_spec, temp_dir)
        if resolved:
            files.append(resolved)
    
    return files

def resolve_single_file(file_spec, temp_dir):
    """Resolve single file specification to stage2.tmp file"""
    # Add _lo suffix if not present
    if not file_spec.endswith('_lo') and not file_spec.endswith('.tmp'):
        file_spec += '_lo'
    
    # Add stage2.tmp suffix if not present
    if not file_spec.endswith('.tmp'):
        file_spec += '_stage2.tmp'
    
    full_path = temp_dir / file_spec
    
    if full_path.exists():
        return full_path
    else:
        print(f"Warning: File not found: {full_path}")
        return None

def create_tex_file(stage2_file, scripts_dir, output_dir, debug=False):
    """
    Combine docclass, headers, and body into final .tex file
    """
    # Read the stage2 body content
    try:
        with open(stage2_file, 'r', encoding='utf-8') as f:
            body_content = f.read().strip()
    except Exception as e:
        print(f"Error reading {stage2_file}: {e}")
        return False
    
    # Determine output filename
    base_name = stage2_file.stem.replace('_lo_stage2', '')
    output_file = output_dir / f"{base_name}.tex"
    
    if debug:
        print(f"Creating {output_file}")
    
    # Create the combined .tex content
    tex_content = []
    
    # 1. Docclass import (placeholder for now)
    tex_content.append("% Document class and basic setup")
    tex_content.append("\\input{docclass}")
    tex_content.append("")
    
    # 2. Header commands import
    tex_content.append("% Header commands and formatting")
    tex_content.append("\\input{tex_header_info}")
    tex_content.append("")
    
    # 3. Begin document and body content
    tex_content.append("\\begin{document}")
    tex_content.append("")
    tex_content.append(body_content)
    tex_content.append("")
    tex_content.append("\\end{document}")
    
    # Write the final .tex file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(tex_content))
        
        if debug:
            print(f"Successfully created: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error writing {output_file}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Module 3: TeX Document Assembly')
    parser.add_argument('files', nargs='*', help='Files to process (e.g., GC01, GC[01..05])')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    # Set up paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent  # Back to GC/ directory
    temp_dir = project_dir / '04_assets' / 'temp'
    scripts_dir = project_dir / '04_assets' / 'scripts'
    tex_output_dir = temp_dir / 'tex'
    
    # Create tex output directory if it doesn't exist
    tex_output_dir.mkdir(exist_ok=True)
    
    # Determine files to process
    if args.files:
        # Process specified files
        all_files = []
        for file_spec in args.files:
            files = resolve_file_spec(file_spec, temp_dir)
            all_files.extend(files)
    else:
        # Process all stage2.tmp files
        all_files = list(temp_dir.glob("*_stage2.tmp"))
    
    if not all_files:
        print("No stage2.tmp files found to process")
        return 1
    
    # Process each file
    success_count = 0
    for stage2_file in all_files:
        if create_tex_file(stage2_file, scripts_dir, tex_output_dir, args.debug):
            success_count += 1
    
    print(f"Successfully processed {success_count}/{len(all_files)} files")
    
    if args.debug:
        print(f"Output directory: {tex_output_dir}")
    
    return 0 if success_count == len(all_files) else 1

if __name__ == "__main__":
    sys.exit(main())
