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
- Console output for interesting parsing decisions
- Integration with dict_analyzer.py for comprehensive reporting

USAGE:
- Automatically imported by Module 2 when --debug flag is used
- Creates lookahead_decisions.log for detailed parsing decisions
- Works with dict_analyzer.py for complete analysis reports
"""

import re
from pathlib import Path
from typing import List, Dict, Any

# =============================================================================
# LOOKAHEAD DECISION LOGGING
# =============================================================================

def log_lookahead_decision(text: str, alternatives: List[List[Dict[str, Any]]], 
                          selected_strategy: int, debug: bool = False, 
                          project_root: Path = None):
    """Log interesting lookahead decisions in narrative format."""
    strategy_names = ["longest-first", "shortest-first", "backtrack"]
    
    # Check if strategies produced different results
    if not _strategies_differ(alternatives):
        return  # All strategies agree, nothing interesting to log
    
    # Console output for interesting cases
    if debug:
        selected_name = strategy_names[selected_strategy]
        improvement = _describe_improvement(alternatives, selected_strategy)
        print(f"🔍 Lookahead improved: {text} → selected {selected_name} ({improvement})")
    
    # File logging
    try:
        if project_root is None:
            # Fallback path resolution
            script_dir = Path(__file__).parent
            project_root = script_dir.parent.parent
            
        log_file = project_root / "04_assets" / "temp" / "lookahead_decisions.log"
        
        selected_name = strategy_names[selected_strategy]
        selected_result = alternatives[selected_strategy]
        
        improvement_description = _describe_improvement(alternatives, selected_strategy)
        before_description = _describe_parse_result(alternatives[0])  # longest-first baseline
        after_description = _describe_parse_result(selected_result)
        
        # Create narrative entry
        log_entry = [
            f'✓ {improvement_description} in "{text}"',
            f'  Changed from: {before_description}',
            f'  Changed to: {after_description}',
            f'  Strategy: {selected_name}',
            ""  # Empty line between entries
        ]
        
        # Append to log file
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write('\n'.join(log_entry))
            
    except Exception as e:
        # Don't let logging errors break processing
        pass

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
        print(f"✓ Processed: {decisions_made} lookahead decisions, {strategy_changes} strategy changes")

def clear_debug_logs(project_root: Path):
    """Clear previous debug logs at start of processing."""
    try:
        log_file = project_root / "04_assets" / "temp" / "lookahead_decisions.log"
        if log_file.exists():
            log_file.unlink()
    except Exception:
        pass

# =============================================================================
# INTEGRATION WITH DICT_ANALYZER
# =============================================================================

def call_dict_analyzer(project_root: Path):
    """Call the dictionary analyzer for comprehensive reporting."""
    try:
        # Import and call the main analyzer
        from dict_analyzer import generate_context_report
        generate_context_report(project_root)
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

def finalize_debug_session(project_root: Path, total_files: int, success_count: int):
    """Finalize debug session - generate comprehensive reports."""
    # Call the dictionary analyzer for comprehensive reporting
    analysis_success = call_dict_analyzer(project_root)
    
    # Summary info
    if analysis_success:
        # Check if we generated any lookahead decisions
        decisions_file = project_root / "04_assets" / "temp" / "lookahead_decisions.log"
        if decisions_file.exists():
            print(f"📝 Generated lookahead decisions log")
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

if __name__ == "__main__":
    # Test the debug module
    print("Module 2 Debug Support")
    print("This module provides debug functionality for Module 2.")
    print("It should be imported by module2_preprocess.py, not run directly.")
    
    if validate_debug_environment():
        print("✅ Debug environment validation passed")
    else:
        print("⚠️ Debug environment validation failed")