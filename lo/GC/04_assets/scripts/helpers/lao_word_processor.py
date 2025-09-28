#!/usr/bin/env python3
"""
Lao Word Processor: Dictionary-based Lao text processing for TeX output

This module handles the core Lao word processing pipeline:
1. Linguistic analysis of Lao text (character classification, fragment detection)
2. Dictionary lookup with multiple parsing strategies (longest-first, shortest-first, backtracking)
3. TeX conversion to \lw{} and \nodict{} format with break point penalties

Used by module2_preprocess.py for dictionary-based line-breaking application.
"""

import re
from typing import List, Dict, Tuple, Any

# Lao Linguistic Rules - Based on actual nodict_analysis.log patterns
TONE_MARKS = {
    '່', '້', '໊', '໋'  # All tone marks
}

DEPENDENT_VOWELS = {
    'ະ',  # Must end syllable
    'ັ',  # Must be between consonants  
    'ິ', 'ີ', 'ຶ', 'ື', 'ຸ', 'ູ',  # Must follow consonants
    'ົ',  # Must be between consonants
    'ຽ',  # Must be between consonants
    'ຳ',  # Special combining vowel+nasal
    'າ',  # Long A - must follow consonant
}

VOWELS_THAT_PRECEDE_CONSONANTS = {
    'ໃ', 'ໄ', 'ໂ', 'ເ'  # Must have consonant after
}

# Single consonants that are likely fragments (high frequency in nodict)
LIKELY_FRAGMENT_CONSONANTS = {
    'ສ', 'ດ', 'ບ', 'ກ', 'ຄ', 'ນ', 'ມ', 'ລ', 'ວ', 'ຫ', 'ພ', 'ທ', 'ຈ', 'ຊ', 'ຍ', 'ຣ', 'ຟ', 'ປ', 'ຂ', 'ຮ', 'ອ', 'ຢ', 'ຖ', 'ຕ', 'ງ', 'ຝ', 'ຜ'
}

def is_invalid_fragment(text: str) -> bool:
    """Check if text is an invalid fragment starting with dependent character."""
    if len(text) < 2 or len(text) > 6:
        return False
    
    # Handle fragments that start with space + dependent vowel (common pattern)
    if text.startswith(' ') and len(text) > 1:
        second_char = text[1]
        # Fragments like " ັ້ນ", " ່ອນ", " ົດ", " ້າ", " ິສ"
        if second_char in DEPENDENT_VOWELS or second_char in TONE_MARKS:
            return True
    
    first_char = text[0]
    
    # Fragments starting with tone marks (່ອນ)
    if first_char in TONE_MARKS:
        return True
        
    # Fragments starting with dependent vowels (ັ່ງ, ັ້ນ, ົດ)
    if first_char in DEPENDENT_VOWELS:
        return True
    
    return False

def is_invalid_standalone_lao(text: str) -> bool:
    """
    Check if text represents invalid standalone Lao.
    Based on actual patterns from nodict_analysis.log covering 750 pages.
    """
    if not text:
        return False
    
    # Single character rules
    if len(text) == 1:
        char = text[0]
        
        # Tone marks never standalone
        if char in TONE_MARKS:
            return True
            
        # Dependent vowels never standalone  
        if char in DEPENDENT_VOWELS:
            return True
            
        # Vowels that precede consonants never standalone
        if char in VOWELS_THAT_PRECEDE_CONSONANTS:
            return True
            
        # Single consonants are likely fragments in most contexts
        # (This is aggressive but based on high nodict frequency)
        if char in LIKELY_FRAGMENT_CONSONANTS:
            return True
    
    # Fragment rules for 2-6 character sequences
    if is_invalid_fragment(text):
        return True
    
    return False

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
    return char in '.,;:!?()[]{}\"\'\'-–—“”‘’‚„‹›«»@#%'

def is_opening_punctuation(char):
    """Check if character is opening punctuation that needs \nobreak after it."""
    return char in '\"\'[{(“‘‚„‹«'
    
