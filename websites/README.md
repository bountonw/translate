# The website www.laoegw.com

This folder builds the site. `books.yaml` lists the books on the home page, `news.yaml` holds the news lines, `assets/` holds the build scripts, layouts and fonts, and `laoegw/` is the built site that is uploaded to the server.

## Queue

Website work that is agreed but not scheduled, in the order it will be done. An entry is deleted when its work is finished.

### 1. Add the Thai books to the website

The website build, `websites/assets/scripts/build_book.py`, reads Markdown chapters with GC's front matter. Add MB and LBF first, then SC and PP, which are written in Typst and need a Typst reader in the converter; SJ waits for its editing. Rulings of 16 October 2026: the Sarabun font; the page words สารบัญ, บทที่ and ต้นฉบับภาษาอังกฤษ; LBF's paragraph codes hidden on the page, as its metadata asks, with the paragraph link addresses kept, and its `original` source line left off; Thai line breaks left to the browser for now; no cover images until covers exist. Each book needs the Thai layout folder `websites/assets/layout/th/`, a contents page and a line in the GitHub check.

Each book's pages go on a branch of its own named BOOK-website, made from main, never on another book's branch.

Detail: this entry is the whole brief. Medium for MB and LBF; large for SC and PP.

### 2. An EPUB of every book on the website

Every book published on the website also gets an EPUB to download. The Lao GC EPUB is live at www.laoegw.com/lo/GC/GC_lo.epub. The EPUB file stays out of git.

Each book's EPUB builder goes on a branch of its own named BOOK-epub, made from main, never on another book's branch.

Detail: none written; this entry is the whole brief. Medium.
