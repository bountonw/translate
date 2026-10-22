# Extending the proofreading site

The site grows by adding files in five places. Each place has tests. Four have a first user; the place for annotators has none yet, and neither has the spanMark place of the page. The core code does not change when a new entry arrives, except where this file says so.

| To add | Add | First user |
|---|---|---|
| a language | an entry in web/languages.json and its font files in web/fonts/ | Thai |
| a book format | a module in parsers/ | parsers/sc_typst.py |
| a book | an entry in books.json | SC |
| a marker of words, such as Bible references | a module in parsers/annotators/ | none yet |
| a feature | a module in server/features/, and its page part in web/features/ | server/features/english.py and web/features/english.js |

README.md lists the commands and the API. This file says how each place works.

## Adding a language

web/languages.json holds one entry per language, keyed by its code. books.json names the code in a book's `language`, and the page puts it in the `lang` attribute of that book's text. The Thai entry:

    "th": {
      "name": "ไทย",
      "name_en": "Thai",
      "refuse": [{"range": "U+0E50-U+0E59", "why": "Thai digits"}],
      "font": {
        "family": "Sarabun",
        "fallback": ["Noto Sans Thai", "Leelawadee UI", "Thonburi", "sans-serif"],
        "files": [{"src": "fonts/Sarabun-Regular.ttf", "weight": 400, "style": "normal"}, ...],
        "license": "fonts/OFL.txt"
      }
    }

- `name` is the language's name in its own script; `name_en` in English.
- `refuse` lists the characters a book in this language may not hold, as ranges of code points. publish and the server refuse such a chapter. In what readers type, the digits among them become Western digits.
- `every_book.refuse`, at the top of the file, holds the project's ban on Thai and Lao digits. It applies to every book, whatever its language.
- `font` names the family, the fallback families, each font file with its weight and style, and the licence file. The page loads only the fonts of the languages it shows.

For Lao:

1. Copy the font files and their licence into web/fonts/.
2. Add an "lo" entry: the name in Lao script copied from a Lao file of the repository, `"refuse": [{"range": "U+0ED0-U+0ED9", "why": "Lao digits"}]`, and the font. A font with Lao letters only should give `"unicode_range": "U+0E80-0EFF"`, so that pages without Lao text never download it.
3. Set `"language": "lo"` in the book's books.json entry.
4. The interface stays Thai or English. A Lao interface needs an "lo" value for every string in web/ui-strings.json, a key lang_lo naming Lao in Lao script, and "lo" in UI_LANGS in web/core/words.js, which adds its button to the language switch.

python3 -m unittest checks that each font file named in the registry exists.

## Adding a book format

A format module in parsers/ reads one source format. It offers one function:

    def load_chapter(book, n, read):
        """book: the books.json entry, with "id" added; n: the chapter number;
        read(path): the file's text at the git ref, or None.
        Returns {"id", "n", "title_th", "title_en", "paragraphs", "sources"}:
        paragraphs is a list of {"a": "GC 17.2", "th": HTML, "fn": [HTML], "en": HTML},
        sources the repository paths read. Raises parsers.ParseError when the chapter cannot be used."""

The module only reads its format. parsers.load_chapter, which review.py calls, then runs the book's annotators and refuses a chapter whose HTML leaves the content model, whose text or English holds a character the registry refuses or an invisible one, or whose title, paragraphs or footnotes hold a marker `[[` or an editor's choice `((`. These checks are in parsers.check_chapter, so every format has them; a format module may check its whole file as well, as sc_typst.py does. `title_th` holds the chapter title in the book's own language, whatever that language is. The content model has no heading tag: a heading inside a paragraph's section, such as a `###` subheading of a GC chapter, is written as `<strong class="subhead">...</strong><br>` at the start of the paragraph's HTML, so that the export prints it on a line of its own; web/app.css gains a rule for `strong.subhead` with the first book that has one. The Lao GC chapters, for example, are Markdown files (lo/GC/03_public/GC01_lo.md), so GC needs a module such as parsers/gc_markdown.py with tests on small made-up inputs, as tests/test_parser.py has for SC.