def is_closing_punctuation(char):
    """Check if character is closing punctuation that needs \nobreak before it."""
    return char in '.,;:!?()[]{}"\'\'-–—”’‚„›»@#%'

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

def group_consecutive_text(text):
    """
    Group consecutive characters by type, treating \\cs{} as part of Lao text.
    """
    if not text:
        return []
    
    # Split text into tokens, keeping \cs{} with adjacent Lao text
    tokens = re.split(r'(\\cs\{\})', text)
    
    groups = []
    current_group = ''
    current_type = None
    
    for token in tokens:
        if not token:
            continue
            
        if token == '\\cs{}':
            # \cs{} continues the current Lao group
            if current_type == 'lao':
                current_group += token
            else:
                if current_group:
                    groups.append((current_type, current_group))
                current_group = token
                current_type = 'lao'
        else:
            # Process each character in the token
            for char in token:
                if is_lao_text(char):
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
def convert_break_points(coded_term):
    """Convert dictionary break point symbols to TeX penalty commands."""
    
    # Handle compound space first (~S~)
    coded_term = re.sub(r'~S~', r'\\cs', coded_term)
    
    # Convert penalty symbols
    # Order matters - longer patterns first
    coded_term = re.sub(r'~~~~~~', r'\\p{-1000}', coded_term)  # superb
    coded_term = re.sub(r'~~~~~', r'\\p{-400}', coded_term)  # excellent
    coded_term = re.sub(r'~~~~', r'\\p{-200}', coded_term)   # encouraged
    coded_term = re.sub(r'~~~', r'\\p{0}', coded_term)       # neutral
    coded_term = re.sub(r'~~', r'\\p{200}', coded_term)      # discouraged
    coded_term = re.sub(r'!!', r'\\p{7500}', coded_term)     # armageddon
    coded_term = re.sub(r'!', r'\\p{5000}', coded_term)      # nuclear
    coded_term = re.sub(r'~', r'\\p{1000}', coded_term)      # emergency
    
    return coded_term


def evaluate_parse_quality(parse_result: List[Dict[str, Any]]) -> int:
    """
    Score a parsing result - lower scores are better.
    
    ENHANCED VERSION: Prevents illegal linguistic splits while preserving 
    \nodict{} for legitimate missing dictionary words.
    
    The goal is to prevent splits like:
    ❌ ເພື່ອນຳ → [ເພື່ອນ] + nodict{ຳ} (ຳ can't stand alone)
    ✅ ເພື່ອນຳ → [ເພື່ອ] + [ນຳ] (both valid words)
    ✅ ມິນເລີ → nodict{ມິນເລີ} (legitimate missing word for dictionary)
    """
    score = 0
    consecutive_dict_bonus = 0
    
    for i, segment in enumerate(parse_result):
        if segment['type'] == 'nodict':
            text_len = len(segment['text'])
            
            # NEW: Severe penalty for linguistically impossible fragments
            if is_invalid_standalone_lao(segment['text']):
                score += 10000  # Heavy penalty to force different word boundaries
                # This makes illegal splits much worse than legitimate missing words
            
            # Normal penalty for nodict segments (legitimate missing words)
            score += text_len * 10
            
            # Extra penalties for very short nodict segments (likely parsing errors)
            if text_len == 1:
                score += 50  # Single character nodict is usually wrong
            elif text_len <= 2:
                score += 25  # Very short nodict segments are suspicious
                
            # Reset consecutive dictionary bonus
            consecutive_dict_bonus = 0
                
        elif segment['type'] == 'dict':
            text_len = len(segment['text'])
            
            # UNCHANGED: Strong rewards for longer dictionary entries (compound words)
            if text_len >= 6:
                score -= 25  # Major bonus for long compounds
            elif text_len >= 4:
                score -= 15  # Good bonus for medium compounds
            elif text_len >= 3:
                score -= 8   # Small bonus for 3-char words
            elif text_len >= 2:
                score -= 3   # Minimal bonus for 2-char words
            else:
                score -= 1   # Single character dict entries get minimal credit
            
            # UNCHANGED: Fragmentation detection via consecutive short entries
            consecutive_dict_bonus += 1
            if consecutive_dict_bonus >= 2:
                if text_len <= 3:
                    score += 8  # Penalty for likely fragmentation
                elif text_len <= 4:
                    score += 4  # Smaller penalty for medium fragments
    
    # UNCHANGED: Multi-segment penalty (compound preservation)
    total_dict_segments = sum(1 for seg in parse_result if seg['type'] == 'dict')
    if total_dict_segments > 1:
        additional_segments = total_dict_segments - 1
        segment_penalty = additional_segments * 18  # 18 points per extra segment
        score += segment_penalty
    
    # UNCHANGED: Global fragmentation penalty
    total_segments = len(parse_result)
    if total_segments > 5:
        score += (total_segments - 5) * 2
    
    # UNCHANGED: Dictionary coverage penalties
    dict_segments = sum(1 for seg in parse_result if seg['type'] == 'dict')
    nodict_segments = sum(1 for seg in parse_result if seg['type'] == 'nodict')
    
    if dict_segments > 0 and nodict_segments > 0:
        coverage_ratio = dict_segments / (dict_segments + nodict_segments)
        if coverage_ratio < 0.5:
            score += 10
    
    return score

