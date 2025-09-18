#!/usr/bin/env python3
"""
Dictionary Loader Helper Module
Handles loading and merging of hierarchical dictionaries for the Lao
preprocessing pipeline.

Dictionary Hierarchy (highest to lowest priority):
1. Chapter patch (if exists)
2. Chapter dictionary (if exists)
3. Book patch (if exists)
4. Book dictionary (if exists)
5. Language patch (if exists)
6. Language main dictionary (always exists as fallback)
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class LaoDictionary:
    """Handles loading and lookup of Lao dictionary with break points."""
    
    def __init__(self, terms: Dict[str, str] = None):
        """
        Initialize dictionary with optional pre-loaded terms.
        
        Args:
            terms: Dictionary mapping clean_term -> coded_term
        """
        self.terms = terms if terms is not None else {}
        self.dictionary_sources = []  # Track where terms came from
    
    def load_from_file(self, dictionary_path: Path, source_name: str = None):
        """
        Load dictionary terms from a pipe-delimited file.
        
        Args:
            dictionary_path: Path to dictionary file
            source_name: Optional name for debugging/tracking
            
        Returns:
            int: Number of terms loaded from this file
        """
        if not dictionary_path.exists():
            return 0
            
        try:
            terms_loaded = 0
            with open(dictionary_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('%'):
                        continue
                    
                    # Parse pipe-delimited format:
                    # clean_term| coded_term % comment
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
                        # Higher priority dictionaries override lower ones
                        self.terms[clean_term] = coded_term
                        terms_loaded += 1
            
            if source_name:
                self.dictionary_sources.append(
                    f"{source_name}: {terms_loaded} terms"
                )
            
            return terms_loaded
            
        except UnicodeDecodeError:
            print(f"Error: Dictionary encoding issue: {dictionary_path}")
            return 0
        except PermissionError:
            print(f"Error: Permission denied: {dictionary_path}")
            return 0
        except Exception as e:
            print(f"Error loading {dictionary_path}: {e}")
            return 0
    
    def get_sorted_terms(self):
        """Return dictionary terms sorted by length (longest first)."""
        return sorted(self.terms.keys(), key=len, reverse=True)
    
    def merge(self, other_dict: 'LaoDictionary', override: bool = True):
        """
        Merge another dictionary into this one.
        
        Args:
            other_dict: Another LaoDictionary to merge
            override: If True, other_dict overrides existing terms
        """
        if override:
            self.terms.update(other_dict.terms)
        else:
            # Only add terms that don't exist
            for term, coded in other_dict.terms.items():
                if term not in self.terms:
                    self.terms[term] = coded
        
        self.dictionary_sources.extend(other_dict.dictionary_sources)


def load_hierarchical_dictionaries(
    chapter: str = None,
    book: str = None,
    debug: bool = False
) -> LaoDictionary:
    """
    Load dictionaries from all hierarchy levels with proper priority.
    
    Priority order (highest to lowest):
    1. Chapter patch (e.g., GC01_lo_patch.txt)
    2. Chapter dictionary (e.g., GC01_lo.txt)
    3. Book patch (e.g., GC_lo_patch.txt)
    4. Book dictionary (e.g., GC_lo.txt)
    5. Language patch (patch.txt)
    6. Language main dictionary (main.txt)
    
    Args:
        chapter: Chapter identifier (e.g., "GC01")
        book: Book identifier (e.g., "GC")
        debug: Enable debug output
        
    Returns:
        LaoDictionary: Merged dictionary with all applicable terms
    """
    # Get base paths
    script_dir = Path(__file__).parent.parent  # Go up from helpers/
    project_dict_dir = script_dir / "dictionaries"
    
    # Language-level dictionary path (4 levels up from scripts/)
    lang_dict_dir = script_dir / ".." / ".." / ".." / ".." / "lo" / "assets" / "dictionaries"
    lang_dict_dir = lang_dict_dir.resolve()
    
    # Initialize empty dictionary (will be filled in reverse priority order)
    merged_dict = LaoDictionary()
    
    # Track what we're loading for debug output
    load_sequence = []
    
    # 6. Language main dictionary (always exists as fallback)
    lang_main = lang_dict_dir / "main.txt"
    if lang_main.exists():
        count = merged_dict.load_from_file(lang_main, "Language main")
        load_sequence.append(f"Language main: {count} terms")
    else:
        print(f"Warning: Language main dictionary not found: {lang_main}")
        print(f"This file must exist as the fallback dictionary.")
        sys.exit(1)
    
    # 5. Language patch dictionary
    lang_patch = lang_dict_dir / "patch.txt"
    if lang_patch.exists():
        count = merged_dict.load_from_file(lang_patch, "Language patch")
        load_sequence.append(f"Language patch: {count} terms (override)")
    
    # 4. Book dictionary (if book specified and directory exists)
    if book and project_dict_dir.exists():
        book_dict = project_dict_dir / f"{book}_lo.txt"
        if book_dict.exists():
            count = merged_dict.load_from_file(book_dict, f"Book {book}")
            load_sequence.append(f"Book {book}: {count} terms (override)")
    
    # 3. Book patch (if book specified and directory exists)
    if book and project_dict_dir.exists():
        book_patch = project_dict_dir / f"{book}_lo_patch.txt"
        if book_patch.exists():
            count = merged_dict.load_from_file(
                book_patch, f"Book {book} patch"
            )
            load_sequence.append(
                f"Book {book} patch: {count} terms (override)"
            )
    
    # 2. Chapter dictionary (if chapter specified and directory exists)
    if chapter and project_dict_dir.exists():
        chapter_dict = project_dict_dir / f"{chapter}_lo.txt"
        if chapter_dict.exists():
            count = merged_dict.load_from_file(
                chapter_dict, f"Chapter {chapter}"
            )
            load_sequence.append(
                f"Chapter {chapter}: {count} terms (override)"
            )
    
    # 1. Chapter patch (highest priority)
    if chapter and project_dict_dir.exists():
        chapter_patch = project_dict_dir / f"{chapter}_lo_patch.txt"
        if chapter_patch.exists():
            count = merged_dict.load_from_file(
                chapter_patch, f"Chapter {chapter} patch"
            )
            load_sequence.append(
                f"Chapter {chapter} patch: {count} terms (override)"
            )
    
    # Debug output
    if debug and load_sequence:
        print("\nDictionary loading sequence:")
        for item in reversed(load_sequence):  # Show in priority order
            print(f"  {item}")
        print(f"Total merged terms: {len(merged_dict.terms)}")
    
    # Summary message
    total_terms = len(merged_dict.terms)
    sources = len([s for s in load_sequence if "0 terms" not in s])
    
    if not debug:
        # Simple message for production
        if chapter:
            print(f"Loaded {total_terms} terms for {chapter}"
                  f" (from {sources} sources)")
        elif book:
            print(f"Loaded {total_terms} terms for book {book}"
                  f" (from {sources} sources)")
        else:
            print(f"Loaded {total_terms} terms from language dictionary")
    
    return merged_dict


def load_simple_dictionary(dictionary_path: Path) -> LaoDictionary:
    """
    Load a single dictionary file (backwards compatibility).
    
    Args:
        dictionary_path: Path to dictionary file
        
    Returns:
        LaoDictionary: Loaded dictionary
    """
    dictionary = LaoDictionary()
    
    if not dictionary_path.exists():
        print(f"Error: Dictionary file not found: {dictionary_path}")
        sys.exit(1)
    
    count = dictionary.load_from_file(dictionary_path, str(dictionary_path))
    
    if count == 0:
        print(f"Error: No terms loaded from {dictionary_path}")
        sys.exit(1)
    
    print(f"Loaded {count} dictionary terms from {dictionary_path}")
    
    return dictionary


def clear_dictionary_cache():
    """
    Clear any cached dictionary data.
    Useful when processing multiple chapters in one session.
    """
    # Placeholder for future caching implementation
    pass


# Cache for multi-chapter processing
_dictionary_cache = {}


def get_cached_dictionary(
    chapter: str = None,
    book: str = None,
    debug: bool = False
) -> LaoDictionary:
    """
    Get dictionary with caching for multi-chapter processing.
    
    Args:
        chapter: Chapter identifier
        book: Book identifier  
        debug: Enable debug output
        
    Returns:
        LaoDictionary: Cached or newly loaded dictionary
    """
    cache_key = f"{book or 'none'}_{chapter or 'none'}"
    
    if cache_key not in _dictionary_cache:
        _dictionary_cache[cache_key] = load_hierarchical_dictionaries(
            chapter, book, debug
        )
    
    return _dictionary_cache[cache_key]


if __name__ == "__main__":
    # Test the dictionary loader
    print("Dictionary Loader Test")
    print("=" * 50)
    
    # Test hierarchical loading
    print("\n1. Testing hierarchical loading for GC01:")
    dict1 = load_hierarchical_dictionaries(
        chapter="GC01", book="GC", debug=True
    )
    print(f"   Loaded {len(dict1.terms)} total terms")
    
    # Test simple loading (backwards compatibility)
    print("\n2. Testing simple loading:")
    lang_dict = Path(__file__).parent.parent / ".." / ".." / ".." / ".." / "lo" / "assets" / "dictionaries" / "main.txt"
    if lang_dict.exists():
        dict2 = load_simple_dictionary(lang_dict.resolve())
        print(f"   Loaded {len(dict2.terms)} terms")
    
    # Test caching
    print("\n3. Testing cache:")
    dict3 = get_cached_dictionary("GC01", "GC")
    dict4 = get_cached_dictionary("GC01", "GC")
    print(f"   Same object: {dict3 is dict4}")
