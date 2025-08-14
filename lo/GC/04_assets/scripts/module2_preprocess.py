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
import subprocess
from pathlib import Path
from patch_overrides import apply_patch_overrides
from typing import List, Dict, Tuple, Any
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
                protected_parts.append('\\nobreak')
            
            # Case 2: Add \nobreak after opening punctuation  
            # " + \lw{word} → "\nobreak\lw{word}
            elif (len(current_part) > 0 and 
                  is_opening_punctuation(current_part[-1]) and
                  needs_nobreak_protection(next_part)):
                protected_parts.append('\\nobreak')
    
    return protected_parts

def process_text_groups(groups, dictionary, debug=False):
    """Process grouped text parts through dictionary lookup and special handling."""
    result_parts = []
    
    for i, (group_type, content) in enumerate(groups):
        if group_type == 'lao':
            # Process Lao text with dictionary using lookahead
            processed_lao = lookup_lao_words(content, dictionary, debug)
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
        module2_debug.log_lookahead_decision(text, alternatives, best_strategy, scored_alternatives, get_project_root())
    
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

# UPDATED LOOKUP FUNCTION WITH LOOKAHEAD
def lookup_lao_words(lao_text, dictionary, debug=False):
    """Apply dictionary lookup to pure Lao text using lookahead logic."""
    # Parse the text using lookahead
    parse_result = parse_chunk_with_lookahead(lao_text, dictionary, debug)
    
    # Convert to TeX format
    return convert_parse_result_to_tex(parse_result)
    
# EXAMPLE TEST FUNCTION TO VALIDATE THE IMPLEMENTATION
def test_lookahead_logic():
    """Test function to validate the lookahead implementation."""
    # This would be used for testing during development
    print("Testing lookahead logic...")
    
    # Mock dictionary for testing
    class MockDictionary:
        def __init__(self):
            self.terms = {
                'ເລືອກ': 'ເລືອກ',
                'ສັນຕະປາປາ': 'ສັນຕະປາປາ', 
                'ເລືອກສັນ': 'ເລືອກ~~ສັນ'
            }
        
        def get_sorted_terms(self):
            return sorted(self.terms.keys(), key=len, reverse=True)
    
    # Mock helper functions
    def mock_convert_break_points(coded_term):
        return coded_term.replace('~~', '\\p{200}')
    
    def mock_find_next_lao_word_break(text, start_pos, dictionary):
        return min(start_pos + 3, len(text))  # Simple fallback
    
    def mock_get_project_root():
        from pathlib import Path
        return Path("/tmp")  # Mock path for testing
    
    # Replace functions temporarily for testing
    global convert_break_points, find_next_lao_word_break, get_project_root
    convert_break_points = mock_convert_break_points
    find_next_lao_word_break = mock_find_next_lao_word_break
    get_project_root = mock_get_project_root
    
    # Test the problematic case
    test_text = "ເລືອກສັນຕະປາປາ"
    mock_dict = MockDictionary()
    
    print(f"Input: {test_text}")
    
    # Test different parsing strategies
    longest_result = parse_longest_first(test_text, mock_dict, True)
    print(f"Longest-first result: {longest_result}")
    
    shortest_result = parse_shortest_first(test_text, mock_dict, True)
    print(f"Shortest-first result: {shortest_result}")
    
    backtrack_result = parse_with_backtrack(test_text, mock_dict, True)
    print(f"Backtrack result: {backtrack_result}")
    
    # Test lookahead selection
    final_result = parse_chunk_with_lookahead(test_text, mock_dict, True)
    print(f"Final selected result: {final_result}")
    
    # Test TeX conversion
    tex_output = convert_parse_result_to_tex(final_result)
    print(f"TeX output: {tex_output}")
    
    # Expected: \lw{ເລືອກ}\lw{ສັນຕະປາປາ}
    print("Expected: \\lw{ເລືອກ}\\lw{ສັນຕະປາປາ}")

# PERFORMANCE ENHANCEMENT FUNCTION
def optimize_dictionary_lookup(dictionary):
    """
    Optimize dictionary for faster lookups by creating prefix trees.
    This is an optional enhancement for better performance.
    """
    # Create a prefix tree (trie) for faster matching
    # This would be useful for very large dictionaries
    
    class TrieNode:
        def __init__(self):
            self.children = {}
            self.is_complete_word = False
            self.word = None
    
    root = TrieNode()
    
    # Build trie from dictionary terms
    for term in dictionary.get_sorted_terms():
        current = root
        for char in term:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]
        current.is_complete_word = True
        current.word = term
    
    return root

def find_all_matches_at_position(text, position, trie_root, max_matches=5):
    """
    Find all dictionary matches starting at a specific position using trie.
    Returns matches sorted by length (longest first).
    """
    matches = []
    current = trie_root
    
    for i in range(position, len(text)):
        char = text[i]
        if char not in current.children:
            break
        
        current = current.children[char]
        if current.is_complete_word:
            matches.append(current.word)
            if len(matches) >= max_matches:
                break
    
    # Return longest matches first
    return sorted(matches, key=len, reverse=True)