## Adding a book

A book kept in a format that parsers/ already reads needs one entry in books.json. For a book with the id XX:

    "XX": {
      "title_en": "English title of the book",
      "title_th": "the title in the book's own language",
      "language": "th",
      "parser": "sc_typst",
      "annotators": [],
      "ref": "main",
      "stages": ["03_public", "02_edit", "01_raw"],
      "thai": "th/XX/{stage}/{name}_th.typ",
      "english": "th/XX/00_source/{name}_en.md",
      "names": {"0": "XX00_preface"}
    }

`title_th` is the book's title in its own language, whatever that language is; the chapter list shows it as the book's heading when a reader has more than one book, and shows `title_en` while it is empty. publish sends it with every chapter. `language` is a code of web/languages.json. `parser` names a module in parsers/, and `annotators` lists modules in parsers/annotators/, run in order. `thai` and `english` are paths in the repository; `{stage}` takes each of `stages` in turn, `{nn}` the two-digit chapter number, `{book}` the book id, and `{name}` the file name's stem: the book id and two digits (XX07), unless `names` gives another for that chapter number. `names` and `annotators` are optional. Chapter ids are the book id and two digits, as XX07. Then run `python3 review.py publish XX 01-05`.

## The content model

A published paragraph is `{"a", "th", "fn", "en"}`: the anchor, the text in the book's language, the footnotes, and the English source, each as HTML. server/content.py defines what that HTML may hold, and both parsers.load_chapter and the server check it:

- the tags em, strong, i, b, sup, sub, p, br and span, each with an optional `class` of lower-case words;
- a marked span, reserved for features to come: `<span data-kind="bible" data-value="John 3:16">...</span>`. `data-kind` is a lower-case word naming what is marked; `data-value` is optional, at most 200 characters, with no quote mark or angle bracket and an ampersand only as `&amp;`. A class may come first. The attributes stand in the order class, data-kind, data-value.

No parser writes a marked span yet. The export turns every paragraph into plain text, so marked spans never change the words Claude reads.

An annotator in parsers/annotators/ adds marked spans. It offers `annotate(paragraph, book)` and returns the paragraph with new HTML around the same words; parsers.load_chapter refuses an annotator that changes the words.

## Adding a feature

A feature is one module in server/features/. The server finds every module there whose name does not start with an underscore. A feature may not take the name of a core path: admin, health, me, chapter, comments, place, finished, chapters, readers, groups, features, export and processed (RESERVED in server/features/\_\_init\_\_.py). server/features/english.py is the first:

    NAME = "english"
    SETTINGS = {"on": {"type": "bool", "default": False, "help": "show the English source beside the translation"}}
    ROUTES = []
    MIGRATIONS = []

What a module declares:

