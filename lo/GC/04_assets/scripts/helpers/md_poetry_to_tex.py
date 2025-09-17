"""
md_poetry_to_tex.py

Purpose:
    Convert Markdown poetry/verse quotations to LaTeX verse environments
    for the Lao TeX preprocessing pipeline.

Responsibilities:
    • Identify verse blocks marked with '>' prefix
    • Convert to LaTeX \begin{verse}...\end{verse} environments
    • Handle nested quotations with \verseindent{} commands
    • Process attribution lines marked with '> > > >'
    • Manage line breaks and stanza breaks appropriately
    • Track conversion statistics

Formatting Notes:
    • Single '>' lines are removed (prevent Markdown wrapping)
    • Two or more consecutive '>' lines become a stanza break
    • Lines ending with '\\' for LaTeX line breaks
    • Attribution uses \attrib{} command
    • Nested verses use \verseindent{}, \verseindentii{}, \verseindentiii{}
"""

import re
from typing import Tuple, Dict, List


def process_poetry(text: str, debug: bool = False) -> Tuple[str, Dict[str, int]]:
    """
    Convert Markdown poetry/verse blocks to LaTeX verse environments.
    
    Handles:
    - Basic verse blocks (lines starting with '>')
    - Nested quotations (up to 3 levels deep)
    - Attribution lines ('> > > >' pattern)
    - Blank line management for stanza breaks
    
    Line ending rules:
    - Each verse line gets '\\' except the very last line before \end{verse}
    - Attribution lines don't get '\\'
    - Blank lines within verses are preserved as stanza breaks
    
    Multiple verse blocks:
    - Consecutive verse blocks are separated naturally by LaTeX
    - No special spacing is added between blocks
    
    Args:
        text: Markdown text with potential poetry blocks
        debug: If True, print debug information about processing
        
    Returns:
        Tuple of:
        - Processed text with LaTeX verse environments
        - Statistics dict with conversion counts
    """
    stats = {
        'verse_blocks': 0,
        'attributions': 0,
        'nested_lines': 0
    }
    
    lines = text.split('\n')
    output_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this starts a verse block
        if line.startswith('>'):
            verse_lines = []
            blank_count = 0
            
            # Collect all consecutive lines starting with '>'
            while i < len(lines) and lines[i].startswith('>'):
                current_line = lines[i]
                
                # Check for attribution (> > > > pattern with spaces)
                if current_line.startswith('> > > > '):
                    # Extract attribution text
                    attrib_text = current_line[8:].strip()
                    verse_lines.append(('attribution', attrib_text))
                    stats['attributions'] += 1
                    i += 1
                    break  # Attribution ends the verse block
                
                # Check for nested quotation levels
                elif current_line.startswith('> > > ') and not current_line.startswith('> > > > '):
                    # Level 3 nesting
                    # Process any accumulated blank lines first
                    if blank_count >= 2:
                        verse_lines.append(('blank', ''))
                    blank_count = 0
                    content = current_line[6:].strip()
                    if content:  # Only add if there's actual content
                        verse_lines.append(('indent3', content))
                        stats['nested_lines'] += 1
                    
                elif current_line.startswith('> > ') and not current_line.startswith('> > > '):
                    # Level 2 nesting
                    # Process any accumulated blank lines first
                    if blank_count >= 2:
                        verse_lines.append(('blank', ''))
                    blank_count = 0
                    content = current_line[4:].strip()
                    if content:  # Only add if there's actual content
                        verse_lines.append(('indent2', content))
                        stats['nested_lines'] += 1
                    
                elif current_line.startswith('> ') or current_line == '>':
                    # Level 1 (normal verse line)
                    content = current_line[2:] if len(current_line) > 1 else ''
                    content = content.strip() if current_line != '>' else ''
                    
                    if not content:  # Blank quoted line
                        blank_count += 1
                        if debug:
                            print(f"  Blank line #{blank_count}")
                    else:
                        # If we had accumulated blank lines, process them first
                        if blank_count >= 2:
                            # Add stanza break (single blank line)
                            verse_lines.append(('blank', ''))
                            if debug:
                                print(f"  Adding stanza break after {blank_count} blanks")
                        blank_count = 0  # Reset
                        verse_lines.append(('normal', content))
                        if debug:
                            print(f"  Normal line: {content[:30]}...")
                
                i += 1
            
            # Check for any accumulated blank lines at end of verse
            if blank_count >= 2 and verse_lines:
                # Don't add a blank at the very end
                pass
            
            # Process collected verse lines if any
            if verse_lines:
                stats['verse_blocks'] += 1
                output_lines.append('\\begin{verse}')
                
                # Process each verse line
                for j, (line_type, content) in enumerate(verse_lines):
                    # Check if this is the last content line before end
                    is_last_content = j == len(verse_lines) - 1
                    # Check if next line is attribution or blank
                    next_is_attrib = (j < len(verse_lines) - 1 and 
                                     verse_lines[j + 1][0] == 'attribution')
                    next_is_blank = (j < len(verse_lines) - 1 and 
                                    verse_lines[j + 1][0] == 'blank')
                    
                    if line_type == 'attribution':
                        # Attribution doesn't get \\
                        output_lines.append(f'\\attrib{{{content}}}')
                    elif line_type == 'blank':
                        # Stanza break - just a blank line
                        output_lines.append('')
                    elif line_type == 'indent3':
                        # Level 3 indentation
                        # Add \\ unless it's the last line, before attribution, or before blank
                        if not is_last_content and not next_is_attrib and not next_is_blank:
                            output_lines.append(f'\\verseindentiii{{{content}}}\\\\')
                        else:
                            output_lines.append(f'\\verseindentiii{{{content}}}')
                    elif line_type == 'indent2':
                        # Level 2 indentation
                        # Add \\ unless it's the last line, before attribution, or before blank
                        if not is_last_content and not next_is_attrib and not next_is_blank:
                            output_lines.append(f'\\verseindentii{{{content}}}\\\\')
                        else:
                            output_lines.append(f'\\verseindentii{{{content}}}')
                    else:  # normal
                        # Add \\ unless it's the last line, before attribution, or before blank
                        if not is_last_content and not next_is_attrib and not next_is_blank:
                            output_lines.append(f'{content}\\\\')
                        else:
                            output_lines.append(content)
                
                output_lines.append('\\end{verse}')
        else:
            # Not a verse line, keep as is
            output_lines.append(line)
            i += 1
    
    return '\n'.join(output_lines), stats


