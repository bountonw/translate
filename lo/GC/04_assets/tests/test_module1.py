"""
test_module1.py
---------------
Regression tests for Module 1 preprocessing pipeline.
Tests only currently working features to prevent breakage.

Run: pytest tests/test_module1.py -v
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from module1_preprocess import (
    parse_yaml_frontmatter,
    extract_chapter_info,
    clean_markdown_body,
    generate_tex_header
)
from helpers.md_footnotes_to_tex import process_footnotes
from helpers.md_emphasis_to_tex import process_emphasis


class TestYAMLExtraction:
    """Test YAML frontmatter extraction."""
    
    def test_parse_yaml_frontmatter(self):
        """Test basic YAML parsing."""
        content = """---
chapter:
  number: 5
  title:
    lo: ບົດທີ 5
    en: Chapter 5
  url: https://example.com
---

Body text here."""
        
        yaml_data, body = parse_yaml_frontmatter(content)
        
        assert yaml_data['chapter']['number'] == '5'
        assert yaml_data['chapter']['title']['lo'] == 'ບົດທີ 5'
        assert 'Body text here.' in body
    
    def test_extract_chapter_info(self):
        """Test chapter info extraction."""
        yaml_data = {
            'chapter': {
                'number': '10',
                'title': {'lo': 'ພາກທີ 10'},
                'url': 'https://test.com'
            }
        }
        
        info = extract_chapter_info(yaml_data)
        
        assert info['number'] == '10'
        assert info['title_lo'] == 'ພາກທີ 10'
        assert info['url'] == 'https://test.com'
    
    def test_generate_tex_header(self):
        """Test TeX header generation."""
        info = {
            'number': '7',
            'title_lo': 'ບົດທີ 7',
            'url': 'https://source.com'
        }
        
        header = generate_tex_header(info)
        
        assert '\\laochapter{7}{ບົດທີ 7}' in header
        assert '\\source{https://source.com}' in header


class TestMarkdownCleaning:
    """Test markdown body cleaning functions."""
    
    def test_section_conversion(self):
        """Test ### heading to \\section{}."""
        body = "### ຫົວຂໍ້ພາສາລາວ\nText here."
        
        cleaned = clean_markdown_body(body)
        
        assert '\\section{ຫົວຂໍ້ພາສາລາວ}' in cleaned
        assert '###' not in cleaned
    
    def test_gc_reference_conversion(self):
        """Test {GC x.y} to \\egw{}."""
        body = "Text with {GC 1.5} reference."
        
        cleaned = clean_markdown_body(body)
        
        assert '\\egw{GC\\nbsp{}1.5}' in cleaned
        assert '{GC 1.5}' not in cleaned
    
    def test_remove_alignment_markers(self):
        """Test removal of ## {GC x.y} lines."""
        body = """## {GC 1.1}
Keep this text.
## {GC 1.2}
And this text."""
        
        cleaned = clean_markdown_body(body)
        
        assert '## {GC' not in cleaned
        assert 'Keep this text.' in cleaned
        assert 'And this text.' in cleaned


