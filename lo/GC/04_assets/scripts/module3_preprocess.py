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
    Resolve file specification to actual stage2.tex files
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
    """Resolve single file specification to stage2.tex file"""
    # Add _lo suffix if not present
    if not file_spec.endswith('_lo') and not file_spec.endswith('.tmp'):
        file_spec += '_lo'
    
    # Add stage2.tex suffix if not present
    if not file_spec.endswith('.tmp'):
        file_spec += '_stage2.tex'
    
    full_path = temp_dir / file_spec
    
    if full_path.exists():
        return full_path
    else:
        print(f"Warning: File not found: {full_path}")
        return None

def create_tex_file_input_paths(file_list):
    """
    Create list of \\input lines for the output tex file
    """
    output = []
    for path in file_list:
        # Resolve TeX \\input paths relative to current working directory
        cwd = Path.cwd()

        # Body file path (sans .tex), relative to CWD
        body_input_path = os.path.relpath(path.with_suffix(''), cwd)

        # Normalize separators
        body_input_norm = body_input_path.replace(os.sep, '/')
        output.append(body_input_norm)
    return output

def create_tex_file(tex_input_paths, output_dir, tex_scripts_path, debug=False):
    """
    Combine docclass, headers, and body into the final .tex file.

    Notes:
      - TeX resolves \\input paths relative to the LaTeX CWD.
      - Header and body paths are made CWD-relative so lualatex works from GC/
        or 04_assets/.
    """
    if len(tex_input_paths) == 0:
        print(f"No input paths provided to create_tex_file")
        return False

    output_file = ""
    if len(tex_input_paths) == 1:
        base_name = tex_input_paths[0].replace('_lo_stage2', '')
        base_name = base_name.replace('temp', '')
        base_name = base_name.replace('/', '')
        base_name = base_name.replace('\\', '')
        output_file = output_dir / f"{base_name}.tex"
    else:
        base_name = "full-output" # TODO: adjust naming for output based on files provided; not super important
        output_file = output_dir / f"{base_name}.tex"

    if debug:
        print(f"Creating {output_file}")

    tex_scripts_norm = str(tex_scripts_path).replace(os.sep, '/')

    # Build .tex
    tex_content = []

    # 1) Docclass
    tex_content.append("% Document class and basic setup")
    tex_content.append(f"\\input{{{tex_scripts_norm}/docclass}}")
    tex_content.append("")

    # 2) Header
    tex_content.append("% Header commands and formatting")
    tex_content.append(f"\\input{{{tex_scripts_norm}/tex_header_info}}")
    tex_content.append("")

    # 3) Document + body
    tex_content.append("\\begin{document}")
    tex_content.append("")
    # Page 1: absolutely empty header/footer
    tex_content.append("\\thispagestyle{empty}")
    # Folios: plain footer, arabic, start at 1
    tex_content.append("\\GCInitFolios")
    tex_content.append("")
    # Ensure vertical mode before any heading in the body
    tex_content.append("\\par")
    # Prevent an initial blank page while loading the body
    tex_content.append("\\begingroup")
    tex_content.append("\\let\\clearpage\\relax")
    tex_content.append("\\let\\cleardoublepage\\relax")
    # Output all provided
    for index, file_info in enumerate(tex_input_paths):
        tex_content.append(f"\\input{{{file_info}}}")
        if index < len(tex_input_paths) - 1:
            tex_content.append(f"\\newpage")
    # Output rest of document info
    tex_content.append("\\endgroup")
    tex_content.append("")
    tex_content.append("\\end{document}")

    # Write file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(tex_content))

        if debug:
            print(f"Successfully created: {output_file}")
            if len(tex_input_paths) == 1:
                print(f"Body input path (CWD-relative): {body_input_norm}")
            else:
                print(f"Multiple files in output")
            print(f"TeX scripts path (CWD-relative): {tex_scripts_norm}")
        return True

    except Exception as e:
        print(f"Error writing {output_file}: {e}")
        return False

def find_project_root():
    """Find GC project root by looking for 04_assets directory"""
    current = Path.cwd()
    
    # If we're in 04_assets directory, parent is project root
    if current.name == '04_assets':
        return current.parent
    
    # Check parent directories for 04_assets
    for path in current.parents:
        if (path / '04_assets').exists():
            return path
    
    # Fallback: use script location to infer
    script_dir = Path(__file__).parent
    if script_dir.name == 'scripts':
        return script_dir.parent.parent  # 04_assets/scripts -> GC/
    else:
        return script_dir.parent.parent  # Assume GC/scripts/

def main():
    parser = argparse.ArgumentParser(description='Module 3: TeX Document Assembly')
    parser.add_argument('files', nargs='*', help='Files to process (e.g., GC01, GC[01..05])')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--full', action='store_true', help='Use all provided files in one giant PDF')
    
    args = parser.parse_args()
    
    # Set up paths - robust detection
    project_root = find_project_root()
    temp_dir = project_root / '04_assets' / 'temp'
    scripts_dir = project_root / '04_assets' / 'scripts'
    tex_output_dir = temp_dir / 'tex'
    
    # Create tex output directory if it doesn't exist
    tex_output_dir.mkdir(exist_ok=True)
    
    # For LaTeX paths, calculate relative to current working directory
    cwd = Path.cwd()
    tex_scripts_path = os.path.relpath(scripts_dir / 'tex', cwd)
    
    if args.debug:
        print(f"Project root: {project_root}")
        print(f"Current working dir: {cwd}")
        print(f"TeX scripts path for LaTeX: {tex_scripts_path}")
    
    # Determine files to process
    if args.files:
        # Process specified files
        all_files = []
        for file_spec in args.files:
            files = resolve_file_spec(file_spec, temp_dir)
            all_files.extend(files)
    else:
        # Process all stage2.tex files
        all_files = list(temp_dir.glob("*_stage2.tex"))
    
    if not all_files:
        print("No stage2.tex files found to process")
        return 1
    
    # Process each file with the calculated tex_scripts_path
    success_count = 0
    if args.full:
        # make all files at once
        file_data = create_tex_file_input_paths(all_files)
        if create_tex_file(file_data, tex_output_dir, tex_scripts_path, args.debug):
            success_count += len(all_files)
    else:
        # make files one at a time
        for stage2_file in all_files:
            file_data = create_tex_file_input_paths([stage2_file])
            if create_tex_file(file_data, tex_output_dir, tex_scripts_path, args.debug):
                success_count += 1
    
    print(f"Successfully processed {success_count}/{len(all_files)} files")
    
    if args.debug:
        print(f"Output directory: {tex_output_dir}")
    
    return 0 if success_count == len(all_files) else 1

if __name__ == "__main__":
    sys.exit(main())