def evaluate_compound_preference(parse_result: List[Dict[str, Any]], text: str) -> int:
    """
    FIXED: Enhanced compound word detection with better fragmentation detection.
    
    This function specifically detects when dictionary compounds have been 
    inappropriately fragmented and applies heavy penalties.
    
    VALIDATED: Successfully detects fragmentations like:
    - ດັ່ງນັ້ນ → ດັ່ງ + ນັ້ນ
    - ຄົ້ນພົບ → ຄົ້ນ + ພົບ  
    - ຍິ່ງໃຫຍ່ → ຍິ່ງ + ໃຫຍ່
    
    Args:
        parse_result: List of parsed segments with type and text
        text: Original text being parsed
        
    Returns:
        int: Penalty score (higher = worse, 0 = no fragmentation detected)
    """
    compound_penalty = 0
    
    # Look for patterns that suggest a compound word was broken up
    dict_segments = [seg for seg in parse_result if seg['type'] == 'dict']
    
    if len(dict_segments) >= 2:
        # Check if consecutive dictionary entries might have been one compound
        for i in range(len(dict_segments) - 1):
            current = dict_segments[i]
            next_seg = dict_segments[i + 1]
            
            # If both segments are short and could combine to form a compound,
            # this is likely inappropriate fragmentation
            if (len(current['text']) <= 4 and 
                len(next_seg['text']) <= 4):
                
                combined = current['text'] + next_seg['text']
                if combined in text:
                    # This is definitely fragmentation - heavy penalty
                    compound_penalty += 15
    
    return compound_penalty

def parse_longest_first(text: str, dictionary, debug: bool = False) -> List[Dict[str, Any]]:
    """Current longest-first parsing strategy."""
    if debug:
        print(f"  Trying longest-first on: {text}")
    
    sorted_terms = dictionary.get_sorted_terms()
    result = []
    position = 0
    
    while position < len(text):
        matched = False
        
        for term in sorted_terms:
            if text[position:position + len(term)] == term:
                result.append({
                    'type': 'dict',
                    'text': term,
                    'coded': dictionary.terms[term]
                })
                position += len(term)
                matched = True
                if debug:
                    print(f"    Matched: {term}")
                break
        
        if not matched:
            word_end = find_next_lao_word_break(text, position, dictionary)
            unknown_text = text[position:word_end]
            result.append({
                'type': 'nodict',
                'text': unknown_text,
                'coded': unknown_text
            })
            if debug:
                print(f"    NoDict: {unknown_text}")
            position = word_end
    
    return result

