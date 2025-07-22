#!/usr/bin/env python3
"""
Lao Bible Numbered Books Reference Data
Used for scripture reference protection in preprocessing pipeline.

This file contains the numbered Bible book names in Lao as used in
the Revised Lao Version 2015 3rd Edition.

These books need special handling to protect the space between the number
and the book name (e.g., "1 ຊາມູເອນ" → "1\nbsp ຊາມູເອນ").
"""

# Numbered Bible books in Lao
# Format: "number bookname" (with regular space)
# Will be converted to "number\nbsp bookname" during preprocessing
NUMBERED_BIBLE_BOOKS = [
    # Samuel
    "1 ຊາມູເອນ",
    "2 ຊາມູເອນ",
    
    # Kings  
    "1 ກະສັດ",
    "2 ກະສັດ",
    
    # Chronicles
    "1 ຂ່າວຄາວ", 
    "2 ຂ່າວຄາວ",
    
    # Corinthians
    "1 ໂກຣິນໂທ",
    "2 ໂກຣິນໂທ",
    
    # Thessalonians
    "1 ເທສະໂລນິກ",
    "2 ເທສະໂລນິກ",
    
    # Timothy
    "1 ຕີໂມທຽວ",
    "2 ຕີໂມທຽວ",
    
    # Peter
    "1 ເປໂຕ",
    "2 ເປໂຕ",
    
    # John
    "1 ໂຢຮັນ",
    "2 ໂຢຮັນ", 
    "3 ໂຢຮັນ"
]

def get_numbered_books():
    """Return list of numbered Bible books in Lao."""
    return NUMBERED_BIBLE_BOOKS.copy()

def get_numbered_books_patterns():
    """Return regex-ready patterns for numbered Bible books."""
    # Escape any special regex characters and create pattern list
    import re
    patterns = []
    for book in NUMBERED_BIBLE_BOOKS:
        # Escape special regex characters
        escaped = re.escape(book)
        patterns.append(escaped)
    return patterns