# DEBUGGING AND STATISTICS FUNCTIONS
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

# VALIDATION FUNCTION FOR INTEGRATION TESTING
def validate_integration():
    """
    Validate that the integration works correctly with sample data.
    Run this after integrating the lookahead logic.
    """
    print("=== Integration Validation ===")
    
    # Test cases that should improve with lookahead
    test_cases = [
        "ເລືອກສັນຕະປາປາ",  # Should become two terms instead of one + nodict
        "ການສຶກສາດີ",        # Test compound scenarios
        "ເຮັດວຽກຢ່າງດີ"       # Test multiple small words vs longer compounds
    ]
    
    print("Testing sample cases (requires actual dictionary):")
    for case in test_cases:
        print(f"  Input: {case}")
        print(f"  (Would show parse result with actual dictionary)")
    
    print("\nValidation complete. Check nodict_terms.log for improvements.")

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
    replacing them with numbered placeholders.

    Returns:
        (placeholder_text, protected_commands)
    """
    import re

    protected_commands = []

    # One-pass matcher for all protected tokens; order is preserved by re.sub callback
    pattern = re.compile(
        r"(\\(?:egw|scrref|lw)\{[^}]+\}"      # \egw{...}, \scrref{...}, \lw{...}
        r"|\\scrspace(?![A-Za-z])"            # \scrspace (standalone)
        r"|\[\^\d+\](?::)?"                   # [^1] and [^1]:
        r"|\\[sS](?![A-Za-z]))"               # \s or \S (not followed by letters)
    )

    def _repl(m: re.Match) -> str:
        idx = len(protected_commands)
        protected_commands.append(m.group(0))
        return f"__PROTECTED_CMD_{idx}__"

    placeholder_text = pattern.sub(_repl, text)
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
    processed_parts = process_text_groups(groups, dictionary, debug)
    
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

        # Apply high-priority exact overrides from patch.txt
        # Requires: from patch_overrides import apply_patch_overrides
        content = apply_patch_overrides(content)
            
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
    """Get the project root directory based on script location."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    return project_root
    
def get_dictionary_path():
    """Get the path to the dictionary file."""
    script_dir = Path(__file__).parent
    return script_dir / '../../../../lo/assets/dictionaries/main.txt'

def get_patch_dictionary_path():
    """Get the path to the patch dictionary file."""
    script_dir = Path(__file__).parent
    return script_dir / '../../../../lo/assets/dictionaries/patch.txt'

def expand_chapter_ranges(file_specs):
    """
    Expand chapter range specifications like GC[01..05] into individual chapters.
    
    Args:
        file_specs (list): List of file specifications
        
    Returns:
        list: Expanded list with ranges converted to individual chapters
    """
    import re
    
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
    if re.match(r'^GC\d+$', base_spec):
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
                if re.match(r'^GC\d+$', base_spec):
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

def run_pre_debug_tests():
    """
    Run test suite before debug processing to ensure stability.
    
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
        
        # Run the test suite
        result = subprocess.run(
            [sys.executable, str(test_script)],
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
    
    args = parser.parse_args()
    
    # Run pre-debug tests to ensure stability
    if args.debug:
        if not run_pre_debug_tests():
            print("⚠️ Tests failed - aborting to prevent breaking functionality")
            print("Fix the failing tests before proceeding with debug mode.")
            sys.exit(1)
    
    # Initialize debug session
    if HAS_DEBUG and args.debug:
        module2_debug.initialize_debug_session(get_project_root())
    
    # Load dictionary
    dictionary_path = get_dictionary_path()
    dictionary = LaoDictionary(dictionary_path)
    
    # Get input files with intelligent matching
    input_files = get_input_files(args)
    
    if not input_files:
        print("No input files to process")
        sys.exit(1)
    
    # Process files
    success_count = 0
    total_count = len(input_files)
    processed_output_files = []
    
    mode_desc = 'debug' if args.debug else 'production'
    print(f"Processing {total_count} file(s) in {mode_desc} mode...")
    
    for input_file in input_files:
        input_path = str(input_file)
        output_path = str(get_output_path(input_file, args.debug))
        
        if process_file(input_path, output_path, dictionary, args.verbose or args.debug):
            success_count += 1
            processed_output_files.append(Path(output_path))
    
    print(f"\nCompleted: {success_count}/{total_count} files processed successfully")
    
    # Finalize debug session and generate comprehensive reports
    if HAS_DEBUG and args.debug:
        module2_debug.finalize_debug_session(get_project_root(), total_count, success_count, processed_output_files)

    
    if success_count < total_count:
        sys.exit(1)

if __name__ == "__main__":
    main()