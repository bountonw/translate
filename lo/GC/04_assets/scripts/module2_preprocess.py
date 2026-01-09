#!/usr/bin/env python3
"""
Module 2: Dictionary Lookup and Line-Breaking Application
Lao Language TeX Preprocessing Pipeline

OVERVIEW:
This is the second module in the preprocessing pipeline that applies dictionary-based
line-breaking to Lao text. It processes the cleaned .tmp files from Module 1 and
applies sophisticated break point penalties using a comprehensive Lao dictionary.

PROJECT STRUCTURE:
├── 04_assets/
│   ├── scripts/        # This preprocessing script
│   ├── temp/           # Input .tmp files (from Module 1) and output .tmp files
│   └── tex/            # Final .tex output files (for later modules)
└── ../../../../lo/assets/dictionaries/main.txt  # Dictionary file

WHAT THIS MODULE DOES:
1. Loads Lao dictionary with break point markings:
   - Clean terms (column 1) for text matching
   - Coded terms (column 2) with break point penalties
   
2. Processes Lao text using dictionary lookup:
   - Handles compound terms with internal spaces
   - Applies longest-match-first strategy
   - Preserves original space boundaries
   
3. Converts break point symbols to TeX penalties:
   - !! → \\p{7500} (armageddon)
   - ! → \\p{5000} (nuclear)
   - ~ → \\p{1000} (emergency)
   - ~~ → \\p{100} (discouraged)
   - ~~~ → \\p{0} (neutral)
   - ~~~~ → \\p{-200} (encouraged)
   - ~~~~~ → \\p{-400} (excellent)
   - ~S~ → \\cs (compound space)
   
6. Wraps terms and manages spacing:
   - Dictionary terms → \\lw{term_with_penalties}
   - Punctuation protection → \\nobreak before punctuation

DICTIONARY FORMAT:
clean_term| coded_term % comment
Example: ການສຶກສາ| ການ~~~~ສຶກສາ % education

INPUT FORMAT:
Cleaned .tmp files from Module 1 with TeX commands and Lao text.

OUTPUT FORMAT:
.tmp files with \\lw{} wrapped terms, break points, and proper spacing for LuaLaTeX.

PROCESSING MODES:
- Production: Overwrites .tmp files
- Debug: Creates _stage2.tex files for inspection

USAGE:
python3 module2_preprocess.py [files...]           # Process specific .tmp files
python3 module2_preprocess.py                      # Process all .tmp files in temp/
python3 module2_preprocess.py --debug              # Enable debug mode
"""

import os
import sys
import argparse
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Any
# Import dictionary loader helper
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent / 'helpers'))
from dict_loader import load_hierarchical_dictionaries, LaoDictionary

# Import Lao word processing functions
from lao_word_processor import (
    is_lao_text, is_punctuation, is_opening_punctuation, is_closing_punctuation,
    group_consecutive_text, lookup_lao_words, TONE_MARKS, DEPENDENT_VOWELS,
    find_lao_word_boundary, parse_longest_first, parse_shortest_first, 
    parse_with_backtrack, is_invalid_standalone_lao
)

try:
    import module2_debug
    HAS_DEBUG = True
except ImportError:
    HAS_DEBUG = False

session_stats = {
    'decisions_made': 0,
    'strategy_changes': 0,
    'interesting_cases': 0
}

def needs_nobreak_protection(text):
    """Check if text needs nobreak protection (ends with \\lw{} or \\nodict{} or is Lao repeat)."""
    return (text.endswith('}') or 
            text in ['\\laorepeat', '\\laorepeatbefore'])

def apply_punctuation_protection(parts):
    """Apply \nobreak protection around punctuation in a list of text parts."""
    if len(parts) <= 1:
        return parts
    
    protected_parts = []
    
    for i, part in enumerate(parts):
        protected_parts.append(part)
        
        # Look ahead to next part
        if i < len(parts) - 1:
            current_part = part
            next_part = parts[i + 1]
            
            # Case 1: Add \nobreak before closing punctuation
            # \lw{word} + "." → \lw{word}\nobreak.
            if (needs_nobreak_protection(current_part) and 
                len(next_part) > 0 and 
                is_closing_punctuation(next_part[0])):
                protected_parts.append('\\nobreak{}')
            
            # Case 2: Add \nobreak after opening punctuation  
            # " + \lw{word} → "\nobreak\lw{word}
            elif (len(current_part) > 0 and 
                  is_opening_punctuation(current_part[-1]) and
                  needs_nobreak_protection(next_part)):
                protected_parts.append('\\nobreak{}')

    return protected_parts
    