- **NAME**: a lower-case word. Its settings are stored as `NAME.setting`, as `english.on`.
- **SETTINGS**: the settings a reader or a group can hold, with their type and default. The only type is bool. A reader gets a setting on when their own value or that of any of their groups that is switched on is on; with no value at all, the default. A setting of another kind, such as a Bible version, changes three core files, with their tests: server/features/\_\_init\_\_.py needs the new type (one of a list of values), a rule for combining a reader's value with the groups' values (the reader's own value first, then the groups' in order), and a way to clear a value (null); server/people.py needs to accept null; review.py needs values other than on and off in `feature` and `group feature`.
- **ROUTES**: `(method, sub, handler, auth)`. `sub` is a regular expression for the part of the path after the feature's prefix, and the registry builds the path itself, so no route can leave its prefix: auth "reader" gives /api/NAME/sub for readers who have the feature on (others get 404 not_found); "any_reader" gives the same path for every reader with a working link, for a route that must answer while the feature is off; "admin" gives /api/admin/NAME/sub with the admin token; None gives /api/NAME/sub open to anyone. `sub` must be a regular expression on its own and may not start with a slash. `handler(app, req, *groups)` returns `(status, payload)` as a core route does; `app.settings(req)` gives the reader's settings, and `req.conn` the database.
- **MIGRATIONS**: `(version, [SQL])` for the feature's own tables, named NAME_something. They run after the core migrations, in the same transaction, and the table feature_schema keeps the version each feature has reached. A feature never changes a core table.
- **me(ctx)**, optional: what GET /api/me carries under `features.NAME`. ctx has `conn`, `reader` and `settings` (this feature's, without the prefix). Without it, /api/me carries the feature's settings, as `"english": {"on": true}`.
- **enabled(settings)**, optional: whether the feature is on for a reader, from this feature's settings without the prefix. Without it, the feature is on when its setting `on` is true. The server uses it for the feature's reader routes; the page's feature() takes the same function.

An on/off setting needs no new command: `feature NAME english on` sets a setting for a reader, `feature --group G english on` for each member of a group, and `group feature G english on` for the group itself. `features` lists every feature with its settings. A feature that needs a command of its own, such as one that loads Bible verses or the glossary, or `review.py search reindex`, adds it to build_parser in review.py, with a test in tests/test_cli.py; a place where features add their commands is made with the first feature that needs one.

tests/test_features.py plugs a made-up feature with a route, a setting, two migrations and a me() hook into the server; a new feature's tests can follow it. The core tests check only their own entries, so a new feature or language breaks none of them.

### The page side

The page is a set of ES modules that the browser loads as they are, with no build step. web/index.html loads web/app.js, the entry point, a plain script that loads web/core/main.js and calls boot(); if that fails, as on a first visit without a connection, app.js shows the general error notice. index.html also names every module in a `<link rel="modulepreload">` line, so the browser fetches them all at once rather than one level of imports after another; web/sw.js reads the same lines to know which files to keep for offline use.

| Module | What it holds |
|---|---|
| core/main.js | the start: reads the link, loads the words, the languages and the chapter list, wires the browser's events, imports every core module, and loads each feature that index.html names with its own import() |
| core/state.js | S, what the page shows now; `store`, what the device keeps; on() and emit(), which carry news from net.js to the modules that draw |
| core/store.js | localStorage behind try/catch, and the names of the keys |
| core/words.js | t(), each key of ui-strings.json in the interface language; UI_LANGS, the interface languages |
| core/languages.js | web/languages.json: each language's lang code and font |
| core/net.js | the API calls, the outbox runner, and the chapter list, chapters and comment lists kept on the device |
| core/outbox.js | the outbox: every write waits there until the server confirms it |
| core/model.js | /api/me and a chapter in the page's shape, with the defaults for an older answer |
| core/refusals.js | why the server refused a comment, in the reader's words, and the check made when the reader taps Save |
| core/ext.js | the places where features plug in |
| core/dom.js | h(), which makes elements; bookHtml(), which rebuilds book text; the marked spans; the small buttons |
| core/screens.js | the router, the link, offline and loading screens, the list of unsaved comments, the note at the foot of the screen, the bar and the settings |
| core/home.js | the chapter list |
| core/chapter.js | an open chapter, the sections at its end, the "finished" box and the reader's place |
| core/para.js | a paragraph and its drawer |
| core/notes.js | the comment cards, the comment form, and the section of comments on paragraphs no longer in the chapter |
| features/english.js | the English feature: the first feature module |

outbox.js, model.js, refusals.js, store.js and ext.js hold no DOM, so tests/core_test.js runs them with node.

chapter.js, home.js, notes.js, para.js and screens.js import one another and are one unit: to follow an action, such as opening a chapter, read all five. None of them may run code when it loads, except registering an entry with ext.js, because such code could use a value of another of the five before that module has run.

#### A feature's page part

A feature's page part is one module, web/features/NAME.js, where NAME is the feature's NAME in server/features/. It calls `feature({name: "NAME"})` once, then adds entries to the places below. To load it:

1. add `<link rel="modulepreload" href="features/NAME.js">` to web/index.html, beside the other modules. boot() in web/core/main.js loads every module that index.html names under features/, each with its own import(), before the page starts; the same line makes the browser fetch the file at once and the service worker keep it for offline use. web/core/main.js and web/sw.js need no change;
2. add its words to web/ui-strings.json, each with "en" and "th".

tests/test_web.py fails until the first is done, and until every key the module uses with t() is in ui-strings.json.

The page reads `features` from GET /api/me. A feature is on when `features.NAME.on` is true; a feature whose settings are not a single switch passes `enabled(settings)` to feature(), as a Bible feature would with `s => !!s.version`. A feature missing from /api/me, or one the page does not know, is off. An entry of a place is used only while its feature is on; an entry without `feature` belongs to the core.

#### The places

Each entry is an object with a `name`, an `order` (entries are used in rising order) and a `feature`. `render(ctx)` returns an element, or null to show nothing. A fault in a feature's function is logged and the entry is left out, and a feature module that fails as it loads is logged and left out as a whole; neither stops the page.

| Place | Where it shows | ctx | First user |
|---|---|---|---|
| `drawerPanel` | a panel in a paragraph's drawer, above the reader's comments. `hint` names a key of ui-strings.json for the line under a chapter title that says what a tap shows | `p` (the paragraph: `a`, `th`, `fn`, `en`), `art` (its element), `chapter`, `me`, `book`, `lang` | English: the paragraph's English, and the hint hint_english |
| `spanMark` | a marked span in the book text, `<span data-kind="bible" data-value="John 3:16">`. `kind` is the data-kind it handles; `decorate(span, ctx)` changes the span once it is drawn; `tap(span, ctx)` runs when the reader taps it and returns true to keep the drawer from opening. A tap inside an open drawer, as on a span of the English panel, does not reach `tap` yet (web/core/para.js) | as for drawerPanel | none yet: a marked span shows its words and does nothing |
| `chapterSection` | a section at the end of a chapter, before the "finished" box. With `refresh: true` it is drawn again whenever the reader's comments change | `chapter`, `comments` (the reader's comments on the chapter, with their state), `me`, `book` | the core: comments on paragraphs no longer in the chapter |
| `settingsItem` | an item beside the language switch at the top of the chapter list | `me` (null on the link and offline screens, so only core items show there), `screen` | the core: the language switch |
| `titleLine` | a line under a chapter's title, in the chapter list and at the head of the chapter | `chapter`, `me`, `where` ("list" or "head") | English: the English title |

