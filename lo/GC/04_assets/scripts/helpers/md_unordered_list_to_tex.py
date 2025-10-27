r"""
md_unordered_list_to_tex.py
---------------------

Purpose:
    Convert Markdown unordered lists (* text here...) to LaTeX commands.

    This is NOT meant to be robust. It just handles the simple list in the intro,
    for now. It might handle more. It might not. But it does enough for now.
    
Responsibilities:
    • Turns unordered lists into LaTeX \begin{itemize} lists
"""

import re
import logging
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)

def process_unordered_lists(text: str) -> str:
    """
    Convert Markdown unordered list markers to LaTeX commands.
    
    Args:
        text: Markdown text with unordered list markers
        
    Returns:
        Tuple of:
        - Processed unordered text with LaTeX commands
    """

    output = ''
    curr_indent = 0
    last_indent = 0
    for line in iter(text.splitlines()):
        if line.strip().startswith('* '): # this is a list element item
            curr_indent = line.count('    ')
            # print('curr_indent', curr_indent, 'last_indent', last_indent)
            spacer = '    ' * curr_indent # for visualizing more easily
            extra_spacer = '    ' * (curr_indent + 1)
            spacer = ''
            extra_spacer = ''
            if curr_indent == 0 or curr_indent > last_indent:
                output += spacer + '\\begin{itemize}\n'
                # print('begin itemize')
            elif curr_indent < last_indent:
                output += extra_spacer + '\\end{itemize}\n'
                # print('end itemize')
            output += line.lstrip().replace('* ', extra_spacer + '\\item ', 1) + '\n'
            last_indent = curr_indent
        elif last_indent > 0:
            while last_indent > 0:
                spacer = '    ' * last_indent
                spacer = ''
                output += spacer + '\\end{itemize}\n'
                last_indent = last_indent - 1
            output += line + '\n'
        else:
            output += line + '\n'
    # output remaining lists
    while last_indent > 0:
        spacer = '    ' * last_indent
        spacer = ''
        output += spacer + '\\end{itemize}\n'
        last_indent = last_indent - 1

    return output