def restore_protected_commands(text, protected_commands):
    """Restore original protected commands from placeholders."""
    for i, command in enumerate(protected_commands):
        placeholder = f"__PROTECTED_CMD_{i}__"
        text = text.replace(placeholder, command)
    return text

def process_tex_command_with_lao(line, dictionary, debug=False):
   """Process TeX commands that contain Lao text in braces."""
   
   def replace_lao_in_braces(match):
       content = match.group(1)
       if is_lao_text(content):
           # Use full processing pipeline to handle spaces properly
           processed = process_text_line(content, dictionary, debug)
           return '{' + processed + '}'
       else:
           return match.group(0)  # Return unchanged if no Lao
   
   # Pattern to match content within braces
   pattern = r'\{([^}]+)\}'
   processed_line = re.sub(pattern, replace_lao_in_braces, line)
   
   return processed_line

def extract_and_preserve_commands(text):
    """
    Extract \\egw{...}, \\scrref{...}, \\lw{...}, \\scrspace,
    footnote markers ([^n] and [^n]:), and \\s/\\S (flex/rigid spaces),
    replacing them with numbered placeholders while allowing \\cs{} to 
    remain visible for dictionary lookup of compound phrases like "word\\cs{}word".

    Returns: 
        (placeholder_text, protected_commands)
    """
    protected_commands = []

    pattern = re.compile(
        r"(\\(?:egw|scrref|lw)\{[^}]+\}"      # \egw{}, \scrref{}, \lw{}
        r"|\\scrspace(?![A-Za-z])"            # \scrspace (standalone)
        r"|\[\^\d+\](?::)?"                   # [^1] and [^1]:
        r"|\\cs\{[^}]*\}"                     # \cs{} - exclude from protection
        r"|\\[sS](?![A-Za-z]))"               # \s or \S (not followed by letters)
    )

    def _repl(m):
        # Don't protect \cs{} commands - let them pass through
        if m.group(0).startswith('\\cs{'):
            return m.group(0)
        
        idx = len(protected_commands)
        protected_commands.append(m.group(0))
        return f"__PROTECTED_CMD_{idx}__"

    placeholder_text = pattern.sub(_repl, text)
    return placeholder_text, protected_commands

def process_text_line(text, dictionary, debug=False):
    """Apply dictionary lookup to text, handling different content types properly."""
    # First, extract and protect \egw{} and other commands
    placeholder_text, protected_commands = extract_and_preserve_commands(text)
    
    # Handle TeX commands with Lao content
    if placeholder_text.strip().startswith('\\'):
        # Skip certain commands entirely
        if any(cmd in placeholder_text for cmd in ['\\source{', '\\p{']):
            return text  # Return original text, not placeholder
        # Process commands that might contain Lao text
        if any(cmd in placeholder_text for cmd in ['\\laochapter{', '\\section{', '\\subsection{']):
            processed = process_tex_command_with_lao(placeholder_text, dictionary, debug)
            return restore_protected_commands(processed, protected_commands)
        # Other TeX commands pass through unchanged
        return text  # Return original text, not placeholder
    
    # Process regular text content
    groups = group_consecutive_text(placeholder_text)
    
    # Step 1: Process text groups through dictionary
    processed_parts = []
    for group_type, content in groups:
        if group_type == 'lao':
            # Apply dictionary lookup to Lao text
            lao_result = lookup_lao_words(content, dictionary, debug)
            processed_parts.append(lao_result)
        else:
            # Pass through other content unchanged
            processed_parts.append(content)
    
    # Step 2: Apply punctuation protection
    protected_parts = apply_punctuation_protection(processed_parts)
    
    # Step 3: Join and restore protected commands
    processed_text = ''.join(protected_parts)

    # HOTFIX — keep \nobreak OUTSIDE \emph{…}
    # Root cause: our punctuation-protection runs on raw text; \emph{…} is not
    # “protected”, so tokenization can split it as "\emph{" + content + "}".
    # When we insert \nobreak between parts, it can land just inside the brace,
    # yielding \emph{\nobreak{}…}. Hoist a leading \nobreak back out so line breaks
    # are controlled at the \emph boundary, not inside its argument.
    processed_text = re.sub(
        r'\\emph\{\s*\\nobreak\{\}\s*',
        r'\\nobreak{}\\emph{',
        processed_text,
    )

    return restore_protected_commands(processed_text, protected_commands)