A feature that changes the chapter text the server sends passes `variant` to feature(), a short word such as English's "en". A chapter kept on the device remembers the variants it was fetched with, and the page fetches it again when a feature with a variant is switched on or off. The server's side of a variant is written for English only, in chapter() of server/app.py, which picks the answer and the ETag; a second feature that changes the chapter text changes that function, with its tests.

#### Rules for page code

- The page runs on Safari for iOS 12 and later: no `?.`, `??`, class fields or top-level await. ES modules and `import()` are fine.
- index.html holds no inline script or style, and nothing loads from another host. Styles a feature adds go into web/app.css. A rule that depends on data, such as a font, is added through the CSS object model, as core/languages.js does.
- Talk to the server through `api()` in core/net.js; send writes through the outbox, so they survive a lost connection. requestFor() in core/outbox.js knows only comments, places and finished marks; a feature that writes adds its own kind of entry there, with a test in tests/core_test.js.
- Keep a reader's data on the device under keys that start with `rv.f:NAME:`; a new link clears them, as it clears the kept chapters.
- Every word comes from ui-strings.json through t(). New Thai uses กรุณา for "please" and no ค่ะ or ครับ, and names ระบบ as the subject when the site itself fails.
- Fonts come from web/languages.json: a new language needs no page code. A new interface language needs its code in UI_LANGS in core/words.js, a key lang_CODE naming it in itself, and its value in every string of ui-strings.json.

#### A sketch: Bible references as links

