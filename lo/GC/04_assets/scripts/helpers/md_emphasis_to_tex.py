r"""
md_emphasis_to_tex.py
---------------------

Purpose:
    Convert Markdown emphasis (bold, italic, underline, strikethrough) to LaTeX commands.
    
Responsibilities:
    • Convert **text** and __text__ to \textbf{text}
    • Convert *text* and _text_ to \emph{text}
    • Convert ***text*** to \textbf{\emph{text}}
    • Convert ~~text~~ to \sout{text} (requires \usepackage{ulem})
    • Convert ++text++ to \uline{text} (requires \usepackage{ulem})
    • Handle nested emphasis correctly
    • Preserve already-escaped asterisks and underscores

Pattern Priority:
    Process from longest to shortest to avoid mis-parsing:
    1. Bold+italic (*** or ___) 
    2. Strikethrough (~~)
    3. Underline (++)
    4. Bold (** or __)
    5. Italic (* or _)
"""

import re
from typing import Tuple, Dict


def process_emphasis(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Convert Markdown emphasis markers to LaTeX commands.
    
    Args:
        text: Markdown text with emphasis markers
        
    Returns:
        Tuple of:
        - Processed text with LaTeX commands
        - Statistics dict with conversion counts
    """
    stats = {
        'bold_italic': 0,
        'bold': 0,
        'italic': 0,
        'strikethrough': 0,
        'underline': 0
    }
    
    # Process bold+italic first (3 markers)
    text, count = convert_bold_italic(text)
    stats['bold_italic'] = count
    
    # Process strikethrough
    text, count = convert_strikethrough(text)
    stats['strikethrough'] = count
    
    # Process underline
    text, count = convert_underline(text)
    stats['underline'] = count
    
    # Process bold (2 markers)
    text, count = convert_bold(text)
    stats['bold'] = count
    
    # Process italic (1 marker)
    text, count = convert_italic(text)
    stats['italic'] = count
    
    return text, stats

def convert_bold_italic(text: str) -> Tuple[str, int]:
    """Convert ***text*** or ___text___ to \\textbf{\\emph{text}}."""
    count = 0
    
    # Pattern for ***text***
    pattern = r'\*\*\*([^*]+)\*\*\*'
    
    def replace_bold_italic(match):
        nonlocal count
        count += 1
        content = match.group(1).strip()
        return f'\\textbf{{\\emph{{{content}}}}}'
    
    text = re.sub(pattern, replace_bold_italic, text)
    
    # Pattern for ___text___
    pattern = r'___([^_]+)___'
    text = re.sub(pattern, replace_bold_italic, text)
    
    return text, count


def convert_bold(text: str) -> Tuple[str, int]:
    """Convert **text** or __text__ to \\textbf{text}."""
    count = 0
    
    # Pattern for **text**
    pattern = r'\*\*([^*]+)\*\*'
    
    def replace_bold(match):
        nonlocal count
        count += 1
        content = match.group(1).strip()
        return f'\\textbf{{{content}}}'
    
    text = re.sub(pattern, replace_bold, text)
    
    # Pattern for __text__
    pattern = r'__([^_]+)__'
    text = re.sub(pattern, replace_bold, text)
    
    return text, count


def convert_italic(text: str) -> Tuple[str, int]:
    """Convert *text* or _text_ to \\emph{text}."""
    count = 0
    
    # Simple pattern: capture * content *
    pattern = r'\*([^*]+)\*'
    
    def replace_italic(match):
        nonlocal count
        count += 1
        return f'\\emph{{{match.group(1)}}}'
    
    text = re.sub(pattern, replace_italic, text)
    
    # Similar for underscore
    pattern = r'_([^_]+)_'
    text = re.sub(pattern, replace_italic, text)
    
    return text, count


def convert_strikethrough(text: str) -> Tuple[str, int]:
    """Convert ~~text~~ to \\sout{text}."""
    count = 0
    
    pattern = r'~~([^~]+)~~'
    
    def replace_strikethrough(match):
        nonlocal count
        count += 1
        content = match.group(1).strip()
        return f'\\sout{{{content}}}'
    
    text = re.sub(pattern, replace_strikethrough, text)
    
    return text, count


def convert_underline(text: str) -> Tuple[str, int]:
    """Convert ++text++ to \\uline{text}."""
    count = 0
    
    pattern = r'\+\+([^+]+)\+\+'
    
    def replace_underline(match):
        nonlocal count
        count += 1
        content = match.group(1).strip()
        return f'\\uline{{{content}}}'
    
    text = re.sub(pattern, replace_underline, text)
    
    return text, count
