#!/usr/bin/env python3
"""Convert Markdown-style blockquotes in Typst files to poetry code blocks."""

import sys
import os
import glob


def parse_blockquote_line(line):
    """Parse a blockquote line and return (indent_level, content).

    indent_level: 0 for '> text', 1 for '> > text', etc.
    content: the text after the blockquote markers.
    """
    count = 0
    i = 0
    while i < len(line):
        if line[i] == '>':
            count += 1
            i += 1
            # After '>', optionally skip one space
            if i < len(line) and line[i] == ' ':
                i += 1
        else:
            break
    content = line[i:]
    indent_level = count - 1  # First '>' = level 0
    return indent_level, content


def convert_blockquote(collect):
    """Convert a list of collected blockquote lines to a poetry block."""
    poetry_lines = []
    for line in collect:
        if line == '' or line.strip() == '':
            # Blank line (stanza break)
            poetry_lines.append('')
        elif line.startswith('>'):
            indent_level, content = parse_blockquote_line(line)
            if content.strip() == '':
                # Empty blockquote line (stanza break)
                poetry_lines.append('')
            else:
                indent = '  ' * indent_level
                poetry_lines.append(indent + content)
        else:
            poetry_lines.append(line)

    # Trim leading and trailing blank lines
    while poetry_lines and poetry_lines[0] == '':
        poetry_lines.pop(0)
    while poetry_lines and poetry_lines[-1] == '':
        poetry_lines.pop()

    return ['```poetry'] + poetry_lines + ['```']


def convert_content(content):
    """Convert all blockquotes in a Typst file content string."""
    lines = content.split('\n')
    output = []
    collect = []
    pending_blanks = []
    in_blockquote = False
    in_frontmatter = False
    frontmatter_count = 0

    for line in lines:
        # Handle frontmatter delimiters
        if line.strip() == '---':
            frontmatter_count += 1
            if frontmatter_count == 1:
                in_frontmatter = True
            elif frontmatter_count == 2:
                in_frontmatter = False
            output.append(line)
            continue

        # Pass frontmatter lines through unchanged
        if in_frontmatter:
            output.append(line)
            continue

        if in_blockquote:
            if line.startswith('>'):
                # Continue blockquote — flush pending blanks as stanza breaks
                collect.extend(pending_blanks)
                pending_blanks = []
                collect.append(line)
            elif line.strip() == '':
                # Blank line — might be stanza break or end of blockquote
                pending_blanks.append(line)
            else:
                # Non-blank, non-'>' line — end of blockquote
                in_blockquote = False
                output.extend(convert_blockquote(collect))
                output.extend(pending_blanks)  # Preserve trailing blank lines
                collect = []
                pending_blanks = []
                output.append(line)
        else:
            if line.startswith('>'):
                # Start blockquote
                in_blockquote = True
                collect = [line]
                pending_blanks = []
            else:
                output.append(line)

    # Handle blockquote at end of file
    if in_blockquote:
        output.extend(convert_blockquote(collect))
        output.extend(pending_blanks)

    return '\n'.join(output)


def process_file(filepath, dry_run=False):
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()

    converted = convert_content(original)

    if converted == original:
        return False  # No changes

    if dry_run:
        return True

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(converted)

    return True


def main():
    dry_run = '--dry-run' in sys.argv

    base_dir = os.path.join(os.path.dirname(__file__), 'th', 'PP')
    pattern = os.path.join(base_dir, '**', '*.typ')
    files = sorted(glob.glob(pattern, recursive=True))

    modified = 0
    for filepath in files:
        if process_file(filepath, dry_run=dry_run):
            modified += 1
            print(f"{'Would modify' if dry_run else 'Modified'}: {filepath}")

    print(f"\n{'Would modify' if dry_run else 'Modified'} {modified} files.")


if __name__ == '__main__':
    main()