The planned `bible` feature below would mark references through the annotator `bible_refs` and add a setting `bible.version`, which needs the core changes for a setting of another kind (above). Two changes to the page come with it. First, web/core/para.js calls tapMark for a marked span inside the drawer too, since a reference in the English panel sits there; today a tap inside the drawer returns before tapMark. Second, the tapped span goes into the drawerPanel context, as `ctx.span`, so that the tap opens the drawer and the Bible panel shows the verse. Its page part would then be one module:

    import { feature, spanMark, drawerPanel } from "../core/ext.js";
    import { api } from "../core/net.js";
    import { h } from "../core/dom.js";
    feature({ name: "bible", enabled: s => !!s.version });
    spanMark({
      name: "bible", feature: "bible", kind: "bible",
      decorate(span) { span.classList.add("ref"); span.setAttribute("role", "link"); span.tabIndex = 0; },
      tap() { return false; },   // the drawer opens, with the tapped span in ctx.span
    });
    drawerPanel({
      name: "bible", feature: "bible", order: 20,
      render(ctx) {
        if (!ctx.span) return null;
        const box = h("section", { class: "bible-block" });
        const version = ctx.me.features.bible.version;
        api("GET", "api/bible/" + encodeURIComponent(version) + "/" + encodeURIComponent(ctx.span.dataset.value))
          .then(r => { if (r.status === 200 && r.data) box.textContent = r.data.text; });
        return box;
      },
    });

A glossary feature is the same shape with `kind: "glossary"`, and may add a drawerPanel listing the terms of the paragraph. A search feature needs a screen of its own, which none of the places above gives; it adds a place for screens to core/ext.js and core/screens.js, with its tests, when it is built.

## The five features planned

**More languages.** Lao: a registry entry and a Lao font (above), a format module for the GC Markdown chapters, and Lao strings for the interface if Lao readers want a Lao interface.

**More book formats.** One module in parsers/ for each, such as gc_markdown.py for the Lao GC chapters or a module for a book kept in another layout. Nothing else changes.

**Bible references as links, with a Bible version per reader.** An annotator `bible_refs` marks each reference as `<span data-kind="bible" data-value="John 3:16">`. A feature `bible` adds a setting `bible.version` (a new setting type: one of a list), so each reader or group chooses a version; a table `bible_verse` filled by an admin route from the translator's Bible files; and a reader route `GET /api/bible/<version>/<reference>` (the sub-pattern `([A-Za-z0-9]+)/(.+)`). The page shows each marked span as a link that opens the verse.

**Glossary and dictionary look-ups.** A feature `glossary` with a table `glossary_term` filled by an admin route from the project's glossary file (th/assets/translation_profile/thai-glossary.txt), a reader route `GET /api/glossary/lookup?term=` (the sub-pattern `lookup`), and a bool setting `glossary.on`. An annotator `glossary_terms` may mark known terms with `data-kind="glossary"`. A dictionary is the same shape with its own table and route.

**How a word was translated in other books, with fuzzy matching.** A feature `search` keeps its index in an SQLite FTS5 table of its own, made by its migration: `CREATE VIRTUAL TABLE search_para USING fts5(book, ch, a, th, en, tokenize='trigram')`. The trigram tokenizer suits Thai and Lao, written without spaces between words, but it finds only exact runs of three or more characters: a phrase query for a word with one vowel changed finds nothing. A near match comes from the query's own trigrams joined with OR and ranked by bm25, which put the paragraph with the right word first in a trial on SC01-08; a word of one or two characters needs LIKE on the table, since it has no trigram. The other books are published like any book but granted to nobody, so they are in the chapter table without reaching readers. The index is rebuilt from the chapter table, with server/content.py's plain() taking the HTML out, by an admin route that `review.py search reindex` would call; keeping it current at every publish needs one new hook in the registry, `on_publish`, added with that feature. A route `GET /api/search/?q=` (the sub-pattern empty) answers the matching paragraphs with their Thai and English, ranked by FTS5's bm25, from the books the reader may search.
