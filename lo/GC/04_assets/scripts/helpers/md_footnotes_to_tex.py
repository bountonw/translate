"""
md_footnotes_to_tex.py
----------------------

Purpose:
    Convert Markdown footnotes to LaTeX footnotes with proper cleanup and validation.
    
Responsibilities:
    • Parse inline markers [^id] and definition lines [^id]: text
    • Convert markers to \footnote{text} with proper LaTeX escaping
    • Remove used definition lines, preserve orphaned definitions
    • Validate and report footnote issues (orphans, duplicates)
    • Handle multi-line footnotes (future extension)

ID Policy:
    • Uppercase letters only (A, AB, XYZ)
    • Lowercase letters only (a, bc, note) 
    • Digits only (1, 23, 456)
    • No mixed case or alphanumeric combinations
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional


# Regex patterns based on ID policy
ID_SHAPE = r"[A-Z]+|[a-z]+|\d+"
RE_MARKER_INLINE = re.compile(rf"\[\^({ID_SHAPE})\](?!:)")
RE_DEF_LINE = re.compile(rf"^\[\^({ID_SHAPE})\]:(.+)$", re.MULTILINE)
RE_DEF_HEAD = re.compile(rf"^\[\^({ID_SHAPE})\]:.+$", re.MULTILINE)


def parse_footnote_definitions(text: str) -> Dict[str, str]:
    """
    Extract all single-line footnote definitions from Markdown text.
    
    Args:
        text: Markdown content to parse
        
    Returns:
        Dictionary mapping footnote ID to definition text (stripped).
        If duplicate IDs exist, last definition wins.
        
    Example:
        Input: "[^1]: First note\n[^abc]: Second note"
        Output: {"1": "First note", "abc": "Second note"}
        
    Policy:
        Only handles single-line definitions [^id]: text
        Multi-line support will be added in future extension.
    """
    def_pairs = RE_DEF_LINE.findall(text)
    result = {def_id: def_text.strip() for def_id, def_text in def_pairs}
    
    # ADD THIS DEBUG CODE HERE (after line 73):
    for def_id, def_text in result.items():
        print(f"DEBUG Footnote [{def_id}]: '{def_text}'")
    
    return result

def find_footnote_markers(text: str) -> List[str]:
    """
    Find all inline footnote markers in document order.
    
    Args:
        text: Markdown content to scan
        
    Returns:
        List of footnote IDs in order of first appearance.
        Duplicates preserved to track usage patterns.
        
    Example:
        Input: "Text[^1] more[^abc] and[^1] again"
        Output: ["1", "abc", "1"]
        
    Notes:
        Does not match definition heads (which contain colons).
    """
    return RE_MARKER_INLINE.findall(text)


def find_orphaned_definitions(text: str) -> List[str]:
    """
    Find definition IDs that are never referenced as inline markers.
    
    Args:
        text: Markdown content to analyze
        
    Returns:
        List of orphaned definition IDs.
        
    Purpose:
        Identify unused footnotes for cleanup warnings.
    """
    marker_ids = set(RE_MARKER_INLINE.findall(text))
    def_ids = RE_DEF_HEAD.findall(text)
    
    return [def_id for def_id in def_ids if def_id not in marker_ids]


def find_orphaned_markers(text: str) -> List[str]:
    """
    Find marker IDs that have no corresponding definitions.
    
    Args:
        text: Markdown content to analyze
        
    Returns:
        List of orphaned marker IDs (may contain duplicates).
        
    Purpose:
        Identify broken footnote references for error reporting.
    """
    def_ids = set(RE_DEF_HEAD.findall(text))
    marker_ids = RE_MARKER_INLINE.findall(text)
    
    return [marker_id for marker_id in marker_ids if marker_id not in def_ids]


def convert_markers_to_footnotes(text: str, definitions: Dict[str, str]) -> Tuple[str, Dict[str, int]]:
    """
    Replace all resolvable footnote markers with LaTeX footnotes.
    
    Args:
        text: Markdown content with [^id] markers
        definitions: Dictionary of id -> definition text
        
    Returns:
        Tuple of:
        - Modified text with \footnote{...} replacements
        - Usage count dict for duplicate reference tracking
        
    Behavior:
        - Markers with definitions: [^id] -> \footnote{definition}
        - Markers without definitions: left unchanged
        - Definition text is sanitized for LaTeX spacing
        
    Example:
        Input: "Text[^1] and[^missing]", {"1": "My note"}
        Output: ("Text\footnote{My note} and[^missing]", {"1": 1})
    """
    usage_counts = {}

    def replace_marker(match):  # This is a nested function
        marker_id = match.group(1)
        if marker_id in definitions:
            # ADD THE DEBUG LINE HERE (around line 160):
            print(f"DEBUG Converting [{marker_id}] to footnote with: '{definitions[marker_id]}'")
            
            # Track usage for duplicate detection
            usage_counts[marker_id] = usage_counts.get(marker_id, 0) + 1
            
            # Sanitize the footnote text and create LaTeX footnote
            sanitized_text = sanitize_footnote_text(definitions[marker_id])
            return f"\\footnote{{{sanitized_text}}}"
        else:
            # Leave unresolvable markers unchanged
            return match.group(0)    
    
    new_text = RE_MARKER_INLINE.sub(replace_marker, text)
    
    # Return only footnotes that were referenced more than once
    duplicate_refs = {k: v for k, v in usage_counts.items() if v > 1}
    
    return new_text, duplicate_refs


def remove_used_definition_lines(text: str, used_ids: Set[str]) -> str:
    """
    Remove definition lines for footnotes that were successfully converted.
    
    Args:
        text: Markdown content with definition lines
        used_ids: Set of footnote IDs that were converted to \footnote{}
        
    Returns:
        Text with used definition lines removed, orphaned definitions preserved.
        
    Behavior:
        - Removes entire line including trailing newline
        - Preserves orphaned definitions for later review
        - Handles CRLF/LF line ending variations
        
    Purpose:
        Clean up document after footnote conversion while preserving
        orphaned definitions for manual review.
    """
    if not used_ids:
        return text
    
    # Create pattern that matches definition lines for used IDs
    used_ids_pattern = "|".join(re.escape(id_) for id_ in used_ids)
    removal_pattern = rf"^\[\^({used_ids_pattern})\]:.*$\r?\n?"
    
    return re.sub(removal_pattern, "", text, flags=re.MULTILINE)


def sanitize_footnote_text(text: str) -> str:
    r"""
    Clean LaTeX spacing macros inside footnote content.
    
    Args:
        text: Raw footnote definition text
        
    Returns:
        Cleaned text suitable for \footnote{} content.
        
    Transformations:
        - Remove leading/trailing \space{} and \nbsp{}
        - Normalize spacing combinations (\space{}\nbsp{} -> \nbsp{})
        - Preserve \nobreak{} macros
        - Trim whitespace but preserve internal spacing
        
    Purpose:
        Ensure footnote content renders cleanly in LaTeX without
        unwanted spacing artifacts.
    """
    # Remove from beginning of the footnote string
    text = re.sub(r'^(\\space\{\}|\\nbsp\{\}|\s)+', '', text)
    # Remove from end
    text = re.sub(r'(\\space\{\}|\\nbsp\{\}|\s)+$', '', text)

    # Normalize internal spacing combinations
    text = re.sub(r'\\space\{\}\\nbsp\{\}', r'\\nbsp{}', text)
    text = re.sub(r'\\nbsp\{\}\\space\{\}', r'\\nbsp{}', text)
    text = re.sub(r'\\space\{\}\\nobreak', r'\\nobreak', text)
    
    return text

def collapse_extra_blank_lines(text: str) -> str:
    """
    Normalize excessive blank lines to maintain double-spaced paragraphs.
    
    Args:
        text: Document content with potential extra blank lines
        
    Returns:
        Text with runs of 3+ blank lines collapsed to exactly 2 newlines.
        
    Behavior:
        - Normalize CRLF/CR to LF for consistent processing
        - Preserve intentional double-spacing between paragraphs
        - Remove accidental triple+ spacing from definition removal
        
    Purpose:
        Maintain clean paragraph spacing after footnote processing.
    """
    # Normalize line endings to LF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Collapse 3+ consecutive newlines (with optional whitespace) to exactly 2 newlines
    text = re.sub(r'\n[ \t]*\n[ \t]*\n[ \t]*(\n[ \t]*)*', '\n\n', text)
    
    return text

def process_footnotes(text: str) -> Tuple[str, Dict[str, any]]:
    # Parse definitions and find markers
    definitions = parse_footnote_definitions(text)
    all_markers = find_footnote_markers(text)
    
    # Find orphaned elements
    orphaned_defs = find_orphaned_definitions(text)
    orphaned_markers = find_orphaned_markers(text)
    
    # Convert markers to footnotes
    converted_text, duplicate_refs = convert_markers_to_footnotes(text, definitions)
    
    # Remove definition lines for successfully converted footnotes
    used_ids = set(marker_id for marker_id in all_markers if marker_id in definitions)
    cleaned_text = remove_used_definition_lines(converted_text, used_ids)
    
    # Collapse extra blank lines
    final_text = collapse_extra_blank_lines(cleaned_text)
    
    # Build comprehensive report
    report = {
        'orphaned_definitions': orphaned_defs,
        'orphaned_markers': orphaned_markers,
        'duplicate_references': duplicate_refs,
        'converted_count': len(used_ids),
        'definition_count': len(definitions),
        'marker_count': len(all_markers)
    }
    
    return final_text, report