class TestEmphasisConversion:
    """Test emphasis marker conversions."""
    
    def test_bold(self):
        """Test **text** conversion."""
        text = "This is **bold** text."
        result, stats = process_emphasis(text)
        
        assert '\\textbf{bold}' in result
        assert '**' not in result
        assert stats['bold'] == 1
    
    def test_italic(self):
        """Test *text* conversion."""
        text = "This is *italic* text."
        result, stats = process_emphasis(text)
        
        assert '\\emph{italic}' in result
        assert stats['italic'] == 1
    
    def test_bold_italic(self):
        """Test ***text*** conversion."""
        text = "This is ***both*** text."
        result, stats = process_emphasis(text)
        
        assert '\\textbf{\\emph{both}}' in result
        assert stats['bold_italic'] == 1
    
    def test_underline(self):
        """Test ++text++ conversion."""
        text = "This is ++underlined++ text."
        result, stats = process_emphasis(text)
        
        assert '\\uline{underlined}' in result
        assert stats['underline'] == 1
    
    def test_strikethrough(self):
        """Test ~~text~~ conversion."""
        text = "This is ~~struck~~ text."
        result, stats = process_emphasis(text)
        
        assert '\\sout{struck}' in result
        assert stats['strikethrough'] == 1
    
    def test_escaped_asterisks(self):
        """Test \\* preservation."""
        text = "Math: 2 \\* 3 = 6"
        result, stats = process_emphasis(text)
        
        assert '2 \\* 3' in result
        assert '\\emph' not in result
        assert '\\textbf' not in result
    
    def test_escaped_underscores(self):
        """Test \\_ preservation."""
        text = "file\\_name\\_here.txt"
        result, stats = process_emphasis(text)
        
        assert 'file\\_name\\_here.txt' in result
        assert '\\emph' not in result
    
    def test_lao_text_emphasis(self):
        """Test emphasis with Lao text."""
        text = "ລາວ **ໜັງສືເຂັ້ມ** ແລະ *ໜັງສືເອນ* ທົດສອບ"
        result, stats = process_emphasis(text)
        
        assert '\\textbf{ໜັງສືເຂັ້ມ}' in result
        assert '\\emph{ໜັງສືເອນ}' in result


class TestFootnoteConversion:
    """Test footnote conversions."""
    
    def test_simple_footnote(self):
        """Test basic footnote conversion."""
        text = """Text[^1] here.

[^1]: Note content."""
        
        result, report = process_footnotes(text)
        
        assert '\\footnote{Note content.}' in result
        assert '[^1]:' not in result
        assert report['converted_count'] == 1
    
    def test_multiple_footnotes(self):
        """Test multiple footnotes."""
        text = """First[^a] and second[^b].

[^a]: Note A.
[^b]: Note B."""
        
        result, report = process_footnotes(text)
        
        assert '\\footnote{Note A.}' in result
        assert '\\footnote{Note B.}' in result
        assert report['converted_count'] == 2
    
    def test_footnote_with_emphasis(self):
        """Test footnote containing emphasis."""
        text = """Text[^1] here.

[^1]: Note with *italic* text."""
        
        result, _ = process_footnotes(text)
        # First footnotes, then emphasis
        result, _ = process_emphasis(result)
        
        assert '\\footnote{Note with \\emph{italic} text.}' in result
    
    def test_orphaned_marker(self):
        """Test orphaned marker detection."""
        text = "Text[^missing] here."
        
        result, report = process_footnotes(text)
        
        assert '[^missing]' in result  # Unchanged
        assert 'missing' in report['orphaned_markers']
    
    def test_orphaned_definition(self):
        """Test orphaned definition detection."""
        text = """Normal text.

[^unused]: This is never referenced."""
        
        result, report = process_footnotes(text)
        
        assert '[^unused]:' in result  # Preserved
        assert 'unused' in report['orphaned_definitions']


class TestIntegration:
    """Test integrated processing pipeline."""
    
    def test_full_pipeline(self):
        """Test complete processing flow."""
        content = """---
chapter:
  number: 1
  title:
    lo: ບົດທີ 1
  url: https://test.com
---

### ຫົວຂໍ້

Text with **bold** and footnote[^1].

[^1]: Note text.

{GC 1.1}"""
        
        # Parse YAML
        yaml_data, body = parse_yaml_frontmatter(content)
        info = extract_chapter_info(yaml_data)
        
        # Clean body
        cleaned = clean_markdown_body(body)
        
        # Generate header
        header = generate_tex_header(info)
        
        # Combine
        full_text = header + '\n\n' + cleaned
        
        # Process footnotes
        full_text, _ = process_footnotes(full_text)
        
        # Process emphasis
        full_text, _ = process_emphasis(full_text)
        
        # Check all conversions
        assert '\\laochapter{1}{ບົດທີ 1}' in full_text
        assert '\\section{ຫົວຂໍ້}' in full_text
        assert '\\textbf{bold}' in full_text
        assert '\\footnote{Note text.}' in full_text
        assert '\\egw{GC\\nbsp{}1.1}' in full_text