def parse_shortest_first(text: str, dictionary, debug: bool = False) -> List[Dict[str, Any]]:
    """Alternative shortest-first parsing strategy."""
    if debug:
        print(f"  Trying shortest-first on: {text}")
    
    sorted_terms = sorted(dictionary.get_sorted_terms(), key=len)
    result = []
    position = 0
    
    while position < len(text):
        matched = False
        
        for term in sorted_terms:
            if text[position:position + len(term)] == term:
                result.append({
                    'type': 'dict',
                    'text': term,
                    'coded': dictionary.terms[term]
                })
                position += len(term)
                matched = True
                if debug:
                    print(f"    Matched: {term}")
                break
        
        if not matched:
            word_end = find_next_lao_word_break(text, position, dictionary)
            unknown_text = text[position:word_end]
            result.append({
                'type': 'nodict',
                'text': unknown_text,
                'coded': unknown_text
            })
            if debug:
                print(f"    NoDict: {unknown_text}")
            position = word_end
    
    return result

def parse_with_backtrack(text: str, dictionary, debug: bool = False, max_lookahead: int = 3) -> List[Dict[str, Any]]:
    """Parsing strategy with limited backtracking and lookahead."""
    if debug:
        print(f"  Trying backtrack on: {text}")
    
    sorted_terms = dictionary.get_sorted_terms()
    result = []
    position = 0
    
    while position < len(text):
        # Find all possible matches at current position
        possible_matches = []
        for term in sorted_terms:
            if text[position:position + len(term)] == term:
                possible_matches.append(term)
                if len(possible_matches) >= max_lookahead:
                    break
        
        if possible_matches:
            # Evaluate each possible match by looking ahead
            best_choice = None
            best_score = float('inf')
            
            for match in possible_matches:
                temp_position = position + len(match)
                remainder = text[temp_position:]
                
                if remainder:
                    # Quick evaluation: can we match the start of remainder?
                    remainder_has_match = any(
                        remainder.startswith(term) 
                        for term in sorted_terms[:50]  # Check top 50 terms for speed
                    )
                    
                    choice_score = len(match) * -2  # Bonus for longer matches
                    if not remainder_has_match and len(remainder) > 0:
                        choice_score += len(remainder) * 5  # Penalty for unmatched remainder
                    
                    if choice_score < best_score:
                        best_score = choice_score
                        best_choice = match
                else:
                    best_choice = match
                    break
            
            if best_choice:
                result.append({
                    'type': 'dict',
                    'text': best_choice,
                    'coded': dictionary.terms[best_choice]
                })
                position += len(best_choice)
                if debug:
                    print(f"    Matched (backtrack): {best_choice}")
                continue
        
        word_end = find_next_lao_word_break(text, position, dictionary)
        unknown_text = text[position:word_end]
        result.append({
            'type': 'nodict',
            'text': unknown_text,
            'coded': unknown_text
        })
        if debug:
            print(f"    NoDict: {unknown_text}")
        position = word_end
    
    return result

def generate_alternative_parses(text: str, dictionary, debug: bool = False) -> List[List[Dict[str, Any]]]:
    """Generate multiple parsing strategies for comparison."""
    alternatives = []
    alternatives.append(parse_longest_first(text, dictionary, debug))
    alternatives.append(parse_shortest_first(text, dictionary, debug))
    alternatives.append(parse_with_backtrack(text, dictionary, debug))
    return alternatives

def parse_chunk_with_lookahead(text: str, dictionary, debug: bool = False) -> List[Dict[str, Any]]:
    """
    Parse a continuous Lao text chunk with lookahead and backtracking.
    UPDATED to use improved scoring that favors compound dictionary entries.
    """
    # Import debug module only when needed to avoid circular imports
    try:
        import module2_debug
        HAS_DEBUG = True
    except ImportError:
        HAS_DEBUG = False
    
    # Generate alternatives quietly
    alternatives = generate_alternative_parses(text, dictionary, False)
    
    # Score alternatives with improved algorithm
    scored_alternatives = []
    for i, alt in enumerate(alternatives):
        base_score = evaluate_parse_quality(alt)
        compound_penalty = evaluate_compound_preference(alt, text)
        total_score = base_score + compound_penalty
        scored_alternatives.append((total_score, alt, i))
    
    best_score, best_parse, best_strategy = min(scored_alternatives, key=lambda x: x[0])
    
    # Log interesting decisions (file logging only)
    if HAS_DEBUG and debug:
        from pathlib import Path
        # Get project root relative to this helper file
        current = Path.cwd()
        if current.name == '04_assets':
            project_root = current.parent
        else:
            for path in current.parents:
                if (path / '04_assets').exists():
                    project_root = path
                    break
            else:
                project_root = Path(__file__).parent.parent.parent
        module2_debug.log_lookahead_decision(text, alternatives, best_strategy, scored_alternatives, project_root)
    
    return best_parse

