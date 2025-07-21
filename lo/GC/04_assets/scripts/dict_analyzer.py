#!/usr/bin/env python3
"""
NoDict Context Analysis and Dictionary Validation Tool

Analyzes \nodict{} terms in processed files to help identify dictionary gaps
and validates dictionary for Unicode normalization issues.

This module is called by Module 2 to generate analysis reports for \nodict{} terms
and check dictionary quality. If this file doesn't exist, Module 2 will continue 
without generating reports.

USAGE:
- Called automatically by Module 2 after processing (debug mode only)
- Can be run standalone: python3 nodict_context_analyzer.py
- Generates: 04_assets/temp/nodict_analysis.log

FEATURES:
- Context analysis: Shows 4 words before/after each \nodict{} term
- Dictionary validation: Checks for improper Unicode sequences (ໍ+າ patterns)
- Groups identical \nodict{} terms for easy pattern recognition
- Helps identify missing dictionary entries and compound words
"""

import re
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional

# =============================================================================
# DICTIONARY VALIDATION FUNCTIONS
# =============================================================================

def check_dictionary_duplicates(dictionary_path: Path) -> List[str]:
    """Check dictionary for duplicate entries."""
    if not dictionary_path.exists():
        return [f"Dictionary file not found: {dictionary_path}"]
    
    duplicates = []
    seen_terms = {}  # clean_term -> list of line numbers
    
    try:
        with open(dictionary_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                clean_term = _extract_clean_term(line)
                if clean_term:
                    seen_terms.setdefault(clean_term, []).append(line_num)
        
        # Find duplicates
        for term, line_numbers in seen_terms.items():
            if len(line_numbers) > 1:
                lines_str = ", ".join(map(str, line_numbers))
                duplicates.append(f"{term} (lines: {lines_str})")
                
    except Exception as e:
        duplicates.append(f"Error reading dictionary: {e}")
    
    return duplicates

def check_dictionary_unicode_issues(dictionary_path: Path) -> List[str]:
    """Check dictionary for improper Unicode sequences that need normalization."""
    if not dictionary_path.exists():
        return [f"Dictionary file not found: {dictionary_path}"]
    
    issues = []
    
    try:
        with open(dictionary_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Check for ໍ + optional tone mark + າ sequences
                if re.search(r'ໍ[່້໊໋]?າ', line):
                    issues.append(f"Line {line_num}: {line.strip()}")
    except Exception as e:
        issues.append(f"Error reading dictionary: {e}")
    
    return issues

def _extract_clean_term(line: str) -> Optional[str]:
    """Extract clean term from dictionary line, return None if invalid."""
    line = line.strip()
    
    # Skip empty lines and comments
    if not line or line.startswith('%') or '|' not in line:
        return None
    
    parts = line.split('|', 1)
    if len(parts) != 2:
        return None
    
    clean_term = parts[0].strip()
    return clean_term if clean_term else None

def analyze_dictionary_quality(dictionary_path: Path) -> Dict[str, List[str]]:
    """Run all dictionary quality checks and return results."""
    return {
        'duplicates': check_dictionary_duplicates(dictionary_path),
        'unicode_issues': check_dictionary_unicode_issues(dictionary_path)
    }

# =============================================================================
# TEXT PROCESSING FUNCTIONS
# =============================================================================

def extract_word_tokens(text: str) -> List[Tuple[str, str]]:
    """Extract word tokens from processed text."""
    tokens = []
    pattern = r'\\(lw|nodict)\{([^}]+)\}'
    current_pos = 0
    
    for match in re.finditer(pattern, text):
        # Add any text before this match
        _add_between_text(tokens, text, current_pos, match.start())
        
        # Add the matched command
        cmd_type = match.group(1)  # 'lw' or 'nodict'
        content = match.group(2)   # content inside braces
        tokens.append((cmd_type, content))
        
        current_pos = match.end()
    
    # Add any remaining text
    _add_between_text(tokens, text, current_pos, len(text))
    
    return tokens

def _add_between_text(tokens: List[Tuple[str, str]], text: str, start: int, end: int):
    """Helper to add text between matches to token list."""
    if end > start:
        between_text = text[start:end]
        if between_text.strip():
            if between_text == '\\space':
                tokens.append(('space', ' '))
            elif between_text.startswith('\\'):
                tokens.append(('command', between_text))
            else:
                tokens.append(('other', between_text))

def extract_context_windows(tokens: List[Tuple[str, str]], window_size: int = 4) -> Dict[str, List[List[str]]]:
    """Extract context windows around \nodict{} terms."""
    nodict_contexts = defaultdict(list)
    
    for i, (token_type, content) in enumerate(tokens):
        if token_type == 'nodict':
            context = _build_context_window(tokens, i, window_size)
            nodict_contexts[content].append(context)
    
    return nodict_contexts

def _build_context_window(tokens: List[Tuple[str, str]], center_index: int, window_size: int) -> List[str]:
    """Build context window around a specific token index."""
    context = []
    
    # Get words before
    before_words = _get_words_before(tokens, center_index, window_size)
    context.extend(before_words)
    
    # Add the nodict term itself with markers
    center_content = tokens[center_index][1]
    context.append(f"*{center_content}*")
    
    # Get words after
    after_words = _get_words_after(tokens, center_index, window_size)
    context.extend(after_words)
    
    return context

def _get_words_before(tokens: List[Tuple[str, str]], center_index: int, window_size: int) -> List[str]:
    """Get words before the center index, respecting sentence boundaries."""
    words = []
    count = 0
    
    for i in range(center_index - 1, -1, -1):
        token_type, content = tokens[i]
        
        if token_type in ['lw', 'nodict']:
            words.insert(0, content)
            count += 1
            if count >= window_size:
                break
        elif _is_sentence_boundary(token_type, content):
            break
    
    return words

def _get_words_after(tokens: List[Tuple[str, str]], center_index: int, window_size: int) -> List[str]:
    """Get words after the center index, respecting sentence boundaries."""
    words = []
    count = 0
    
    for i in range(center_index + 1, len(tokens)):
        token_type, content = tokens[i]
        
        if token_type in ['lw', 'nodict']:
            words.append(content)
            count += 1
            if count >= window_size:
                break
        elif _is_sentence_boundary(token_type, content):
            break
    
    return words

def _is_sentence_boundary(token_type: str, content: str) -> bool:
    """Check if token represents a sentence boundary."""
    return token_type == 'other' and any(punct in content for punct in '.!?;')

def clean_lw_content(content: str) -> str:
    """Remove TeX commands from \lw{} content to get clean text."""
    # Remove penalty commands like \p{1000}
    content = re.sub(r'\\p\{[^}]+\}', '', content)
    # Remove other common commands
    content = re.sub(r'\\cs', '', content)
    return content.strip()

# =============================================================================
# FILE ANALYSIS FUNCTIONS
# =============================================================================

def analyze_file(file_path: Path) -> Dict[str, List[List[str]]]:
    """Analyze a single processed file for nodict contexts."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tokens = extract_word_tokens(content)
        contexts = extract_context_windows(tokens)
        return contexts
        
    except Exception as e:
        print(f"Warning: Could not analyze {file_path}: {e}")
        return {}

def analyze_temp_directory(temp_dir: Path) -> Dict[str, List[List[str]]]:
    """Analyze all processed .tmp files in the temp directory."""
    files_to_analyze = _get_files_to_analyze(temp_dir)
    all_contexts = defaultdict(list)
    
    for file_path in files_to_analyze:
        file_contexts = analyze_file(file_path)
        
        # Merge contexts
        for term, contexts in file_contexts.items():
            all_contexts[term].extend(contexts)
    
    return all_contexts

def _get_files_to_analyze(temp_dir: Path) -> List[Path]:
    """Get list of files to analyze, preferring stage2 files."""
    # Look for stage2 files first (debug mode), then regular .tmp files
    stage2_files = list(temp_dir.glob('*_stage2.tmp'))
    if stage2_files:
        return stage2_files
    
    # Fall back to regular .tmp files, excluding stage1
    tmp_files = list(temp_dir.glob('*.tmp'))
    return [f for f in tmp_files if not f.stem.endswith('_stage1')]

# =============================================================================
# REPORT FORMATTING FUNCTIONS
# =============================================================================

def format_duplicate_report(duplicates: List[str]) -> List[str]:
    """Format duplicate check results."""
    lines = ["=== DICTIONARY DUPLICATE CHECK ===", ""]
    
    if duplicates:
        lines.extend([
            f"⚠️  DUPLICATE ENTRIES FOUND ({len(duplicates)} terms):",
            ""
        ])
        for duplicate in duplicates:
            lines.append(f"  {duplicate}")
        lines.extend([
            "",
            "These duplicate entries should be reviewed and consolidated."
        ])
    else:
        lines.append("✅ No duplicate entries found")
    
    return lines

def format_unicode_report(unicode_issues: List[str]) -> List[str]:
    """Format Unicode validation results."""
    lines = ["=== DICTIONARY UNICODE VALIDATION ===", ""]
    
    if unicode_issues:
        lines.extend([
            f"⚠️  UNICODE ISSUES FOUND ({len(unicode_issues)} entries):",
            "The following entries contain improper ໍ+າ sequences that need manual correction:",
            ""
        ])
        for issue in unicode_issues:
            lines.append(f"  {issue}")
        lines.extend([
            "",
            "These entries need to be manually corrected in the dictionary file."
        ])
    else:
        lines.append("✅ No Unicode normalization issues found")
    
    return lines

def format_context_report(nodict_contexts: Dict[str, List[List[str]]]) -> List[str]:
    """Format nodict context analysis results."""
    if not nodict_contexts:
        return [
            "=== NODICT CONTEXT ANALYSIS ===",
            "✅ No \\nodict{} terms found for context analysis"
        ]
    
    lines = [
        "=== NODICT CONTEXT ANALYSIS REPORT ===",
        f"Generated: {Path().cwd()}",
        ""
    ]
    
    # Sort by frequency (most common first)
    sorted_terms = sorted(nodict_contexts.items(), 
                         key=lambda x: len(x[1]), reverse=True)
    
    for term, contexts in sorted_terms:
        lines.append(f"{term} (found {len(contexts)} times):")
        
        unique_contexts = _get_unique_contexts(contexts)
        for context_str in unique_contexts[:10]:  # Limit to 10 examples
            lines.append(f"  {context_str}")
        
        if len(contexts) > 10:
            lines.append(f"  ... and {len(contexts) - 10} more contexts")
        
        lines.append("")  # Empty line between terms
    
    return lines

def _get_unique_contexts(contexts: List[List[str]]) -> List[str]:
    """Get unique context strings, cleaning lw content."""
    unique_contexts = []
    
    for context in contexts:
        clean_context = []
        for word in context:
            if word.startswith('*') and word.endswith('*'):
                clean_context.append(word)  # Keep nodict terms marked
            else:
                clean_word = clean_lw_content(word)
                if clean_word:
                    clean_context.append(clean_word)
        
        context_str = ' '.join(clean_context)
        if context_str not in unique_contexts:
            unique_contexts.append(context_str)
    
    return unique_contexts

def build_analysis_report(dictionary_path: Path, quality_results: Dict[str, List[str]], 
                         nodict_contexts: Dict[str, List[List[str]]]) -> List[str]:
    """Build the complete analysis report."""
    report_lines = []
    
    # Add dictionary path header
    report_lines.extend([f"Dictionary: {dictionary_path}", ""])
    
    # 1. Duplicates section
    report_lines.extend(format_duplicate_report(quality_results['duplicates']))
    report_lines.extend(["", "=" * 50, ""])
    
    # 2. Unicode issues section  
    report_lines.extend(format_unicode_report(quality_results['unicode_issues']))
    report_lines.extend(["", "=" * 50, ""])
    
    # 3. Context analysis section
    report_lines.extend(format_context_report(nodict_contexts))
    
    return report_lines

def write_analysis_report(report_lines: List[str], output_file: Path) -> bool:
    """Write the analysis report to file."""
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        return True
    except Exception as e:
        print(f"Warning: Could not write analysis report: {e}")
        return False

def print_console_summary(quality_results: Dict[str, List[str]], 
                         nodict_contexts: Dict[str, List[List[str]]], 
                         output_file: Path):
    """Print summary to console."""
    print(f"Generated analysis report: {output_file}")
    
    # Dictionary quality summary
    duplicates = quality_results['duplicates']
    unicode_issues = quality_results['unicode_issues']
    
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} dictionary duplicates - see log for details")
    else:
        print("✅ Dictionary duplicate check passed")
        
    if unicode_issues:
        print(f"⚠️  Found {len(unicode_issues)} dictionary Unicode issues - see log for details")
    else:
        print("✅ Dictionary Unicode validation passed")
        
    if nodict_contexts:
        print(f"📊 Found {len(nodict_contexts)} unique \\nodict{{}} terms")

# =============================================================================
# MAIN ORCHESTRATION FUNCTION
# =============================================================================

def generate_context_report(project_root: Path = None):
    """Generate the complete nodict context analysis report."""
    # Setup paths
    if project_root is None:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
    
    temp_dir = project_root / "04_assets" / "temp"
    output_file = temp_dir / "nodict_analysis.log"
    dictionary_path = project_root / "04_assets" / "scripts" / "../../../../lo/assets/dictionaries/main.txt"
    
    if not temp_dir.exists():
        print(f"Warning: {temp_dir} not found, skipping context analysis")
        return
    
    # Run analysis
    quality_results = analyze_dictionary_quality(dictionary_path)
    nodict_contexts = analyze_temp_directory(temp_dir)
    
    # Generate and write report
    report_lines = build_analysis_report(dictionary_path, quality_results, nodict_contexts)
    
    if write_analysis_report(report_lines, output_file):
        print_console_summary(quality_results, nodict_contexts, output_file)

def main():
    """Standalone execution."""
    generate_context_report()

if __name__ == "__main__":
    main()