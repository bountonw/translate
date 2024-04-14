#==[ FOLDERS ]==================================================================

# We set ALL folders through variables to make them easily configurable.

# Input directory
SRCDIR = ../..
# Partial output directory
TEXDIR = ./tex
# Draft output directory
DFTDIR = ./draft
# Templates directory
TPLDIR = ./templates
# Filters directory
FILDIR = ./filters
# Dictionaries directory
DICDIR = ./dictionaries
# Html directory
HTMDIR = ./html
# Font directory
FNTDIR = ../../th/assets/fonts
# Ebooks directory
EBKDIR = ./ebooks
# Preprocessed directory
PREDIR = ./preprocessed
# Graphs directory
GPHDIR = ./graphs
# Draft output directory
LBFDIR = ./lbf

#==[ FILE LISTS ]===============================================================

# We define a list that gathers source files.
# Sorting is important since this list - and the lists derived
# from it - are used also for chapter concatenation.
ALLSRC = $(sort $(wildcard $(SRCDIR)/*.md))

# We define lists for files of intermediate build steps.
# we use the previous list and simply replace paths/suffixes.
ALLPRE = $(patsubst $(SRCDIR)/%.md,$(PREDIR)/%.md,$(ALLSRC))
ALLTEX = $(patsubst $(SRCDIR)/%.md,$(TEXDIR)/%.tex,$(ALLSRC))
ALLHTM = $(patsubst $(SRCDIR)/%.md,$(HTMDIR)/%.html,$(ALLSRC))
ALLPDF = $(patsubst $(SRCDIR)/%.md,$(DFTDIR)/%.pdf,$(ALLSRC))
ALLODT = $(patsubst $(SRCDIR)/%.md,$(DFTDIR)/%.odt,$(ALLSRC))

#==[ GLOBAL TARGETS ]===========================================================

# We define some targets that are easy to call from the console.
# Note the use of the file lists as prerequisites: targets for those single
# files (or better, the single-file target masks that match them) are still
# undefined, but we'll take care of those in a moment.

# Preprocessing is where most custom markup parsing happens.
# See the single-file mask for details.
preprocessed: $(ALLPRE)

# The following targets just gather the single-chapter
# and the whole-book ones for each format.
latex: $(ALLTEX) $(TEXDIR)/book.tex
pdf: $(ALLPDF) $(DFTDIR)/book.pdf
odt: $(ALLODT) $(DFTDIR)/book.odt

# The HTML targets bundles togeter chapter, toc and index production.
html: $(ALLHTM) $(HTMDIR)/toc.html $(HTMDIR)/index.html

# The ebook target is basically just an alias.
ebook: $(EBKDIR)/book.epub

# This target deletes intermediate files.
clean:
	rm -rf $(PREDIR)
	rm -rf $(TEXDIR)
	rm -rf $(GPHDIR)

# Delete both intermediate and final files.
clobber:
	make clean
	rm -rf $(DFTDIR)
	rm -rf $(HTMDIR)
	rm -rf $(EBKDIR)
	rm -rf $(LBFDIR)

#==[ PREPROCESSING: TEXT -> MARKDOWN ]==========================================

# This target produces a single preprocessed chapter, translating the text file
# to a markdown filse, using the chapter.md template and the book metadata.

# In order, we:
#   - create the output folder
#   - concatenate metadata and source text
#   - wrap thai fragments inside version tags in spans with class="th"
#   - replace Bible version tags with inline html
#   - replace paragraph tags with inline html
#   - pass the result through pandoc, with some extra configuration
#       - prefix ids with file basename $* to avoid conflicts in html/epub doc
#       - set base header to lvl 2 (so # in the source means H2) since we apply
#         custom H1 titles generated from metadata (see template file to see how)
#       - set read/write format to standalone markdown
#       - set current/previous/next chapter names as metadata to make (html)
#         navigation much easier to set up through html chapter template.
#         NOTE: to fetch prev/next chapter file basename we use a simple
#         ls | grep | tail trick, but we are under the assumption that
#         alphabetical order of filenames corresponds to chapter order!
#       - apply the markdown chapter template

# NOTE: this was an early solution for thai segment wrapping, but it's sluggish
#   perl -S -p -e 's/(\B[^!-~]+\B)(?=[^()]*?\))/<span class="th">\1<\/span>/g'

# usage: make preprocessed/filename.md
$(PREDIR)/%.md : $(SRCDIR)/%.md $(TPLDIR)/chapter.md
	mkdir -p $(PREDIR)/$(shell dirname $*)
	cat $(SRCDIR)/$(shell dirname $(shell dirname $*))/metadata.yaml $(SRCDIR)/$*.md \
  | \
	pandoc \
	  --id-prefix='$*@' \
	  --from markdown \
	  --to markdown \
	  --standalone \
	  --variable=this:$* \
	  --variable=prev:$(notdir $(basename $(shell ls $(SRCDIR)/*.md | grep -B 1 $(SRCDIR)/$*.md | head -n 1))) \
	  --variable=next:$(notdir $(basename $(shell ls $(SRCDIR)/*.md | grep -A 1 $(SRCDIR)/$*.md | tail -n +2))) \
	  --template=$(TPLDIR)/chapter.md \
	> $(PREDIR)/$*.md

#==[ LATEX SOURCECODE - SINGLE CHAPTER ]========================================

# This target produces a single TeX sourcefile for a chapter (not standalone!).
# Prerequisites are the preprocessed source file, the single chapter TeX
# template, a custom pandoc filter to translate some specific HTML to macros
# (see filter code for details) and the hyphenation dictionaries.

# In order, we:
#   - create the output folder
#   - read the preprocessed source
#   - feed it through pandoc, with some extra configuration:
#       - input markdown and output LaTeX code
#       - apply the single chapter TeX template
#       - apply the custom pandoc filter (see filter code for details)
#   - feed result through swath, that is a TeX-aware hyphenator,
#       - using | as syllable delimiter
#       - using unicode input/output (necessary, since it's thai)
#       - use greedy word matching (prefer long words, default behaviour)
#   - save it to target folder
# So we have a maximally hyphenated TeX file.
# Then we apply some tricky substitutions to this file (in place):
#   - read penalized-breaks line by line, i.e. one possible penalized
#     break at a time, and replace occurrences with double bars, i.e.
#     replace "some|thing" with "some||thing"
#   - read forbidden-breaks line by line, i.e. one possible forbidden
#     break at a time, and replace occurrences with unbroken words, i.e.
#     replace "some|thing" with "something"
#   - replace double bars (penalized breaks) with the macro \pwbr
#   - replace single bars (ordinary breaks) with the macro \wbr
# So we have a TeX files where word breaks are applied only when required,
# and are classified by priority and handled by the macros \pwbr and \wbr.

# usage: make tex/filename.tex
# usage: make tex/filename.tex

$(TEXDIR)/%.tex : $(PREDIR)/%.md $(TPLDIR)/chapter.tex $(FILDIR)/inline-latex.hs $(DICDIR)/penalized-breaks $(DICDIR)/forbidden-breaks
#$(TEXDIR)/%.tex : $(PREDIR)/%.md $(TPLDIR)/chapter.tex $(DICDIR)/penalized-breaks $(DICDIR)/forbidden-breaks
	mkdir -p $(TEXDIR)/${shell dirname $*}
	cat $(PREDIR)/$*.md \
	| \
	pandoc \
	  --from markdown \
	  --to latex \
	  --template=$(TPLDIR)/chapter.tex \
	  --lua-filter $(FILDIR)/remove-paragraph-code-headings.lua \
	  --lua-filter $(FILDIR)/transform-poetry.lua \
	  --variable=modified:"$(shell git log -n 1 --pretty=format:%cd --date=format:"%Y-%m-%d at %H:%M" $(SRCDIR)/$*.md)" \
	| \
	swath \
	  -b "|" \
	  -u u,u \
	  -m max \
	> $(TEXDIR)/$*.tex 
	while read a z; do perl -S -pi -e \
	  "s/(?!\p{Thai})$$a\|$$z(?<!\p{Thai})/$$a||$$z/g" \
	  $(TEXDIR)/$*.tex; done < $(DICDIR)/penalized-breaks
	while read a z; do perl -S -pi -e \
	  "s/(?!\p{Thai})$$a\|$$z(?<!\p{Thai})/$$a$$z/g" \
	  $(TEXDIR)/$*.tex; done < $(DICDIR)/forbidden-breaks
	perl -S -pi -e 's/\|\|/{\\pwbr}/g' $(TEXDIR)/$*.tex
	perl -S -pi -e 's/\|/{\\wbr}/g' $(TEXDIR)/$*.tex

#==[ PDF DRAFT - SINGLE CHAPTER ]===============================================

# This target generates the PDF draft for a single chapter; its prerequisites
# are the tex source for the chapter, the template for tex chapters and the
# tex template for drafting. The two templates are applied in that order.

# usage: make draft/filename.pdf
$(DFTDIR)/%.pdf : $(TEXDIR)/%.tex $(TPLDIR)/chapter.tex $(TPLDIR)/draft.tex
	mkdir -p $(DFTDIR)/${shell dirname $*}
	pandoc \
	  $(TEXDIR)/$*.tex \
	  --from latex+raw_tex \
	  --to latex \
	  --pdf-engine=xelatex \
	  --template=$(TPLDIR)/chapter.tex \
	  --template=$(TPLDIR)/draft.tex \
	  --output $(DFTDIR)/$*.pdf

#==[ LBF ICML - SINGLE CHAPTER ]===============================================

# (LBF-only) This target generates the ICML files for a single chapter; its
# prerequisites are the tex source for the chapter.

# usage: make lbf/filename.icml
$(LBFDIR)/%.icml:
	mkdir -p $(PREDIR)/$(shell dirname $*)	
	cat $(SRCDIR)/$(shell dirname $(shell dirname $*))/metadata.yaml $(SRCDIR)/$*.md \
  | \
	pandoc \
	  --id-prefix='$*@' \
	  --from markdown \
	  --to markdown \
	  --standalone \
	  --variable=this:$* \
	  --template=$(TPLDIR)/chapter-lbf.md \
	> $(PREDIR)/$*.md
	mkdir -p $(LBFDIR)/${shell dirname $*}
	pandoc \
	  $(PREDIR)/$*.md \
	  --from markdown \
	  --lua-filter $(FILDIR)/remove-paragraph-code-headings.lua \
	  --lua-filter $(FILDIR)/transform-poetry.lua \
	  --lua-filter $(FILDIR)/remove-paragraph-codes.lua \
	  --standalone \
	  --output $(LBFDIR)/$*.icml

#==[ LATEX SOURCECODE - WHOLE BOOK ]============================================

# This target generates the tex sourcecode for the whole book. there is nothing
# tricky here, we're just letting pandoc concatenate the single chapter sources
# ALLTEX. Note the resulting source file is not a compilable standalone!

# usage: make tex/book.tex
$(TEXDIR)/book.tex : $(ALLTEX)
	mkdir -p $(TEXDIR)
	pandoc \
	  --from latex \
	  --parse-raw \
	  --to latex \
	  --output $(TEXDIR)/book.tex \
	  $(ALLTEX)

#==[ PDF BOOK - WHOLE BOOK ]====================================================

# This target generates the PDF draft for the whole book. We are just applying
# the drafting tex template to the whole-book source file and letting pandoc
# compile it using XeLaTeX. Note XeLaTeX is needed to use OTF thai fonts.

# usage: make draft/book.pdf
$(DFTDIR)/book.pdf : $(TEXDIR)/book.tex $(TPLDIR)/draft.tex
	mkdir -p $(DFTDIR)
	pandoc \
	  --from latex \
	  --parse-raw \
	  --to latex \
	  --pdf-engine=xelatex \
	  --template=$(TPLDIR)/draft.tex \
	  --output $(DFTDIR)/book.pdf \
	  $(TEXDIR)/book.tex

#==[ ODT DRAFT - SINGLE CHAPTER ]===============================================

# This target generates the ODT draft for a single chapter from the source text
# and the global book metadata. Note the template/reference-odt configuration
# is a bit tricky: while we're using an odt template, the styling comes from
# the reference-odt (that was initially produced by pandoc to ensure
# compatibility and then tweaked). So, we effectively have two templating
# dependencies: one for structure and one for presentation/styling.
# We also pass the current date through the metadata as a timestamp for
# the draft.

# usage: make draft/filename.odt
$(DFTDIR)/%.odt : $(SRCDIR)/%.md $(TPLDIR)/draft.odt $(TPLDIR)/reference.odt $(SRCDIR)/metadata.yaml
	mkdir -p $(DFTDIR)
	pandoc \
	  --from markdown \
	  --to odt \
	  --template=$(TPLDIR)/draft.odt \
	  --variable=date:$(shell date +%FT%T.%N) \
	  --reference-odt=$(TPLDIR)/reference.odt \
	  --output $(DFTDIR)/$*.odt \
	  $(SRCDIR)/metadata.yaml \
	  $(SRCDIR)/$*.md
# TODO: check wheter it's ok to pass *.md instead of preprocessed *.md

#==[ ODT DRAFT - WHOLE BOOK ]===================================================

# This target generates an ODT draft for the whole book. Very similar to
# the single-chapter target, it just acts on the concatenation of all
# preprocessed chapters instead of a single one.

# usage: make draft/book.odt
$(DFTDIR)/book.odt : $(ALLPRE) $(TPLDIR)/reference.odt
	mkdir -p $(DFTDIR)
	pandoc \
	  --from markdown \
	  --to odt \
	  --template=$(TPLDIR)/draft.odt \
	  --variable=date:$(shell date +%FT%T.%N) \
	  --reference-odt=$(TPLDIR)/reference.odt \
	  --output $(DFTDIR)/book.odt \
	  $(SRCDIR)/metadata.yaml \
	  $(ALLPRE)

#==[ HTML - SINGLE CHAPTER ]====================================================

# This target generates the HTML for a single chapter. Note that in depends not
# only on the book metadata, the preprocessed source and the HTML default
# template, but also on html_assets. It is a target that copies static resources
# like css/js scripts to the output folder.
# Note we prefix ids with the file basename to avoid conflicts in hyperlinks.

# usage: make html/filename.html
$(HTMDIR)/%.html : html_assets $(SRCDIR)/metadata.yaml $(PREDIR)/%.md $(TPLDIR)/html/default.html
	pandoc \
	  --from markdown \
	  --to html5 \
	  --id-prefix='$*@' \
	  --template=$(TPLDIR)/html/default.html \
	  --output $(HTMDIR)/$*.html \
	  $(SRCDIR)/metadata.yaml \
	  $(PREDIR)/$*.md

#==[ HTML TOC ]=================================================================

# This target generates the HTML table of contents. Note that in depends not
# only on the book metadata, the preprocessed source, the HTML default
# template, the HTML toc template and all HTML chapters, but also on html_assets:
# it is a target that copies static resources like css/js scripts to the output folder.

# The procedure is a bit tricky: pandoc can produce TOCs only for single-page
# HTML documents. But we can work around that.
# First we feed pandoc all the HTML chapters, applying a special toc-only
# template and letting it generate the toc with maximum depth (6).
# This way we obtain a file containing the full toc and nothing else (no
# content) thanks to the special template. The links are wrong, though,
# and we'll take care of that in the third step.
# The second step is to feed the "pre-toc" to pandoc and apply the book metadata
# and the default template. This way we obtain a fully styled HTML page.
# The third step consists of two substitutions to fix the links:
#   - since we prefixed ids with the chapter files basename while producing
#     the single html chapters, we have them like that in the pre-toc too; but then
#     it's very easy to do a replacement like "#basename@id" -> "basename.html#id"
#     and that gives us exactly the correct urls
#   - we don't need the prefixes anymore in the chapter files, so we just
#     remove them from all the html files
# This gives us both a working TOC and single chapter files with correctly
# formed hyperlinks. (One might argue that manipulating the chapter within this
# toc target is improper, but it works.)

# usage: make html/toc.html
$(HTMDIR)/toc.html : html_assets $(ALLHTM) $(SRCDIR)/metadata.yaml $(TPLDIR)/html/default.html $(TPLDIR)/html/toc-only.html
	pandoc \
	  --from html \
	  --to html5 \
	  --toc \
	  --toc-depth=6 \
	  --template=$(TPLDIR)/html/toc-only.html \
	  --output $(PREDIR)/pre-toc.html \
	  $(ALLHTM)
	pandoc \
	  --from markdown \
	  --to html5 \
	  --template=$(TPLDIR)/html/default.html \
	  --variable=pagetitle:'สารบัญ' \
	  --output $(HTMDIR)/toc.html \
	  $(SRCDIR)/metadata.yaml \
	  $(PREDIR)/pre-toc.html
	perl -S -pi -e 's/"#(.*?)@(.*?)"/"\1.html#\2"/g' $(HTMDIR)/toc.html
	perl -S -pi -e 's/"(.*?)@(.*?)"/"\2"/g' $(ALLHTM)

#==[ HTML COVER ]===============================================================

# This target generates the html cover. It is simply a rendering of the index
# template with the default styling and the book metadata applied to it.

# usage: make html/index.html
$(HTMDIR)/index.html : html_assets $(SRCDIR)/metadata.yaml $(TPLDIR)/html/default.html
	pandoc \
	  --from markdown \
	  --to html5 \
	  --template=$(TPLDIR)/html/default.html \
	  --variable=pagetitle:'ปก' \
	  --output $(HTMDIR)/index.html \
	  $(SRCDIR)/metadata.yaml \
	  $(TPLDIR)/html/index.html

#==[ HTML ASSETS ]==============================================================

# This targets gathers all operations necessary to trasfer static assets for
# for the html output to the output folder. This means just copying css, js,
# fonts and images in the correct folders.

# TODO: set prerequisites, if necessary
html_assets:
	mkdir -p $(HTMDIR)
	cp -r $(TPLDIR)/html/css $(HTMDIR)/
	cp -r $(TPLDIR)/html/js $(HTMDIR)/
	mkdir -p $(HTMDIR)/fonts/
	cp $(FNTDIR)/THSarabunNew* $(HTMDIR)/fonts/
	mkdir -p $(HTMDIR)/images/
	cp $(SRCDIR)/cover-image.png $(HTMDIR)/images/cover.png

#==[ EPUB ]=====================================================================

# This target is the single-step generation of the epub ebook format.
# It depends just on the preprocessed source, the book metadata and the css
# stylesheet ment for ebook readers. Some straightforward options for pandoc
# allow us to embed fonts, stylesheets and cover images without effort.

# usage: make ebooks/book.epub
$(EBKDIR)/book.epub: $(SRCDIR)/metadata.yaml $(TPLDIR)/epub/stylesheet.css $(ALLPRE)
	mkdir -p $(EBKDIR)
	pandoc \
	  --toc \
	  --toc-depth=2 \
	  --epub-embed-font=$(FNTDIR)/THSarabunNew.ttf \
	  --epub-embed-font=$(FNTDIR)/THSarabunNew-Bold.ttf \
	  --epub-embed-font=$(FNTDIR)/THSarabunNew-Italic.ttf \
	  --epub-embed-font=$(FNTDIR)/THSarabunNew-BoldItalic.ttf \
	  --epub-stylesheet=$(TPLDIR)/epub/stylesheet.css \
	  --epub-cover-image=$(SRCDIR)/cover-image.png \
	  -o $(EBKDIR)/book.epub \
	  $(SRCDIR)/metadata.yaml \
	  $(ALLPRE)


#==[ HIC SUNT LEONES ]==========================================================

# The next two targets are not yet properly tested.

# The first one converts EPUB -> MOBI
# We'll need to clean this up and test it, if needed, to use it in production.

# usage: make ebooks/book.mobi
$(EBKDIR)/book.mobi: $(EBKDIR)/book.epub
	./kindlegen $(EBKDIR)/book.epub -o book.mobi

# The second one generates dependencies graphs for makefile targets; I needed
# that to orient myself during development, but it has a lot of software
# dependencies and is of no use for the typesetting; you can safely ignore it.

# usage: make graph
graphs/%.svg: makefile
	mkdir -p $(GPHDIR)
	make -Bnd $* \
	| \
	 ./make2graph \
	| \
	dot \
	  -Grankdir=LR \
	  -Gsplines=ortho \
	  -Tsvg \
	  -o $(GPHDIR)/$*.svg

