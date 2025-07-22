#!/usr/bin/env python3
"""
Complete Lao Bible Books Reference Data
Used for scripture reference protection in preprocessing pipeline.

This file contains all 66 Bible book names in Lao as used in
the Revised Lao Version 2015 3rd Edition.
"""

# All 66 Bible books in Lao
# Format: "bookname" (will be used for pattern matching)
ALL_BIBLE_BOOKS = [
    # Old Testament (39 books)
    "ປະຖົມມະການ",      # Genesis
    "ອົບພະຍົບ",        # Exodus  
    "ລະບຽບພວກເລວີ",         # Leviticus
    "ຈົດບັນຊີ",            # Numbers
    "ພຣະບັນຍັດສອງ",        # Deuteronomy
    "ໂຢຊວຍ",          # Joshua
    "ພວກຜູ້ປົກຄອງ",       # Judges
    "ນາງຣຸດ",              # Ruth
    "1 ຊາມູເອນ",        # 1 Samuel
    "2 ຊາມູເອນ",        # 2 Samuel
    "1 ກະສັດ",          # 1 Kings
    "2 ກະສັດ",          # 2 Kings
    "1 ຂ່າວຄາວ",        # 1 Chronicles
    "2 ຂ່າວຄາວ",        # 2 Chronicles
    "ເອຊະຣາ",            # Ezra
    "ເນເຫມີຢາ",           # Nehemiah
    "ເອສະເທີ",           # Esther
    "ໂຢບ",              # Job
    "ເພງສັນລະເສີນ",           # Psalms
    "ສຸພາສິດ",          # Proverbs
    "ປັນຍາຈານ",         # Ecclesiastes
    "ຍອດເພງ",      # Song of Songs
    "ເອຊາຢາ",           # Isaiah
    "ເຢເຣມີຢາ",           # Jeremiah
    "ເພງຄ່ຳຄວນ",          # Lamentations
    "ເອເຊກຽນ",       # Ezekiel
    "ດານີເອນ",          # Daniel
    "ໂຮເສອາ",          # Hosea
    "ໂຢເອນ",           # Joel
    "ອາໂມດ",            # Amos
    "ໂອບາດີຢາ",           # Obadiah
    "ໂຢນາ",             # Jonah
    "ມີກາ",             # Micah
    "ນາຮູມ",            # Nahum
    "ຮາບາກຸກ",          # Habakkuk
    "ເຊຟານີຢາ",           # Zephaniah
    "ຮັກກາຍ",            # Haggai
    "ເຊກາຣີຢາ",           # Zechariah
    "ມາລາກີ",           # Malachi
    
    # New Testament (27 books)
    "ມັດທາຍ",           # Matthew
    "ມາຣະໂກ",           # Mark
    "ລູກາ",             # Luke
    "ໂຢຮັນ",            # John
    "ກິດຈະການ",         # Acts
    "ໂຣມ",              # Romans
    "1 ໂກຣິນໂທ",        # 1 Corinthians
    "2 ໂກຣິນໂທ",        # 2 Corinthians
    "ຄາລາເຕຍ",         # Galatians
    "ເອເຟໂຊ",          # Ephesians
    "ຟີລິບປອຍ",          # Philippians
    "ໂກໂລຊາຍ",          # Colossians
    "1 ເທສະໂລນິກ",      # 1 Thessalonians
    "2 ເທສະໂລນິກ",      # 2 Thessalonians
    "1 ຕີໂມທຽວ",        # 1 Timothy
    "2 ຕີໂມທຽວ",        # 2 Timothy
    "ຕີໂຕ",              # Titus
    "ຟີເລໂມນ",          # Philemon
    "ເຮັບເຣີ",          # Hebrews
    "ຢາໂກໂບ",          # James
    "1 ເປໂຕ",          # 1 Peter
    "2 ເປໂຕ",          # 2 Peter
    "1 ໂຢຮັນ",          # 1 John
    "2 ໂຢຮັນ",          # 2 John
    "3 ໂຢຮັນ",          # 3 John
    "ຢູດາ",             # Jude
    "ພຣະນິມິດ"         # Revelation
]

def get_all_bible_books():
    """Return list of all Bible books in Lao."""
    return ALL_BIBLE_BOOKS.copy()