def convert_parse_result_to_tex(parse_result: List[Dict[str, Any]]) -> str:
    """Convert parse result to TeX format with \\lw{} and \\nodict{} commands."""
    tex_parts = []
    
    for segment in parse_result:
        if segment['type'] == 'dict':
            coded_term = convert_break_points(segment['coded'])
            tex_parts.append(f'\\lw{{{coded_term}}}')
        elif segment['type'] == 'nodict':
            tex_parts.append(f'\\nodict{{{segment["text"]}}}')
    
    return ''.join(tex_parts)

def lookup_lao_words(lao_text, dictionary, debug=False):
    """Apply dictionary lookup to pure Lao text using lookahead logic."""
    
    # Parse the text using lookahead
    parse_result = parse_chunk_with_lookahead(lao_text, dictionary, debug)
    
    # Convert to TeX format
    return convert_parse_result_to_tex(parse_result)

def analyze_parse_statistics(parse_result):
    """Analyze and return statistics about a parse result."""
    stats = {
        'total_segments': len(parse_result),
        'dict_matches': 0,
        'nodict_segments': 0,
        'total_dict_chars': 0,
        'total_nodict_chars': 0,
        'shortest_nodict': float('inf'),
        'longest_nodict': 0,
        'single_char_nodicts': 0
    }
    
    for segment in parse_result:
        if segment['type'] == 'dict':
            stats['dict_matches'] += 1
            stats['total_dict_chars'] += len(segment['text'])
        elif segment['type'] == 'nodict':
            stats['nodict_segments'] += 1
            length = len(segment['text'])
            stats['total_nodict_chars'] += length
            stats['shortest_nodict'] = min(stats['shortest_nodict'], length)
            stats['longest_nodict'] = max(stats['longest_nodict'], length)
            if length == 1:
                stats['single_char_nodicts'] += 1
    
    if stats['shortest_nodict'] == float('inf'):
        stats['shortest_nodict'] = 0
    
    # Calculate coverage percentage
    total_chars = stats['total_dict_chars'] + stats['total_nodict_chars']
    if total_chars > 0:
        stats['dict_coverage'] = (stats['total_dict_chars'] / total_chars) * 100
    else:
        stats['dict_coverage'] = 100
    
    return stats

def print_parse_comparison(text, alternatives):
    """Print a detailed comparison of different parsing strategies."""
    print(f"\n=== Parse Comparison for: {text} ===")
    strategy_names = ["Longest-first", "Shortest-first", "Backtrack"]
    
    for i, alt in enumerate(alternatives):
        stats = analyze_parse_statistics(alt)
        score = evaluate_parse_quality(alt)
        
        print(f"\n{strategy_names[i]} Strategy:")
        print(f"  Score: {score}")
        print(f"  Dictionary coverage: {stats['dict_coverage']:.1f}%")
        print(f"  Segments: {stats['total_segments']} ({stats['dict_matches']} dict, {stats['nodict_segments']} nodict)")
        
        if stats['nodict_segments'] > 0:
            print(f"  NoDict lengths: {stats['shortest_nodict']}-{stats['longest_nodict']}, {stats['single_char_nodicts']} single chars")
        
        print("  Result:", end=" ")
        for segment in alt:
            if segment['type'] == 'dict':
                print(f"[{segment['text']}]", end="")
            else:
                print(f"?{segment['text']}?", end="")
        print()