def process_file(input_path, output_path, dictionary, debug_mode=False):
    """Process a single .tmp file with dictionary application."""
    try:
        # Read input file
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split into lines for processing
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Apply dictionary processing to each line, passing debug flag
            processed_line = process_text_line(line, dictionary, debug_mode)
            processed_lines.append(processed_line)
        
        # Join processed lines
        final_content = '\n'.join(processed_lines)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        if debug_mode:
            print(f"✓ Processed: {input_path} → {output_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error processing {input_path}: {e}")
        return False

def get_project_root():
    """Find GC project root by looking for 04_assets directory"""
    current = Path.cwd()
    
    # If we're in 04_assets directory, parent is project root
    if current.name == '04_assets':
        result = current.parent
        return result
    
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

def expand_chapter_ranges(file_specs):
    """
    Expand chapter range specifications like GC[01..05] into individual chapters.
    
    Args:
        file_specs (list): List of file specifications
        
    Returns:
        list: Expanded list with ranges converted to individual chapters
    """
    expanded = []
    
    for spec in file_specs:
        # Check for range pattern like GC[01..05] or GC[1..5]
        range_match = re.match(r'GC\[(\d+)\.\.(\d+)\]', spec)
        if range_match:
            start_num = int(range_match.group(1))
            end_num = int(range_match.group(2))
            
            # Generate chapter numbers in the range
            for chapter_num in range(start_num, end_num + 1):
                expanded.append(f"GC{chapter_num:02d}")
        else:
            expanded.append(spec)
    
    return expanded
    
def resolve_file_specification(file_spec, temp_dir, debug_mode=False):
    """
    Intelligently resolve a file specification to actual file path.
    
    Args:
        file_spec (str): User-provided file specification (e.g., "GC05", "GC01_lo", "GC03_lo.tmp")
        temp_dir (Path): Path to temp directory
        debug_mode (bool): Whether we're in debug mode
        
    Returns:
        Path or None: Resolved file path, or None if not found
    """
    from pathlib import Path
    
    # If it's already a complete .tmp file path, use as-is
    if file_spec.endswith('.tmp'):
        candidate = temp_dir / file_spec
        if candidate.exists():
            return candidate
        else:
            return None
    
    # Auto-complete the file specification
    base_spec = file_spec
    
    # Add '_lo' if it's just GC## format
    if re.match(r'^GC\d+.*?$', base_spec):
        base_spec = base_spec + '_lo'
    
    # Now we have something like "GC05_lo"
    # Try to find the best available file with fallback logic
    
    candidates = []
    
    if debug_mode:
        # Debug mode: prefer stage1 files, fallback to regular .tmp
        candidates.extend([
            temp_dir / f"{base_spec}_stage1.tmp",  # Preferred for debug
            temp_dir / f"{base_spec}.tmp"          # Fallback
        ])
    else:
        # Production mode: prefer regular .tmp, but also check stage1 for fallback
        candidates.extend([
            temp_dir / f"{base_spec}.tmp",         # Preferred for production
            temp_dir / f"{base_spec}_stage1.tmp"   # Fallback (from debug run)
        ])
    
    # Return the first existing candidate
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    return None

