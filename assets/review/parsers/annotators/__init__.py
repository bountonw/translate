"""Annotators: modules that mark spans in a parsed paragraph, such as Bible references or glossary terms.

No annotator exists yet. A book lists the ones it uses in books.json, as
"annotators": ["bible_refs"], and parsers.load_chapter runs them in that order
over every paragraph. A module here offers one function:

    def annotate(paragraph, book):
        '''paragraph: {"a", "th", "fn", "en"} as the format module made it;
        book: the books.json entry. Returns the paragraph, with spans in the
        reserved form of server/content.py, as
        <span data-kind="bible" data-value="John 3:16">...</span>.'''

An annotator changes only the HTML around the words; it never changes the words.
"""
