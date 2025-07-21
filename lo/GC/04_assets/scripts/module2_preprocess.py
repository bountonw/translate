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
   - ~~ → \\p{200} (discouraged)
   - ~~~ → \\p{0} (neutral)
   - ~~~~ → \\p{-200} (encouraged)
   - ~~~~~ → \\p{-400} (excellent)
   - ~S~ → \\cs (compound space)
   
6. Wraps terms and manages spacing:
   - Dictionary terms → \\lw{term_with_penalties}
   - Original spaces → \\space
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
- Debug: Creates _stage2.tmp files for inspection

USAGE:
python3 module2_preprocess.py [files...]           # Process specific .tmp files
python3 module2_preprocess.py                      # Process all .tmp files in temp/
python3 module2_preprocess.py --debug              # Enable debug mode
"""

import os
import sys
import argparse
import re
from pathlib import Path

class LaoDictionary:
    """Handles loading and lookup of Lao dictionary with break points."""
    
    def __init__(self, dictionary_path):
        self.dictionary_path = dictionary_path
        self.terms = {}  # clean_term -> coded_term mapping
        self.load_dictionary()
    
    def load_dictionary(self):
        """Load dictionary from pipe-delimited file."""
        try:
            with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('%'):
                        continue
                    
                    # Parse pipe-delimited format: clean_term| coded_term % comment
                    if '|' not in line:
                        continue
                    
                    parts = line.split('|', 1)
                    if len(parts) != 2:
                        continue
                    
                    clean_term = parts[0].strip()
                    coded_part = parts[1].strip()
                    
                    # Remove comment if present
                    if '%' in coded_part:
                        coded_term = coded_part.split('%')[0].strip()
                    else:
                        coded_term = coded_part
                    
                    if clean_term and coded_term:
                        self.terms[clean_term] = coded_term
            
            print(f"Loaded {len(self.terms)} dictionary terms from {self.dictionary_path}")
            
        except FileNotFoundError:
            print(f"Error: Dictionary file not found: {self.dictionary_path}")
            sys.exit(1)
        except UnicodeDecodeError:
            print(f"Error: Dictionary file encoding issue: {self.dictionary_path}")
            sys.exit(1)
        except PermissionError:
            print(f"Error: Permission denied accessing dictionary file: {self.dictionary_path}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading dictionary: {e}")
            sys.exit(1)
    
    def get_sorted_terms(self):
        """Return dictionary terms sorted by length (longest first) for matching."""
        return sorted(self.terms.keys(), key=len, reverse=True)

def convert_break_points(coded_term):
    """Convert dictionary break point symbols to TeX penalty commands."""
    # Handle compound space first (~S~)
    coded_term = re.sub(r'~S~', r'\\cs', coded_term)
    
    # Convert penalty symbols
    # Order matters - longer patterns first
    coded_term = re.sub(r'~~~~~', r'\\p{-400}', coded_term)  # excellent
    coded_term = re.sub(r'~~~~', r'\\p{-200}', coded_term)   # encouraged
    coded_term = re.sub(r'~~~', r'\\p{0}', coded_term)       # neutral
    coded_term = re.sub(r'~~', r'\\p{200}', coded_term)      # discouraged
    coded_term = re.sub(r'!!', r'\\p{7500}', coded_term)     # armageddon
    coded_term = re.sub(r'!', r'\\p{5000}', coded_term)      # nuclear
    coded_term = re.sub(r'~', r'\\p{1000}', coded_term)      # emergency
    
    return coded_term

def is_lao_text(text):
    """Check if text contains Lao characters (includes extended Lao range)."""
    # Lao Unicode ranges: 
    # U+0E80-U+0EFF (main Lao block)
    # U+0EC0-U+0EC4 (Lao vowels that might be missed)
    for char in text:
        if ('\u0e80' <= char <= '\u0eff'):
            return True
    return False

def is_punctuation(char):
    """Check if character is punctuation."""
    return char in '.,;:!?()[]{}"\'\'-–—“”‘’‚„‹›«»@#%'

def is_opening_punctuation(char):
    """Check if character is opening punctuation that needs \nobreak after it."""
    return char in '"\'[{(“‘‚„‹«'
    
def is_closing_punctuation(char):
    """Check if character is closing punctuation that needs \nobreak before it."""
    return char in '.,;:!?()[]{}"\'\'-–—”’‚„›»@#%'

def needs_nobreak_protection(text):
    """Check if text needs nobreak protection (ends with \lw{} or \nodict{} or is Lao repeat)."""
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
                protected_parts.append('\\nobreak')
            
            # Case 2: Add \nobreak after opening punctuation  
            # " + \lw{word} → "\nobreak\lw{word}
            elif (len(current_part) > 0 and 
                  is_opening_punctuation(current_part[-1]) and
                  needs_nobreak_protection(next_part)):
                protected_parts.append('\\nobreak')
    
    return protected_parts

def process_text_groups(groups, dictionary):
    """Process grouped text parts through dictionary lookup and special handling."""
    result_parts = []
    
    for i, (group_type, content) in enumerate(groups):
        if group_type == 'lao':
            # Process Lao text with dictionary
            processed_lao = lookup_lao_words(content, dictionary)
            result_parts.append(processed_lao)
        elif group_type == 'ellipsis':
            # Handle ellipsis with context-aware command selection
            ellipsis_command = handle_ellipsis_context(groups, i)
            result_parts.append(ellipsis_command)
        elif group_type == 'lao_repetition':
            # Handle Lao repetition mark with context-aware command selection
            repetition_command = handle_lao_repetition_context(groups, i)
            result_parts.append(repetition_command)
        elif group_type == 'space':
            # Original spaces become \space
            result_parts.append('\\space')
        else:
            # English, numbers, punctuation, placeholders - leave as-is, no wrapping
            result_parts.append(content)
    
    return result_parts

def group_consecutive_text(text):
    """Group consecutive characters by type (Lao, English, punctuation, numbers)."""
    if not text:
        return []
    
    groups = []
    current_group = ''
    current_type = None
    
    for char in text:
        if char == '…':
            char_type = 'ellipsis'
        elif char == 'ໆ':
            char_type = 'lao_repetition'
        elif is_lao_text(char):
            char_type = 'lao'
        elif char.isalpha():
            char_type = 'english'
        elif char.isdigit():
            char_type = 'number'
        elif is_punctuation(char):
            char_type = 'punctuation'
        elif char.isspace():
            char_type = 'space'
        else:
            char_type = 'other'
        
        if char_type == current_type:
            current_group += char
        else:
            if current_group:
                groups.append((current_type, current_group))
            current_group = char
            current_type = char_type
    
    if current_group:
        groups.append((current_type, current_group))
    
    return groups

def find_lao_word_boundary(text, start_pos):
    """Find the end of the current Lao word starting at start_pos."""
    pos = start_pos
    
    while pos < len(text):
        char = text[pos]
        
        # Stop at spaces, punctuation, or non-Lao characters
        if (char.isspace() or 
            is_punctuation(char) or 
            not is_lao_text(char) or
            char.isdigit()):
            break
        pos += 1
    
    return pos

def needs_nobreak_protection(text):
    """Check if text needs nobreak protection (ends with \\lw{} or \\nodict{} or is Lao repeat)."""
    return (text.endswith('}') or 
            text in ['\\laorepeat', '\\laorepeatbefore'])

def find_next_lao_word_break(text, start_pos, dictionary):
    """
    Find the next reasonable word break in continuous Lao text.
    Try to isolate unknown words as small units rather than entire text.
    """
    # Start with minimum length and work up
    max_search_length = min(20, len(text) - start_pos)  # Don't search beyond reasonable word length
    
    # Try progressively longer segments to find where dictionary matching resumes
    for test_length in range(1, max_search_length + 1):
        test_end = start_pos + test_length
        
        # Check if text starting at test_end matches any dictionary term
        remaining_text = text[test_end:]
        if remaining_text:  # Make sure there's still text to check
            for term in dictionary.get_sorted_terms():
                if remaining_text.startswith(term):
                    # Found a dictionary match starting at test_end
                    # So our unknown segment should be text[start_pos:test_end]
                    return test_end
    
    # If no dictionary match found in reasonable distance, 
    # look for natural Lao syllable boundaries (basic approach)
    for i in range(start_pos + 1, min(start_pos + 10, len(text))):
        char = text[i]
        # Look for likely syllable boundaries (tone marks, vowels followed by consonants)
        if char in 'ເແໂໃໄ':  # Leading vowels often start new syllables
            return i
        # Could add more sophisticated Lao syllable detection here
    
    # Fallback: return a reasonable chunk (don't go to end of entire text)
    return min(start_pos + 6, len(text))  # Max 6 characters if no pattern found

def lookup_lao_words(lao_text, dictionary):
    """Apply dictionary lookup to pure Lao text only."""
    sorted_terms = dictionary.get_sorted_terms()
    result_parts = []
    position = 0
    
    while position < len(lao_text):
        matched = False
        
        # Try to match dictionary terms
        for term in sorted_terms:
            if lao_text[position:position + len(term)] == term:
                coded_term = dictionary.terms[term]
                converted_term = convert_break_points(coded_term)
                result_parts.append(f'\\lw{{{converted_term}}}')
                position += len(term)
                matched = True
                break
        
        if not matched:
            # Find a reasonable word break instead of going to the end
            word_end = find_next_lao_word_break(lao_text, position, dictionary)
            unknown_word = lao_text[position:word_end]
            
            # Debug: Log all \nodict{} entries to a file
            debug_file = get_project_root() / "04_assets" / "temp" / "nodict_terms.log"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_file, 'a', encoding='utf-8') as f:
                f.write(f"{unknown_word}\n")
            
            result_parts.append(f'\\nodict{{{unknown_word}}}')
            position = word_end
    
    return ''.join(result_parts)

# Add this helper function to generate a clean unique list
def generate_unique_nodict_report():
    """Generate a unique, sorted list of all \nodict{} terms found."""
    debug_file = get_project_root() / "04_assets" / "temp" / "nodict_terms.log"
    unique_file = get_project_root() / "04_assets" / "temp" / "unique_nodict_terms.txt"
    
    if debug_file.exists():
        # Read all terms, remove duplicates, sort by frequency
        with open(debug_file, 'r', encoding='utf-8') as f:
            terms = [line.strip() for line in f if line.strip()]
        
        # Count frequency and create unique sorted list
        from collections import Counter
        term_counts = Counter(terms)
        
        with open(unique_file, 'w', encoding='utf-8') as f:
            f.write("# Unique \\nodict{} terms found (frequency: term)\n")
            for term, count in term_counts.most_common():
                f.write(f"{count}: {term}\n")
        
        print(f"Generated unique nodict report: {unique_file}")
        print(f"Found {len(term_counts)} unique missing terms")
    else:
        print("No nodict terms found")

def process_tex_command_with_lao(line, dictionary):
    """Process TeX commands that contain Lao text in braces."""
    
    def replace_lao_in_braces(match):
        content = match.group(1)
        if is_lao_text(content):
            return '{' + lookup_lao_words(content, dictionary) + '}'
        else:
            return match.group(0)  # Return unchanged if no Lao
    
    # Pattern to match content within braces
    pattern = r'\{([^}]+)\}'
    processed_line = re.sub(pattern, replace_lao_in_braces, line)
    
    return processed_line

def extract_and_preserve_commands(text):
    """Extract \\egw{}, footnote markers, and flex/rigid spaces, replace with placeholders."""
    import re
    
    protected_commands = []
    placeholder_text = text
    
    # Find all \egw{...} commands
    egw_pattern = r'\\egw\{[^}]+\}'
    matches = re.finditer(egw_pattern, text)
    
    for i, match in enumerate(matches):
        command = match.group(0)
        placeholder = f'__PROTECTED_CMD_{i}__'
        protected_commands.append(command)
        placeholder_text = placeholder_text.replace(command, placeholder, 1)
    
    # Find all footnote markers [^1], [^2], etc. and [^1]:, [^2]:, etc.
    footnote_pattern = r'\[\^\d+\](?::)?'
    matches = re.finditer(footnote_pattern, placeholder_text)
    
    for match in matches:
        command = match.group(0)
        placeholder = f'__PROTECTED_CMD_{len(protected_commands)}__'
        protected_commands.append(command)
        placeholder_text = placeholder_text.replace(command, placeholder, 1)
    
    # Find \s and \S flex/rigid space markers (not followed by letters to avoid \section, \source, etc.)
    flex_pattern = r'\\[sS](?![a-zA-Z])'
    matches = re.finditer(flex_pattern, placeholder_text)
    
    # Process matches in reverse order to avoid position shifts
    for match in reversed(list(matches)):
        command = match.group(0)
        placeholder = f'__PROTECTED_CMD_{len(protected_commands)}__'
        protected_commands.append(command)
        placeholder_text = placeholder_text[:match.start()] + placeholder + placeholder_text[match.end():]
    
    return placeholder_text, protected_commands

def restore_protected_commands(text, protected_commands):
    """Restore protected commands from placeholders, converting flex/rigid spaces."""
    result = text
    for i, command in enumerate(protected_commands):
        placeholder = f'__PROTECTED_CMD_{i}__'
        
        # Convert flex/rigid space markers to LaTeX commands
        if command == '\\s':
            converted_command = '\\fs'
        elif command == '\\S':
            converted_command = '\\rs'
        else:
            converted_command = command  # Keep other commands unchanged
        
        result = result.replace(placeholder, converted_command)
    
    return result

def handle_lao_repetition_context(groups, current_index):
    """Determine appropriate Lao repetition command based on following punctuation."""
    # Check if next group is punctuation
    if current_index < len(groups) - 1:
        next_type, next_content = groups[current_index + 1]
        if next_type == 'punctuation':
            return "\\laorepeatbefore"
    
    return "\\laorepeat"

def handle_ellipsis_context(groups, current_index):
    """Determine appropriate ellipsis command based on surrounding punctuation."""
    # Check if previous group is punctuation
    previous_is_punctuation = False
    if current_index > 0:
        prev_type, prev_content = groups[current_index - 1]
        if prev_type == 'punctuation':
            previous_is_punctuation = True
    
    # Check if next group is punctuation
    next_is_punctuation = False
    if current_index < len(groups) - 1:
        next_type, next_content = groups[current_index + 1]
        if next_type == 'punctuation':
            next_is_punctuation = True
    
    # Return appropriate ellipsis command
    if previous_is_punctuation:
        return "\\ellafter"
    elif next_is_punctuation:
        return "\\ellbefore"
    else:
        return "\\ellipsis"

def process_text_line(text, dictionary):
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
            processed = process_tex_command_with_lao(placeholder_text, dictionary)
            return restore_protected_commands(processed, protected_commands)
        # Other TeX commands pass through unchanged
        return text  # Return original text, not placeholder
    
    # Process regular text content
    groups = group_consecutive_text(placeholder_text)
    
    # Step 1: Process text groups through dictionary
    processed_parts = process_text_groups(groups, dictionary)
    
    # Step 2: Apply punctuation protection
    protected_parts = apply_punctuation_protection(processed_parts)
    
    # Step 3: Join and restore protected commands
    processed_text = ''.join(protected_parts)
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
            # Apply dictionary processing to each line
            processed_line = process_text_line(line, dictionary)
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
    """Get the project root directory based on script location."""
    script_dir = Path(__file__).parent
    return script_dir.parent.parent

def get_dictionary_path():
    """Get the path to the dictionary file."""
    script_dir = Path(__file__).parent
    return script_dir / '../../../../lo/assets/dictionaries/main.txt'

def get_input_files(args):
    """Get list of .tmp files to process."""
    project_root = get_project_root()
    temp_dir = project_root / '04_assets' / 'temp'
    
    if args.files:
        # Process specific files
        input_files = []
        for filename in args.files:
            if filename.endswith('.tmp'):
                input_files.append(temp_dir / filename)
            else:
                # Assume it's a base name, look for stage1.tmp or .tmp
                stage1_file = temp_dir / f"{filename}_stage1.tmp"
                base_file = temp_dir / f"{filename}.tmp"
                
                if stage1_file.exists():
                    input_files.append(stage1_file)
                elif base_file.exists():
                    input_files.append(base_file)
                else:
                    print(f"Warning: Could not find .tmp file for {filename}")
        return input_files
    else:
        # Process all .tmp files in temp directory
        if not temp_dir.exists():
            print(f"Error: {temp_dir} directory not found")
            sys.exit(1)
        
        if args.debug:
            # Debug mode: look for stage1 files from Module 1 debug output
            stage1_files = list(temp_dir.glob('*_stage1.tmp'))
            if stage1_files:
                return stage1_files
            # Fall back to tmp files if no stage1 files
            tmp_files = list(temp_dir.glob('*.tmp'))
            if not tmp_files:
                print(f"No .tmp files found in {temp_dir}")
                sys.exit(1)
            return tmp_files
        else:
            # Production mode: only process tmp files (ignore any stale stage1)
            tmp_files = list(temp_dir.glob('*.tmp'))
            if not tmp_files:
                print(f"No .tmp files found in {temp_dir}")
                sys.exit(1)
            return tmp_files

def get_output_path(input_path, debug_mode=False):
    """Generate output path based on input path and mode."""
    input_file = Path(input_path)
    
    if debug_mode:
        # stage1.tmp -> stage2.tmp, or .tmp -> stage2.tmp
        if input_file.stem.endswith('_stage1'):
            base_name = input_file.stem.replace('_stage1', '')
            output_name = f"{base_name}_stage2.tmp"
        else:
            base_name = input_file.stem
            output_name = f"{base_name}_stage2.tmp"
    else:
        # stage1.tmp -> .tmp, or .tmp -> .tmp (overwrite)
        if input_file.stem.endswith('_stage1'):
            base_name = input_file.stem.replace('_stage1', '')
            output_name = f"{base_name}.tmp"
        else:
            output_name = input_file.name  # Keep same name (overwrite)
    
    return input_file.parent / output_name

def main():
    parser = argparse.ArgumentParser(
        description="Module 2: Dictionary Lookup and Line-Breaking Application"
    )
    parser.add_argument(
        'files', 
        nargs='*', 
        help='Temp files to process (default: all .tmp files in 04_assets/temp/)'
    )
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='Enable debug mode (create stage2 files)'
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Load dictionary
    dictionary_path = get_dictionary_path()
    dictionary = LaoDictionary(dictionary_path)
    
    # Get input files
    input_files = get_input_files(args)
    
    if not input_files:
        print("No input files to process")
        sys.exit(1)
    
    # Process files
    success_count = 0
    total_count = len(input_files)
    
    print(f"Processing {total_count} file(s) in {'debug' if args.debug else 'production'} mode...")
    
    for input_file in input_files:
        input_path = str(input_file)
        output_path = str(get_output_path(input_file, args.debug))
        
        if process_file(input_path, output_path, dictionary, args.verbose or args.debug):
            success_count += 1
    
    print(f"\nCompleted: {success_count}/{total_count} files processed successfully")
    
    if success_count < total_count:
        sys.exit(1)

def generate_unique_nodict_report():
    """Generate a unique, sorted list of all \nodict{} terms found."""
    debug_file = get_project_root() / "04_assets" / "temp" / "nodict_terms.log"
    unique_file = get_project_root() / "04_assets" / "temp" / "unique_nodict_terms.txt"
    
    if debug_file.exists():
        # Read all terms, remove duplicates, sort by frequency
        with open(debug_file, 'r', encoding='utf-8') as f:
            terms = [line.strip() for line in f if line.strip()]
        
        # Count frequency and create unique sorted list
        from collections import Counter
        term_counts = Counter(terms)
        
        with open(unique_file, 'w', encoding='utf-8') as f:
            f.write("# Unique \\nodict{} terms found (frequency: term)\n")
            for term, count in term_counts.most_common():
                f.write(f"{count}: {term}\n")
        
        print(f"Generated unique nodict report: {unique_file}")
        print(f"Found {len(term_counts)} unique missing terms")
    else:
        print("No nodict terms found")

if __name__ == "__main__":
    main()
    generate_unique_nodict_report()