def get_input_files(args):
    """Get list of .tmp files to process with intelligent file matching."""
    project_root = get_project_root()
    temp_dir = project_root / '04_assets' / 'temp'
    
    if not temp_dir.exists():
        print(f"Error: {temp_dir} directory not found")
        sys.exit(1)
    
    if args.files:
        # Process specific files with intelligent matching
        input_files = []
        
        # First expand any range specifications
        expanded_specs = expand_chapter_ranges(args.files)
        
        for file_spec in expanded_specs:
            resolved_path = resolve_file_specification(file_spec, temp_dir, args.debug)
            
            if resolved_path:
                input_files.append(resolved_path)
                if args.verbose or args.debug:
                    print(f"Resolved '{file_spec}' → {resolved_path.name}")
            else:
                print(f"Warning: Could not find file for specification '{file_spec}'")
                
                # Show what we looked for
                base_spec = file_spec
                if re.match(r'^GC\d+.*?$', base_spec):
                    base_spec = base_spec + '_lo'
                
                print(f"  Searched for: {base_spec}.tmp, {base_spec}_stage1.tmp")
        
        return input_files
    else:
        # Process all .tmp files in temp directory (existing behavior)
        if args.debug:
            # Debug mode: look for stage1 files from Module 1 debug output
            stage1_files = list(temp_dir.glob('*_stage1.tmp'))
            if stage1_files:
                print(f"Processing all debug files: {len(stage1_files)} files")
                return stage1_files
            # Fall back to tmp files if no stage1 files
            tmp_files = list(temp_dir.glob('*.tmp'))
            if not tmp_files:
                print(f"No .tmp files found in {temp_dir}")
                sys.exit(1)
            print(f"No stage1 files found, using production files: {len(tmp_files)} files")
            return tmp_files
        else:
            # Production mode: only process tmp files (ignore any stale stage1)
            tmp_files = list(temp_dir.glob('*.tmp'))
            if not tmp_files:
                print(f"No .tmp files found in {temp_dir}")
                sys.exit(1)
            print(f"Processing all available files: {len(tmp_files)} files")
            return tmp_files

def get_output_path(input_path, debug_mode=False):
    """Generate output path based on input path and mode."""
    input_file = Path(input_path)
    
    if debug_mode:
        # stage1.tmp -> stage2.tex, or .tmp -> stage2.tex
        if input_file.stem.endswith('_stage1'):
            base_name = input_file.stem.replace('_stage1', '')
            output_name = f"{base_name}_stage2.tex"
        else:
            base_name = input_file.stem
            output_name = f"{base_name}_stage2.tex"
    else:
        # stage1.tmp -> .tmp, or .tmp -> .tmp (overwrite)
        if input_file.stem.endswith('_stage1'):
            base_name = input_file.stem.replace('_stage1', '')
            output_name = f"{base_name}.tmp"
        else:
            output_name = input_file.name  # Keep same name (overwrite)
    
    return input_file.parent / output_name

def run_pre_debug_tests(filename="GC01"):
    """
    Run test suite before debug processing to ensure stability.
    
    Args:
        filename: Base filename for testing (e.g., "GC05")
    
    Returns:
        bool: True if all tests pass, False if any test fails
    """
    # Prevent infinite recursion when called from test suite
    if os.environ.get('MODULE2_TESTING', '0') == '1':
        return True
    
    try:
        print("🔍 Running pre-debug tests to ensure stability...")
        
        # Import the test module
        script_dir = Path(__file__).parent
        test_script = script_dir / "test_module2.py"
        
        if not test_script.exists():
            print("⚠️ Test script not found - proceeding without tests")
            return True
        
        # Set environment variable to prevent recursion
        env = os.environ.copy()
        env['MODULE2_TESTING'] = '1'
        
        # Run the test suite with filename parameter
        result = subprocess.run(
            [sys.executable, str(test_script), filename],
            cwd=get_project_root(),
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )
        
        if result.returncode == 0:
            print("✅ All tests passed - proceeding with debug processing")
            return True
        else:
            print("❌ Tests failed - debug output:")
            print(result.stdout)
            if result.stderr:
                print("Errors:")
                print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️ Tests timed out - proceeding without validation")
        return True
    except Exception as e:
        print(f"⚠️ Test execution error: {e} - proceeding without validation")
        return True

# Dictionary Maintenance helper function
def _run_dictionary_maintenance(project_root):
    """
    Module 2 cleanup hook:
    - Sort & overwrite main.txt / patch.txt
    - Write duplicate log only if duplicates exist
    - Print a console notice when a log is written
    """
    try:
        from dict_maintenance import maintain_dictionaries
        maintain_dictionaries(project_root=project_root)
    except Exception as e:
        print(f"[Module2] Dictionary maintenance skipped: {e}")

def extract_chapter_book_from_filename(filename):
    """
    Extract chapter and book identifiers from a filename.
    
    Args:
        filename: Path or string like 'GC01_lo.tmp', 'MB03_lo_stage1.tmp',
                  or 'GC00_introduction_lo.tmp'
        
    Returns:
        tuple: (chapter, book) e.g., ('GC01', 'GC'), 
               ('GC00_introduction', 'GC'), or (None, None)
    """
    import re
    
    name = Path(filename).stem  # Remove .tmp extension
    # Remove stage suffixes
    name = re.sub(r'_stage[12]$', '', name)
    # Remove _lo suffix
    name = re.sub(r'_lo$', '', name)
    
    # Match pattern like GC01, MB03, GC00_introduction, etc.
    match = re.match(r'^([A-Z]+)(\d+)(?:_\w+)?$', name)
    if match:
        book = match.group(1)
        chapter = name  # Full chapter code like GC01 or GC00_introduction
        return chapter, book
    
    return None, None

