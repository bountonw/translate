#!/usr/bin/env python3
"""
Module 2 Debug Support
Debug and logging functionality for Lao text preprocessing Module 2.

This module provides detailed logging and analysis for the lookahead algorithm
and dictionary processing. It's optional - if this file doesn't exist, Module 2
will run in production mode without debug features.

FEATURES:
- Lookahead decision logging with narrative format
- Strategy comparison analysis
- Dictionary source conflict tracking
- Console output for interesting parsing decisions
- Integration with dict_analyzer.py for comprehensive reporting

USAGE:
- Automatically imported by Module 2 when --debug flag is used
- Creates lookahead_decisions.log for detailed parsing decisions
- Creates dictionary_sources.log for terms with multiple sources
- Works with dict_analyzer.py for complete analysis reports
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Global counters for session tracking
session_stats = {
    'decisions_made': 0,
    'strategy_changes': 0,
    'interesting_cases': 0
}

# =============================================================================
# DICTIONARY SOURCE CONFLICT LOGGING
# =============================================================================

def log_dictionary_conflicts(conflicts: Dict[str, Dict[str, str]], project_root: Path = None):
    """
    Log terms that appear in multiple dictionary sources.
    
    Args:
        conflicts: Dict mapping term -> {source_name: coded_term}
        project_root: Project root path for log file location
    """
    if not conflicts:
        return  # No conflicts to log
    
    try:
        if project_root is None:
            script_dir = Path(__file__).parent
            project_root = script_dir.parent.parent
            
        log_file = project_root / "04_assets" / "temp" / "dictionary_sources.log"
        
        # Priority order for display (highest to lowest)
        priority_order = [
            "Chapter patch",
            "Chapter",
            "Book patch", 
            "Book",
            "Language patch",
            "Language main"
        ]
        
        log_entries = []
        log_entries.append("DICTIONARY SOURCE CONFLICTS")
        log_entries.append("=" * 60)
        log_entries.append("")
        log_entries.append("Terms found in multiple dictionary sources:")
        log_entries.append("(Listed in priority order - highest priority source determines final encoding)")
        log_entries.append("")
        
        for term, sources in sorted(conflicts.items()):
            log_entries.append(f"Term: {term}")
            
            # Sort sources by priority
            sorted_sources = []
            for priority_name in priority_order:
                for source_name, coded_term in sources.items():
                    if priority_name.lower() in source_name.lower():
                        sorted_sources.append((source_name, coded_term))
                        break
            
            # Add any sources not in priority list
            for source_name, coded_term in sources.items():
                if not any(source_name in [s[0] for s in sorted_sources]):
                    sorted_sources.append((source_name, coded_term))
            
            # Mark the final (highest priority) source
            for i, (source_name, coded_term) in enumerate(sorted_sources):
                if i == 0:  # First in sorted list = highest priority
                    log_entries.append(f"  {source_name}: {coded_term} ← FINAL")
                else:
                    log_entries.append(f"  {source_name}: {coded_term}")
            
            log_entries.append("")
        
        log_entries.append(f"Total conflicting terms: {len(conflicts)}")
        log_entries.append("")
        
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_entries))
            
    except Exception as e:
        pass

def print_dictionary_conflict_summary(conflict_count: int):
    """Print summary of dictionary conflicts to console."""
    if conflict_count > 0:
        print(f"Dictionary conflicts logged to dictionary_sources.log ({conflict_count} terms)")
    else:
        print("Dictionary duplicate check passed")

# =============================================================================
# LOOKAHEAD DECISION LOGGING
# =============================================================================

def log_lookahead_decision(text: str, alternatives: List[List[Dict[str, Any]]], 
                          selected_strategy: int, scored_alternatives: List[Tuple], 
                          project_root: Path = None):
    """Log interesting lookahead decisions in narrative format."""
    global session_stats
    
    strategy_names = ["longest-first", "shortest-first", "backtrack"]
    session_stats['decisions_made'] += 1
    
    # Check if strategies produced different results
    if not _strategies_differ(alternatives):
        return  # All strategies agree, nothing interesting to log
    
    session_stats['interesting_cases'] += 1
    
    # Only count as strategy change if we didn't select longest-first (baseline)
    if selected_strategy != 0:
        session_stats['strategy_changes'] += 1
    
    # Only log when we actually change from longest-first AND results differ
    if selected_strategy == 0 or not _results_actually_differ(alternatives[0], alternatives[selected_strategy]):
        return  # No actual change, don't log
    
    # File logging only - no console output
    try:
        if project_root is None:
            script_dir = Path(__file__).parent
            project_root = script_dir.parent.parent
            
        log_file = project_root / "04_assets" / "temp" / "lookahead_decisions.log"
        
        selected_name = strategy_names[selected_strategy]
        improvement_description = _describe_improvement(alternatives, selected_strategy)
        
        # Build strategy comparison lines
        comparison_lines = []
        for score, alt, strategy_idx in scored_alternatives:
            strategy_name = strategy_names[strategy_idx]
            parse_description = _describe_parse_result(alt)
            comparison_lines.append(f"{strategy_name:<15} (score: {score:3d}): {parse_description}")
        
        # Find fragments created
        fragments = _find_fragments_created(alternatives[0], alternatives[selected_strategy])
        
        # Create formatted log entry
        log_entry = [
            f'{"="*60}',
            f'STRATEGY CHANGE: {selected_name}',
            f'Text: "{text}"',
            "",
            "STRATEGY COMPARISON:",
            *comparison_lines,
            "",
            f'DECISION: Selected {selected_name} (score: {scored_alternatives[selected_strategy][0]})',
            f'FRAGMENTS CREATED: {fragments}' if fragments else 'FRAGMENTS CREATED: None',
            f'IMPROVEMENT: {improvement_description}',
            f'{"="*60}',
            ""
        ]
        
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write('\n'.join(log_entry))
            
    except Exception as e:
        pass

def _find_fragments_created(original_result: List[Dict[str, Any]], new_result: List[Dict[str, Any]]) -> str:
    """Find which words were fragmented between two parse results."""
    original_words = [seg['text'] for seg in original_result if seg['type'] == 'dict']
    new_words = [seg['text'] for seg in new_result if seg['type'] == 'dict']
    
    fragments = []
    for orig_word in original_words:
        if orig_word not in new_words:
            # This word was broken up, find what it became
            # Simple approach: look for consecutive words that together make the original
            for i in range(len(new_words) - 1):
                if orig_word.startswith(new_words[i]):
                    remaining = orig_word[len(new_words[i]):]
                    if i + 1 < len(new_words) and remaining == new_words[i + 1]:
                        fragments.append(f"{orig_word} → {new_words[i]} + {new_words[i + 1]}")
                        break
    
    return ", ".join(fragments) if fragments else "None"

def _results_actually_differ(result1: List[Dict[str, Any]], result2: List[Dict[str, Any]]) -> bool:
    """Check if two parse results are actually different (not just scored differently)."""
    if len(result1) != len(result2):
        return True
    
    for seg1, seg2 in zip(result1, result2):
        if seg1['text'] != seg2['text'] or seg1['type'] != seg2['type']:
            return True
    
    return False

def _strategies_differ(alternatives: List[List[Dict[str, Any]]]) -> bool:
    """Check if different strategies produced meaningfully different results."""
    if len(alternatives) < 2:
        return False
    
    # Compare structure of results
    first_structure = _get_parse_structure(alternatives[0])
    
    for alt in alternatives[1:]:
        if _get_parse_structure(alt) != first_structure:
            return True
    
    return False

def _get_parse_structure(parse_result: List[Dict[str, Any]]) -> str:
    """Get a string representation of parse structure for comparison."""
    parts = []
    for segment in parse_result:
        if segment['type'] == 'dict':
            parts.append(f"D:{len(segment['text'])}")  # Dict with length
        else:
            parts.append(f"N:{len(segment['text'])}")  # Nodict with length
    return "|".join(parts)

def _describe_improvement(alternatives: List[List[Dict[str, Any]]], selected_idx: int) -> str:
    """Describe what kind of improvement the selected strategy made."""
    longest_first = alternatives[0]
    selected = alternatives[selected_idx]
    
    longest_nodicts = sum(1 for seg in longest_first if seg['type'] == 'nodict')
    selected_nodicts = sum(1 for seg in selected if seg['type'] == 'nodict')
    
    if selected_nodicts < longest_nodicts:
        return "Reduced fragmentation"
    elif selected_nodicts == longest_nodicts:
        # Check if nodict segments got smaller
        longest_nodict_chars = sum(len(seg['text']) for seg in longest_first if seg['type'] == 'nodict')
        selected_nodict_chars = sum(len(seg['text']) for seg in selected if seg['type'] == 'nodict')
        
        if selected_nodict_chars < longest_nodict_chars:
            return "Improved word boundaries"
        else:
            return "Optimized parsing"
    else:
        return "Alternative parsing"

def _describe_parse_result(parse_result: List[Dict[str, Any]]) -> str:
    """Create human-readable description of parse result."""
    parts = []
    
    for segment in parse_result:
        if segment['type'] == 'dict':
            # Clean the dictionary term for display
            clean_text = _clean_tex_commands(segment['text'])
            parts.append(f"[{clean_text}]")
        else:
            parts.append(f"nodict{{{segment['text']}}}")
    
    return " + ".join(parts)

def _clean_tex_commands(text: str) -> str:
    """Remove TeX commands from text for clean display."""
    # Remove penalty commands like \p{1000}
    text = re.sub(r'\\p\{[^}]+\}', '', text)
    # Remove compound space commands
    text = re.sub(r'\\cs', '', text)
    return text.strip()

# =============================================================================
# DEBUG STATISTICS AND REPORTING
# =============================================================================

def print_lookahead_summary(decisions_made: int, strategy_changes: int, debug: bool = False):
    """Print summary of lookahead processing to console."""
    if debug and decisions_made > 0:
        print(f"✅ Processed: {decisions_made} lookahead decisions, {strategy_changes} strategy changes")

def clear_debug_logs(project_root: Path):
    """Clear previous debug logs at start of processing."""
    try:
        log_files = [
            project_root / "04_assets" / "temp" / "lookahead_decisions.log",
            project_root / "04_assets" / "temp" / "dictionary_sources.log"
        ]
        for log_file in log_files:
            if log_file.exists():
                log_file.unlink()
    except Exception:
        pass

# =============================================================================
# INTEGRATION WITH DICT_ANALYZER
# =============================================================================

def call_dict_analyzer(project_root: Path, processed_files: List[Path] = None):
    """Call the dictionary analyzer for comprehensive reporting."""
    try:
        # Import and call the main analyzer
        from dict_analyzer import generate_context_report
        generate_context_report(project_root, processed_files)
        return True
    except ImportError:
        # dict_analyzer.py doesn't exist, continue silently
        return False
    except Exception as e:
        # Other errors, warn but don't fail
        print(f"Warning: Dictionary analysis failed: {e}")
        return False

# =============================================================================
# MAIN DEBUG ORCHESTRATION
# =============================================================================

def initialize_debug_session(project_root: Path):
    """Initialize debug session - clear old logs, prepare for new session."""
    clear_debug_logs(project_root)

def finalize_debug_session(project_root: Path, total_files: int, success_count: int, 
                          processed_files: List[Path] = None, dictionary_conflicts: Dict[str, Dict[str, str]] = None):
    """Finalize debug session - generate comprehensive reports."""
    # Log dictionary conflicts if any
    if dictionary_conflicts:
        log_dictionary_conflicts(dictionary_conflicts, project_root)
        print_dictionary_conflict_summary(len(dictionary_conflicts))
    else:
        print_dictionary_conflict_summary(0)
    
    # Call the dictionary analyzer for comprehensive reporting
    analysis_success = call_dict_analyzer(project_root, processed_files)
    
    # Summary info
    if analysis_success:
        # Check if we generated any lookahead decisions
        decisions_file = project_root / "04_assets" / "temp" / "lookahead_decisions.log"
        if decisions_file.exists():
            print(f"🔍 Generated lookahead decisions log")
        else:
            print(f"✅ No lookahead strategy changes needed")

# =============================================================================
# DEBUGGING UTILITIES
# =============================================================================

def debug_parse_alternatives(text: str, alternatives: List[List[Dict[str, Any]]]):
    """Debug utility to print detailed parse alternatives."""
    strategy_names = ["Longest-first", "Shortest-first", "Backtrack"]
    
    print(f"\n=== Debug Parse Alternatives for: {text} ===")
    
    for i, alt in enumerate(alternatives):
        print(f"\n{strategy_names[i]} Strategy:")
        for segment in alt:
            if segment['type'] == 'dict':
                clean_text = _clean_tex_commands(segment['text'])
                print(f"  ✓ Dict: [{clean_text}]")
            else:
                print(f"  ✗ NoDict: {{{segment['text']}}}")
    
    print()

def validate_debug_environment():
    """Validate that debug environment is properly set up."""
    try:
        # Check if we can create log files
        from pathlib import Path
        script_dir = Path(__file__).parent
        temp_dir = script_dir.parent.parent / "04_assets" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Test write access
        test_file = temp_dir / "debug_test.tmp"
        test_file.write_text("test")
        test_file.unlink()
        
        return True
    except Exception as e:
        print(f"Warning: Debug environment validation failed: {e}")
        return False

def print_session_summary():
    """Print summary of lookahead session to console."""
    global session_stats
    
    if session_stats['decisions_made'] > 0:
        if session_stats['strategy_changes'] > 0:
            print(f"📊 Lookahead: {session_stats['strategy_changes']} strategy changes out of {session_stats['decisions_made']} decisions")
        else:
            print(f"✅ Lookahead: No strategy changes needed ({session_stats['decisions_made']} decisions)")

if __name__ == "__main__":
    # Test the debug module
    print("Module 2 Debug Support")
    print("This module provides debug functionality for Module 2.")
    print("It should be imported by module2_preprocess.py, not run directly.")
    
    if validate_debug_environment():
        print("✅ Debug environment validation passed")
    else:
        print("⚠️ Debug environment validation failed") 
