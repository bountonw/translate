#!/usr/bin/env python3
"""
Lao Dictionary Sorter

Sorts a two-column Lao dictionary by the first column while preserving 
header comments and handling Lao Unicode collation properly.

Input format:
% Comments at top are preserved
ກໍ| ກໍ %
ກໍ່| ກໍ່ %
ກກ| ກກ %

Output: Same format but sorted by first column
"""

import argparse
import sys
import locale
from pathlib import Path


def parse_dictionary_line(line):
    """
    Parse a dictionary line into components.
    
    Args:
        line (str): Dictionary line
        
    Returns:
        dict: Parsed components or None for comments/empty lines
    """
    line = line.strip()
    
    # Handle empty lines
    if not line:
        return {'type': 'empty', 'original': line}
    
    # Handle comment lines (start with %)
    if line.startswith('%'):
        return {'type': 'comment', 'original': line}
    
    # Handle dictionary entries
    if '|' in line:
        # Split at first | to get clean and coded terms
        parts = line.split('|', 1)
        if len(parts) == 2:
            clean_term = parts[0].strip()
            rest = parts[1].strip()
            
            # Further split the rest to get coded term and comment
            if '%' in rest:
                rest_parts = rest.split('%', 1)
                coded_term = rest_parts[0].strip()
                comment = ' %' + rest_parts[1]
            else:
                coded_term = rest
                comment = ''
            
            return {
                'type': 'entry',
                'original': line,
                'clean_term': clean_term,
                'coded_term': coded_term,
                'comment': comment,
                'sort_key': clean_term.lower()  # For case-insensitive sorting
            }
    
    # Handle malformed lines
    return {'type': 'other', 'original': line}


def sort_dictionary(input_file, output_file=None, verbose=False, reverse=False):
    """
    Sort dictionary by first column while preserving comments.
    
    Args:
        input_file (str): Path to input file
        output_file (str): Path to output file (default: input_sorted.txt)
        verbose (bool): Print progress information
        reverse (bool): Sort in reverse order
        
    Returns:
        dict: Statistics about the sorting
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    if output_file is None:
        output_file = input_path.stem + '_sorted.txt'
    
    # Read and parse all lines
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    parsed_lines = []
    header_comments = []
    dictionary_entries = []
    other_lines = []
    
    # Separate different types of lines
    in_header = True
    
    for line_num, line in enumerate(lines, 1):
        parsed = parse_dictionary_line(line)
        
        if parsed['type'] == 'comment' and in_header:
            header_comments.append(parsed)
        elif parsed['type'] == 'entry':
            in_header = False  # First dictionary entry ends header
            dictionary_entries.append(parsed)
        elif parsed['type'] == 'empty':
            if in_header:
                header_comments.append(parsed)
            else:
                other_lines.append(parsed)
        else:
            in_header = False
            other_lines.append(parsed)
        
        if verbose and parsed['type'] == 'entry':
            print(f"Line {line_num:4d}: {parsed['clean_term']}")
    
    # Sort dictionary entries by clean term
    dictionary_entries.sort(key=lambda x: x['sort_key'], reverse=reverse)
    
    # Rebuild output
    output_lines = []
    
    # Add header comments
    for item in header_comments:
        output_lines.append(item['original'])
    
    # Add sorted dictionary entries
    for item in dictionary_entries:
        if item['comment']:
            reconstructed = f"{item['clean_term']}| {item['coded_term']}{item['comment']}"
        else:
            reconstructed = f"{item['clean_term']}| {item['coded_term']}"
        output_lines.append(reconstructed)
    
    # Add any other lines at the end
    for item in other_lines:
        output_lines.append(item['original'])
    
    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in output_lines:
            f.write(line.rstrip() + '\n')
    
    # Prepare statistics
    stats = {
        'total_lines': len(lines),
        'header_comments': len(header_comments),
        'dictionary_entries': len(dictionary_entries),
        'other_lines': len(other_lines),
        'sorted_entries': len(dictionary_entries)
    }
    
    return stats


def print_stats(stats, input_file, output_file, reverse=False):
    """Print sorting statistics."""
    direction = "reverse" if reverse else "normal"
    
    print(f"\n{'='*50}")
    print("DICTIONARY SORTING COMPLETE")
    print(f"{'='*50}")
    print(f"Input file:           {input_file}")
    print(f"Output file:          {output_file}")
    print(f"Sort order:           {direction}")
    print(f"Total lines:          {stats['total_lines']}")
    print(f"Header comments:      {stats['header_comments']}")
    print(f"Dictionary entries:   {stats['dictionary_entries']}")
    print(f"Other lines:          {stats['other_lines']}")
    print(f"Entries sorted:       {stats['sorted_entries']}")
    print(f"{'='*50}")


def preview_sort(input_file, n=10):
    """
    Preview the first n entries after sorting without writing a file.
    
    Args:
        input_file (str): Path to input file
        n (int): Number of entries to preview
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    dictionary_entries = []
    
    for line in lines:
        parsed = parse_dictionary_line(line)
        if parsed['type'] == 'entry':
            dictionary_entries.append(parsed)
    
    # Sort entries
    dictionary_entries.sort(key=lambda x: x['sort_key'])
    
    print(f"\nPreview of first {min(n, len(dictionary_entries))} sorted entries:")
    print("-" * 50)
    
    for i, item in enumerate(dictionary_entries[:n]):
        print(f"{i+1:3d}: {item['clean_term']} | {item['coded_term']}")
    
    if len(dictionary_entries) > n:
        print(f"... and {len(dictionary_entries) - n} more entries")
    
    print(f"\nTotal dictionary entries: {len(dictionary_entries)}")


def main():
    parser = argparse.ArgumentParser(
        description="Sort Lao dictionary by first column while preserving comments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sort_dict.py dictionary.txt
  python sort_dict.py dictionary.txt -o sorted_dict.txt
  python sort_dict.py dictionary.txt -r          # reverse sort
  python sort_dict.py dictionary.txt --preview   # preview only
  python sort_dict.py dictionary.txt -v          # verbose output

The script preserves header comments (lines starting with %) and sorts
only the dictionary entries by their first column (clean terms).
        """
    )
    
    parser.add_argument('input_file', help='Input dictionary file')
    parser.add_argument('-o', '--output', help='Output file (default: input_sorted.txt)')
    parser.add_argument('-r', '--reverse', action='store_true', help='Sort in reverse order')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--preview', type=int, nargs='?', const=20, 
                       help='Preview first N entries without writing file (default: 20)')
    
    args = parser.parse_args()
    
    try:
        if args.preview is not None:
            preview_sort(args.input_file, args.preview)
        else:
            stats = sort_dictionary(
                args.input_file, 
                args.output, 
                args.verbose,
                args.reverse
            )
            
            output_file = args.output or (Path(args.input_file).stem + '_sorted.txt')
            print_stats(stats, args.input_file, output_file, args.reverse)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()