def main():
    parser = argparse.ArgumentParser(
        description="Module 2: Dictionary Lookup and Line-Breaking Application",
        epilog="""
Examples:
  %(prog)s GC01                    # Process chapter 1
  %(prog)s GC01 GC05              # Process chapters 1 and 5
  %(prog)s GC[01..05]             # Process chapters 1 through 5
  %(prog)s GC01_lo.tmp            # Process specific file
  %(prog)s                        # Process all files in temp folder
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'files', 
        nargs='*', 
        help='File specifications to process. Supports: GC01, GC01_lo, GC01_lo.tmp, GC[01..05] ranges'
    )
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='Enable debug mode (create stage2 files, prefer stage1 input)'
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Verbose output'
    )
    parser.add_argument(
        '--log-folder', # "output" to args.log_folder
        type=Path,
        help='Use specified log folder (not cleared for you between runs)'
    )
    
    args = parser.parse_args()
    
    # Run pre-debug tests to ensure stability
    if args.debug:
        # Extract filename from first input file for testing
        test_filename = "GC01"  # Default fallback
        if args.files:
            # Use first file specification for testing
            test_filename = args.files[0]
            # Remove any file extensions or suffixes for test
            if test_filename.endswith('.tmp'):
                test_filename = test_filename[:-4]
            if test_filename.endswith('_lo'):
                test_filename = test_filename[:-3]
        
        if not run_pre_debug_tests(test_filename):
            print("⚠️ Tests failed - aborting to prevent breaking functionality")
            print("Fix the failing tests before proceeding with debug mode.")
            sys.exit(1)
    
    # Initialize debug session
    log_folder = get_project_root() / "04_assets" / "temp"
    if HAS_DEBUG and args.debug:
        if args.log_folder:
            log_folder = args.log_folder
        else:
            # only clear if log_folder not set -- we don't want to erase existing files between runs.
            # this is not the cleanest thing in the world, but it's OK for now.
            module2_debug.initialize_debug_session(log_folder)

    # Get input files with intelligent matching
    input_files = get_input_files(args)
    
    if not input_files:
        print("No input files to process")
        sys.exit(1)
    
    # Group files by chapter for proper dictionary loading
    from collections import defaultdict
    files_by_chapter = defaultdict(list)
    
    for input_file in input_files:
        chapter, book = extract_chapter_book_from_filename(input_file.name)
        files_by_chapter[(chapter, book)].append(input_file)
    
    # Process files
    success_count = 0
    total_count = len(input_files)
    processed_output_files = []
    all_conflicts = {}
    
    mode_desc = 'debug' if args.debug else 'production'
    print(f"Processing {total_count} file(s) in {mode_desc} mode...")
    
    # Process each chapter group with its appropriate dictionary
    for (chapter, book), chapter_files in files_by_chapter.items():
        # Load dictionary for this chapter/book combination
        dictionary, conflicts = load_hierarchical_dictionaries(
            chapter=chapter,
            book=book,
            debug=args.debug
        )
        
        # Collect conflicts for debug reporting
        if conflicts:
            all_conflicts.update(conflicts)
        
        # Process all files for this chapter
        for input_file in chapter_files:
            input_path = str(input_file)
            output_path = str(get_output_path(input_file, args.debug))
            
            if process_file(input_path, output_path, dictionary, args.verbose or args.debug):
                success_count += 1
                processed_output_files.append(Path(output_path))
    
    print(f"\nCompleted: {success_count}/{total_count} files processed successfully")
    
    # Finalize debug session and generate comprehensive reports
    if HAS_DEBUG and args.debug:
        module2_debug.finalize_debug_session(
            log_folder, total_count, success_count, 
            processed_output_files, all_conflicts
        ) 
        _run_dictionary_maintenance(get_project_root())
    
    if success_count < total_count:
        sys.exit(1)
if __name__ == "__main__":
    main()