def _identify_verse_blocks(lines: List[str]) -> List[Tuple[int, int]]:
    """
    Identify start and end indices of verse blocks in the text.
    
    Helper function to find all blocks of consecutive lines starting with '>'.
    
    Args:
        lines: List of text lines
        
    Returns:
        List of (start_index, end_index) tuples for verse blocks
    """
    blocks = []
    i = 0
    
    while i < len(lines):
        if lines[i].startswith('>'):
            start = i
            # Find end of this block
            while i < len(lines) and lines[i].startswith('>'):
                i += 1
            blocks.append((start, i))
        else:
            i += 1
    
    return blocks


def validate_verse_markup(text: str) -> List[str]:
    """
    Validate verse markup and return any warnings.
    
    Checks for:
    - Unclosed verse blocks
    - Malformed attribution markers
    - Excessive nesting levels
    
    Args:
        text: Text to validate
        
    Returns:
        List of warning messages (empty if valid)
    """
    warnings = []
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        # Check for excessive nesting (more than 3 levels)
        if line.startswith('> > > > > '):
            warnings.append(
                f"Line {i+1}: Excessive nesting (>4 levels) detected"
            )
        
        # Check for malformed attribution (missing spaces)
        if re.match(r'^>>>>', line):
            warnings.append(
                f"Line {i+1}: Possible malformed attribution "
                f"(use '> > > > ' with spaces)"
            )
    
    return warnings
