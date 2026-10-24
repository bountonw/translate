# Extending the proofreading site

The site grows by adding files in five places. Each place has tests. Four have a first user; the place for annotators has none yet. The core code does not change when a new entry arrives, except where this file says so.

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
5. The admin page is in English. A Lao admin page needs an "lo" value for every string in admin/strings.json and "lo" first in LANGS in admin/words.js; a value left empty shows the English.

python3 -m unittest checks that each font file named in the registry exists.

## Adding a book format

A format module in parsers/ reads one source format. It offers one function:

    def load_chapter(book, n, read):
        """book: the books.json entry, with "id" added; n: the chapter number;
        read(path): the file's text at the git ref, or None.
        Returns {"id", "n", "title", "title_en", "paragraphs", "sources"}:
        paragraphs is a list of {"a": "GC 17.2", "text": HTML, "fn": [HTML], "en": HTML},
        sources the repository paths read. Raises parsers.ParseError when the chapter cannot be used."""

The module only reads its format. parsers.load_chapter, which review.py calls, then runs the book's annotators and refuses a chapter whose HTML leaves the content model, whose text or English holds a character the registry refuses or an invisible one, or whose title, paragraphs or footnotes hold a marker `[[` or an editor's choice `((`. These checks are in parsers.check_chapter, so every format has them; a format module may check its whole file as well, as sc_typst.py does. `title` and each paragraph's `text` hold the book's own language, whatever that language is (books.json "language"); the fields that hold the translation's text never name a language, and `_en` and `en` hold the English. The content model has no heading tag: a heading inside a paragraph's section, such as a `###` subheading of a GC chapter, is written as `<strong class="subhead">...</strong><br>` at the start of the paragraph's HTML, so that the export prints it on a line of its own; web/app.css gains a rule for `strong.subhead` with the first book that has one. The Lao GC chapters, for example, are Markdown files (lo/GC/03_public/GC01_lo.md), so GC needs a module such as parsers/gc_markdown.py with tests on small made-up inputs, as tests/test_parser.py has for SC.

## Adding a book

A book kept in a format that parsers/ already reads needs one entry in books.json. For a book with the id XX:

    "XX": {
      "title_en": "English title of the book",
      "title": "the title in the book's own language",
      "language": "th",
      "parser": "sc_typst",
      "annotators": [],
      "ref": "main",
      "stages": ["03_public", "02_edit", "01_raw"],
      "source": "th/XX/{stage}/{name}_th.typ",
      "english": "th/XX/00_source/{name}_en.md",
      "names": {"0": "XX00_preface"},
      "notes": "th/XX/04_assets/notes/XX_notes.txt",
      "align": "assets/review/align/XX/{name}.json"
    }

`title` is the book's title in its own language, whatever that language is; the chapter list shows it as the book's heading when a reader has more than one book, and shows `title_en` while it is empty. publish sends it with every chapter. `language` is a code of web/languages.json. `parser` names a module in parsers/, and `annotators` lists modules in parsers/annotators/, run in order. `source` (the chapter's file in the book's language) and `english` are paths in the repository; `{stage}` takes each of `stages` in turn, `{nn}` the two-digit chapter number, `{book}` the book id, and `{name}` the file name's stem: the book id and two digits (XX07), unless `names` gives another for that chapter number. `names` and `annotators` are optional. `notes` is the book's notes file, whose lines `{XX 13.1} | English words | span of the book's text | reason` review.py triage matches against reviewers' comments. `align` is where the book's sentence alignment files lie in the repository ("Sentence alignment" below). Both are optional. Chapter ids are the book id and two digits, as XX07. Then run `python3 review.py publish XX 01-05`.

### Paragraph tags

Every paragraph is named by the tag written before it in the book's source, as `// {XX 9.1}` in a Typst chapter or `## {XX 9.1}` in a Markdown one. A tag is a label, never a position: the site, the export, the markers and the reviewers' comments name a paragraph by its tag, so a paragraph keeps its name when paragraphs before it are added, merged or removed, and a comment stays on its paragraph. Nothing counts paragraphs to make a name. A new book's source therefore gets its tags written into it once, before its first publish, and keeps them from then on. publish stops with "The book XX has no paragraph tags" when a chapter has text but no tag, and sends nothing.

## The content model

A published paragraph is `{"a", "text", "fn", "en"}`: the anchor, the text in the book's language, the footnotes, and the English source, each as HTML. It may also carry `al`, its sentence pairs ("Sentence alignment" below). server/content.py defines what that HTML may hold, and both parsers.load_chapter and the server check it:

- the tags em, strong, i, b, sup, sub, p, br and span, each with an optional `class` of lower-case words;
- a marked span, reserved for features to come: `<span data-kind="bible" data-value="John 3:16">...</span>`. `data-kind` is a lower-case word naming what is marked; `data-value` is optional, at most 200 characters, with no quote mark or angle bracket and an ampersand only as `&amp;`. A class may come first. The attributes stand in the order class, data-kind, data-value.

No parser writes a marked span yet. The export turns every paragraph into plain text, so marked spans never change the words Claude reads.

An annotator in parsers/annotators/ adds marked spans. It offers `annotate(paragraph, book)` and returns the paragraph with new HTML around the same words; parsers.load_chapter refuses an annotator that changes the words.

## Sentence alignment

A book's alignment files say which span of each paragraph's text renders which English sentences, so that the page can show a sentence's English. They are optional, one per chapter, at the repository path that books.json gives in `align` (`{name}`, `{nn}` and `{book}` as for the other paths): for SC, assets/review/align/SC/SC01.json. publish reads the file at the same ref as the chapter, and sends only what still fits the text.

    {
      "format": 2,
      "sentences": 1,
      "book": "SC",
      "chapter": "SC01",
      "paragraphs": {
        "SC 9.1": {
          "text_sha256": "<SHA-256 of the paragraph's plain text>",
          "en_sha256": "<SHA-256 of the paragraph's plain English>",
          "pairs": [{"text": [0, 57], "en": [1]}, {"text": [58, 140], "en": [2, 3]}]
        }
      }
    }

- The plain text of a paragraph is align_text() of server/content.py: its HTML with the footnote numbers (`<sup class="fn">`) and every tag taken out and the entities decoded, nothing else; `<br>` adds no line break and no space is trimmed. It is the text the page shows, in the same order. The hashes are SHA-256 in hexadecimal of the UTF-8 plain text, of `text` and of `en`.
- A pair's `text` is a range `[start, end)` of the plain text, counted in Unicode code points, `end` not included. Its `en` lists English sentence numbers, from 1.
- Format 1, the files made before the fields got neutral names, names `text` `th` and `text_sha256` `th_sha256`. publish reads both formats; align-packet writes format 2.
- The English sentences are those of sentences() in parsers/align.py, rules 1 (`"sentences": 1`): a sentence ends at . ! or ? when a space and a capital, a digit or an opening quote follow, never after an abbreviation such as Mr. or e.g. or an initial; it always ends where a `<p>` ends, and at the end of a verse line (`<br>`) only after . ! or ?. A file made under other rules is not used.
- publish drops a paragraph whose hashes no longer match its text, or whose pairs do not fit it, and says how many it dropped and which; a paragraph of the file that is no longer in the chapter is not counted, since nobody reads it; the rest go to the server as `al`. The server stores each pair with the English as ranges, `{"text": [start, end], "en": [[start, end], ...]}`, in the same plain text, and the chapter answer carries `al` to readers who see the English.
- `review.py align-packet SC 01` writes what an agent needs to make the file: for each paragraph the plain text (`text`), its chunks between spaces with their ranges (`text_chunks`), the numbered English sentences, and a template of the file with the hashes filled in. The agent fills the pairs and writes the template to the path the packet names.
- On the page, web/features/sentences.js wraps each range in spans: a reader with the English on taps a Thai sentence, and the paragraph's panel opens on the English with that sentence and its English lit; Previous sentence and Next sentence step through the pairs. A paragraph without pairs opens the panel on its whole English.

## Adding a feature

A feature is one module in server/features/. The server finds every module there whose name does not start with an underscore. A feature may not take the name of a core path: admin, health, me, chapter, comments, place, finished, opened, earlier, chapters, readers, groups, features, export, processed, replies, devices, rounds, auth, sessions, identities, requests, general and dev (RESERVED in server/features/\_\_init\_\_.py). server/features/english.py is the first:

    NAME = "english"
    SETTINGS = {"on": {"type": "bool", "default": False, "help": "show the English source beside the translation"}}
    ROUTES = []
    MIGRATIONS = []

What a module declares:

- **NAME**: a lower-case word. Its settings are stored as `NAME.setting`, as `english.on`.
- **SETTINGS**: the settings a reader or a group can hold, with their type and default. The only type is bool. A reader gets a setting on when their own value or that of any of their groups that is switched on is on; with no value at all, the default. A setting of another kind, such as a Bible version, changes three core files, with their tests: server/features/\_\_init\_\_.py needs the new type (one of a list of values), a rule for combining a reader's value with the groups' values (the reader's own value first, then the groups' in order), and a way to clear a value (null); server/people.py needs to accept null; review.py needs values other than on and off in `feature` and `group feature`.
- **ROUTES**: `(method, sub, handler, auth)`. `sub` is a regular expression for the part of the path after the feature's prefix, and the registry builds the path itself, so no route can leave its prefix: auth "reader" gives /api/NAME/sub for readers who have the feature on (others get 404 not_found), whether they are signed in with the session cookie or send a link that signs in by itself (server/auth.py, reader_auth); "any_reader" gives the same path for every reader signed in, for a route that must answer while the feature is off; "admin" gives /api/admin/NAME/sub with the admin token; None gives /api/NAME/sub open to anyone. `sub` must be a regular expression on its own and may not start with a slash. `handler(app, req, *groups)` returns `(status, payload)` as a core route does; `app.settings(req)` gives the reader's settings, and `req.conn` the database.
- **MIGRATIONS**: `(version, [SQL])` for the feature's own tables, named NAME_something. They run after the core migrations, in the same transaction, and the table feature_schema keeps the version each feature has reached. A feature never changes a core table.
- **me(ctx)**, optional: what GET /api/me carries under `features.NAME`. ctx has `conn`, `reader` and `settings` (this feature's, without the prefix). Without it, /api/me carries the feature's settings, as `"english": {"on": true}`.
- **enabled(settings)**, optional: whether the feature is on for a reader, from this feature's settings without the prefix. Without it, the feature is on when its setting `on` is true. The server uses it for the feature's reader routes; the page's feature() takes the same function.

An on/off setting needs no new command: `feature NAME [NAME ...] english on` sets a setting for readers, and `group feature G english on` for a group itself. `features` lists every feature with its settings. A feature that needs a command of its own, such as one that loads Bible verses or the glossary, or `review.py search reindex`, adds it to build_parser in review.py, with a test in tests/test_cli.py; a place where features add their commands is made with the first feature that needs one. The admin page lists every on/off setting from GET /local/features, so a new setting needs no change there; a feature's own command also needs a local route in review_admin.py (COMMANDS, which review_admin.routes() lists), an entry in ROUTES of admin/api.js, and a control for the command and each of its options in the admin page's section it belongs to, with the control's words in admin/strings.json; tests/test_admin_page.py fails until its CONTRACT lists the route, its OPTIONS list the options, and the page calls the route and sends each option.

tests/test_features.py plugs a made-up feature with a route, a setting, two migrations and a me() hook into the server; a new feature's tests can follow it. The core tests check only their own entries, so a new feature or language breaks none of them.

### The page side

The page is a set of ES modules that the browser loads as they are, with no build step. web/index.html loads web/app.js, the entry point, a plain script that loads web/core/main.js and calls boot(); if that fails, as on a first visit without a connection, app.js shows the general error notice. index.html also names every module in a `<link rel="modulepreload">` line, so the browser fetches them all at once rather than one level of imports after another; web/sw.js reads the same lines to know which files to keep for offline use.

| Module | What it holds |
|---|---|
| core/main.js | the start: reads the address (#k= a personal link, #join= a general link, #auth= the result of a sign-in with LINE), loads the words, the languages and the chapter list, wires the browser's events, imports every core module, and loads each feature that index.html names with its own import(); signin.js decides the first screen |
| core/state.js | S, what the page shows now, with S.mode (session, link or null), S.reader (the number of the reader signed in now), S.deviceWaiting while the link waits for the translator's approval of this device and S.deviceNumber, the device's number in the translator's lists; `store`, what the device keeps; on() and emit(), which carry news from net.js to the modules that draw |
| core/store.js | localStorage behind try/catch, with `blocked` when the browser refuses it; the names of the keys, the tag of a link (linkTag), the tag of a reader (ownerTag) and the drafts kept per reader (draftKey, draftMoves) |
| core/auth.js | the plain rules of signing in: what each sign-in result and each 401 shows (afterSignIn, afterRefusal), the line for a refusal of a start or a code, the checks of an address and of the six digits, and whether the hint on adding the site to the Home Screen shows |
| core/signin.js | the screens before a reader is signed in: the welcome screen of a personal link, the sign-in screen, the request screens of a general link, the email form with its code, the stopped and blocked-storage screens, "Enter as <reader>" on the dev server; the start of a LINE sign-in and the way back from it; session mode and link mode |
| core/account.js | "Your devices" (#account), an entry of the settingsItem place for a reader signed in: the browsers signed in, each with Sign out; the ways to sign in, with Add LINE and Add an email address; Sign out on this browser |
| core/words.js | t(), each key of ui-strings.json in the interface language; UI_LANGS, the interface languages |
| core/languages.js | web/languages.json: each language's lang code and font |
| core/net.js | the API calls, each with X-Review-Page: 1 and the session cookie, or in link mode with the link's code and the device key, kept in a variable once read or made; the wait for the translator's approval of a device, with its number; the outbox runner, which sends only the ops of the reader signed in now, and takes over the lock rv-outbox from a page frozen with it; the reader signed in now (who, adoptReader), the reader number of each link, and the move of a reader's waiting comments and drafts from the reader's links to the reader's number; and the chapter list, chapters and comment lists kept on the device, with what a new chapter list makes stale, and the chapter list asked for again after a refusal it explains |
| core/outbox.js | the outbox: every write waits there, under the number of the reader who wrote it, until the server confirms it |
| core/model.js | /api/me and a chapter in the page's shape, with the defaults for an older answer and for a chapter kept by an older page; the grouping of "My earlier comments" |
| core/refusals.js | why the server refused a comment, in the reader's words; the check made when the reader taps Save; how long until the daily limit resets |
| core/ext.js | the places where features plug in |
| core/dom.js | h(), which makes elements; bookHtml(), which rebuilds book text; the marked spans; decorateText(), which runs the bookText place over book text once it is drawn; the dots of "Show spaces"; the reading text of book text (the text without the footnote numbers, as quotes.js counts it), the letter under a tap (tappedOffset) and the spans wrapped around ranges of it; the small buttons |
| core/screens.js | the router (#BOOK/CH for a chapter, #earlier for "My earlier comments", #account for "Your devices"); the link, offline, loading and device screens; the list of unsaved comments; the note at the foot of the screen; the bar with its "Show spaces" button and A− and A+, the text size kept on the device; the settings |
| core/home.js | the chapter list, with "Updated <date>" on the row of a changed chapter, the button to "My earlier comments", and under the list the hint on adding the site to the Home Screen |
| core/earlier.js | "My earlier comments": the reader's comments of earlier review rounds, read-only |
| core/chapter.js | an open chapter: its head with the line of updates.js, the sections at its end, the "finished" box and the reader's place |
| core/para.js | a paragraph: its text, footnotes and, side by side on a wide screen, its English; its taps, which go to the panel or, while the reader picks words, to the picker; the reader's selection, which fills the quote box at once and, once it rests, opens the comment box; the soft and deeper backgrounds of quoted words and the mark of the words being quoted; the soft background of the paragraph opened last |
| core/panel.js | the paragraph's panel: a sheet from the bottom, or a column at the right on a screen wider than tall and at least 640 pixels wide; its two faces, the English (the lead section) with the sections under it, and the comment box with the reader's comments; its heights, the drag of its bar and its head, the sheet made whole while a text box has focus, and the text moved only to uncover the words it keeps in view (keepLit for A− and A+); the line "Saving…" and "Saved" at the top of the comment box; Pick words, also in another paragraph; the keyboard's way into the panel and back; the layout classes of html (panel-side, wide), kept while the reader types, and the English beside the paragraphs |
| core/quotes.js | plain rules of the reading text: how ranges cut its text nodes, its words (Intl.Segmenter, or runs between spaces), the letter under a tap from the boxes of the letters around the caret, the quoted words between two picked words, where a comment's quote stands (`at`), the backgrounds of quoted words, the stops of Previous and Next sentence, and the English ranges of the sentence pairs, a range two pairs share naming both |
| core/notes.js | the comment cards, with the line that a comment's paragraph changed, the translator's reply and the time until the daily limit resets; the read-only cards of earlier rounds; the comment form, with Pick words beside the quote box and the quote's place; and the section of comments on paragraphs no longer in the chapter |
| core/changes.js | what changed in a chapter since the reader last opened it: the record kept on the device, the marks, and when to send the version opened |
| core/updates.js | a new version of a chapter on the screen: the line at the head of the chapter, the marks on the paragraphs, "Show the earlier wording" (a core entry of the panelSection place) and PUT /api/opened |
| features/english.js | the English feature, the first feature module: the English face of the panel, the English beside each paragraph and its setting, and the English title |
| features/sentences.js | a Thai sentence and its English: entries of the english feature in the bookText, spanMark and panelSection places, with Previous sentence and Next sentence |

outbox.js, model.js, refusals.js, store.js, ext.js, changes.js, auth.js and quotes.js hold no DOM, so tests/core_test.js runs them with node, with the entries of features/sentences.js. It also runs net.js with a stand-in for fetch: the headers of session mode and link mode, the device key, the wait for approval, a 401 that pauses the outbox, and the waiting comments and drafts of a reader's links becoming the reader's.

chapter.js, earlier.js, home.js, notes.js, para.js, panel.js, screens.js, signin.js and account.js import one another and are one unit: to follow an action, such as opening a chapter, opening a paragraph's panel or signing in, read all nine. None of them may run code when it loads, except registering an entry with ext.js, because such code could use a value of another of the nine before that module has run. updates.js draws for chapter.js and panel.js but imports none of the nine, so it stands outside the unit; it too runs nothing when it loads but its entry in the panelSection place.

The core keeps more things on the device. `rv.opened:BOOK/CH` is the record of changes.js for one chapter, which a sign-in as another reader clears with the kept chapters. `rv.spaces` is the "Show spaces" choice, `rv.size` the step of A− and A+, and `rv.side` the choice of the English beside each paragraph; they stay with the device, as the interface language does. `rv.device` is the device's own random key, which every request in link mode sends in X-Review-Device; a new link keeps it, so the site counts one device. `rv.links` maps the tag of each link opened on the device (store.js, linkTag: eight hexadecimal digits, never the code) to the reader number /api/me or the link's claim gave for it. `rv.reader` is the number of the reader signed in last, whose chapter list the device keeps; `rv.code` is the link of link mode; `rv.flow` is the screen of signing in the reader is on ({kind, code, at}), so that a sign-in with LINE comes back to it; `rv.homeHint` is true once the reader hid the hint on adding the site to the Home Screen. A draft is kept per reader, as `rv.draft:R7:BOOK/CH/A`, and only while it holds words the reader wrote (store.js, draftHolds): words a selection or a pick put in the quote box alone are no draft. The page keeps nothing that signs in: the session cookie is HttpOnly, and the page never sees it.

What a reader writes is kept apart per reader and never deleted unsent unless the reader asks. A delete the site refuses, as in a chapter closed meanwhile, stays in the outbox with the comment's words, and the page says that the comment was not deleted and the translator still receives it. Each op of the outbox names the number of its reader (`reader`), and each draft carries its reader's tag. The page shows, counts and sends only those of the reader signed in now, with the session cookie or, in link mode, with the link's code. An op written by a page of round 3b names its link (`code`), and so does one written in link mode before the device knew the link's number; once the device learns that link's reader number, the op and the link's drafts become that reader's (outbox.js, renumber). Those of another reader number wait untouched until that reader signs in on this browser again. An op whose link the device never tied to a number stays too, and the list of comments not saved shows its words with Copy. The match is by number, never by name, because two readers may share a name. A sign-in as another reader clears what the device keeps for reading (the chapter list, the chapters, the comment lists, the records of changes and the `rv.f:` keys of features), never what any reader wrote.

Every 401 of a reader route pauses the outbox and shows the screen of signing in that its code calls for (auth.js, afterRefusal): the sign-in screen, with a line for signed_out and link_used; the welcome screen of the kept link for sign_in_required; the stopped screen; the link screen for bad_code. A 403 bad_page, a request the site took for another site's, shows the general error notice; the op waits and goes again later, as after a 429, and is never refused for it.

When a request answers 403 device_waiting, the link works on other devices and waits for the translator's approval on this one. The page shows the device screen in place of the chapter list, with the device's number from the answer, sends nothing, keeps everything, and asks /api/me again every two minutes, when the device comes back online and when the reader taps "Check again"; an answer of /api/me means the device was let in.

#### A feature's page part

A feature's page part is one module, web/features/NAME.js, where NAME is the feature's NAME in server/features/. It calls `feature({name: "NAME"})` once, then adds entries to the places below. To load it:

1. add `<link rel="modulepreload" href="features/NAME.js">` to web/index.html, beside the other modules. boot() in web/core/main.js loads every module that index.html names under features/, each with its own import(), before the page starts; the same line makes the browser fetch the file at once and the service worker keep it for offline use. web/core/main.js and web/sw.js need no change;
2. add its words to web/ui-strings.json, each with "en" and "th".

tests/test_web.py fails until the first is done, and until every key the module uses with t() is in ui-strings.json.

A module may also add entries to a feature that another module declares: it names that feature in each entry's `feature` and does not call feature() itself. web/features/sentences.js adds to english in this way, because the server sends sentence pairs only with the English; its entries are used exactly while English is on, and it is loaded by its own modulepreload line like any feature module.

The page reads `features` from GET /api/me. A feature is on when `features.NAME.on` is true; a feature whose settings are not a single switch passes `enabled(settings)` to feature(), as a Bible feature would with `s => !!s.version`. A feature missing from /api/me, or one the page does not know, is off. An entry of a place is used only while its feature is on; an entry without `feature` belongs to the core.

#### The places

Each entry is an object with a `name`, an `order` (entries are used in rising order) and a `feature`. `render(ctx)` returns an element, or null to show nothing. A fault in a feature's function is logged and the entry is left out, and a feature module that fails as it loads is logged and left out as a whole; neither stops the page.

| Place | Where it shows | ctx | First user |
|---|---|---|---|
| `panelSection` | a section of a paragraph's panel (core/panel.js). The entry with `lead: true` leads the panel's first face, whose button says the key `label`; every other section follows it on that face in rising order, or stands under the comment form when no lead section draws anything, as for a reader with English off. With `beside: true` in ctx, the lead section is drawn beside the paragraph instead, when the reader shows it side by side on a wide screen, and the panel then has the comment box alone. `hint` names a key of ui-strings.json for the line under a chapter title that says what a tap shows | `p` (the paragraph: `a`, `text`, `fn`, `en`, and `al` when it has sentence pairs, `[{text: [start, end], en: [[start, end], ...]}]`), `art` (its element), `chapter`, `me`, `book`, `lang`, `span` (the marked span the reader tapped, or null), `show(a, span)` (shows paragraph a in the panel with span lit, as Next sentence does), `beside`, `face` ("en" on the lead's face, "note" under the comment form) | English: the lead, the paragraph's English (order 10, label lang_en), and the hint hint_english. Sentences: Previous and Next sentence (order 15). The core: "Show the earlier wording" (updates.js, order 20) |
| `spanMark` | a marked span in the book text, `<span data-kind="bible" data-value="John 3:16">`, whether the server sent it or a bookText entry made it. `kind` is the data-kind it handles; `decorate(span, ctx)` changes a span the server sent once it is drawn; `tap(span, ctx)` runs when the reader taps it and returns true to keep the panel from opening or closing; when it returns false, the panel opens on its first face with the span in ctx.span. A tap on a span that is lit (class `hl`) while the panel shows its paragraph's first face closes the panel instead. A section that lights what belongs to the tapped span gives those elements the class `hl`; the panel scrolls its face to the first of them, and the text moves only when the panel would cover the lit words, then only enough to show them. A tap in the panel's own text, as on a span of its English, does not reach `tap` yet (web/core/panel.js) | as for panelSection | sentences: a tap on a Thai sentence (kind "sentence") lights it, and its English in the panel or beside the paragraph |
| `bookText` | a change to book text once it is drawn, such as spans around some of its words; `decorate(el, ctx)` must leave the words as they are. The core runs it over a paragraph's text and footnotes; a panel runs it over its own text by calling decorateText() of core/dom.js, as English does. Every element that holds the book's own text has the class `bt`, and "Show spaces" puts its dots on those after the entries have run | as for panelSection, and `where`: "para", "fn", "en" (the English in the panel), "side" (the English beside the paragraph) or "earlier" (the earlier wording) | sentences: the spans of the Thai and English sentences |
| `chapterSection` | a section at the end of a chapter, before the "finished" box. With `refresh: true` it is drawn again whenever the reader's comments change | `chapter`, `comments` (the reader's comments on the chapter, with their state), `me`, `book` | the core: comments on paragraphs no longer in the chapter |
| `settingsItem` | an item beside the language switch at the top of the chapter list | `me` (null on the link and offline screens, so only core items show there), `screen` | the core: the language switch |
| `titleLine` | a line under a chapter's title, in the chapter list and at the head of the chapter | `chapter`, `me`, `where` ("list" or "head") | English: the English title |

A feature that changes the chapter text the server sends passes `variant` to feature(), a short word such as English's "en". A chapter kept on the device remembers the variants it was fetched with, and the page fetches it again when a feature with a variant is switched on or off. The server's side of a variant is written for English only, in chapter() of server/app.py, which picks the answer and the ETag; a second feature that changes the chapter text changes that function, with its tests.

#### Rules for page code

- The page runs on Safari for iOS 12 and later: no `?.`, `??`, class fields or top-level await. ES modules and `import()` are fine.
- index.html holds no inline script or style, and nothing loads from another host. Styles a feature adds go into web/app.css. A rule that depends on data, such as a font, is added through the CSS object model, as core/languages.js does.
- Talk to the server through `api()` in core/net.js, which adds X-Review-Page: 1 and sends the session cookie, or in link mode the link's code and the device key; a request in link mode without the device key is refused with 400 no_device. A feature's answer of 401 or of 403 device_waiting goes to authFailed(r.data.error) or deviceWaiting(r.data) of net.js, as the core's do. Send writes through the outbox, with the reader of net.js's who(), so they survive a lost connection and stay with the reader who made them. requestFor() in core/outbox.js knows only comments, places, finished marks and the versions of chapters opened; a feature that writes adds its own kind of entry there, with a test in tests/core_test.js.
- Keep a reader's data on the device under keys that start with `rv.f:NAME:`; a sign-in as another reader clears them, as it clears the kept chapters.
- Every word comes from ui-strings.json through t(). New Thai uses กรุณา for "please" and no ค่ะ or ครับ, and names ระบบ as the subject when the site itself fails.
- Fonts come from web/languages.json: a new language needs no page code. A new interface language needs its code in UI_LANGS in core/words.js, a key lang_CODE naming it in itself, and its value in every string of ui-strings.json.

#### A sketch: Bible references as links

The planned `bible` feature below would mark references through the annotator `bible_refs` and add a setting `bible.version`, which needs the core changes for a setting of another kind (above). One change to the page comes with it: web/core/panel.js passes a tap on a marked span in the panel's own text to tapMark, since a reference in the English sits there; today the panel's text takes no taps. The tapped span already reaches the panelSection context as `ctx.span` (features/sentences.js uses it), so the tap opens the panel and the Bible section shows the verse. Its page part would then be one module:

    import { feature, spanMark, panelSection } from "../core/ext.js";
    import { api } from "../core/net.js";
    import { h } from "../core/dom.js";
    feature({ name: "bible", enabled: s => !!s.version });
    spanMark({
      name: "bible", feature: "bible", kind: "bible",
      decorate(span) { span.classList.add("ref"); span.setAttribute("role", "link"); span.tabIndex = 0; },
      tap() { return false; },   // the panel opens, with the tapped span in ctx.span
    });
    panelSection({
      name: "bible", feature: "bible", order: 30,
      render(ctx) {
        if (!ctx.span) return null;
        const box = h("section", { class: "bible-block" });
        const version = ctx.me.features.bible.version;
        api("GET", "api/bible/" + encodeURIComponent(version) + "/" + encodeURIComponent(ctx.span.dataset.value))
          .then(r => { if (r.status === 200 && r.data) box.textContent = r.data.text; });
        return box;
      },
    });

A glossary feature is the same shape with `kind: "glossary"`, and may add a panelSection listing the terms of the paragraph. A search feature needs a screen of its own, which none of the places above gives; it adds a place for screens to core/ext.js and core/screens.js, with its tests, when it is built.

## Accounts and roles

One person has one account, and today every account is a reader: the reader's number is the account's number. The tables of signing in name it `account` (identity.account, session.account, auth_flow.account, access_request.account), and the routes that sign in lie under /api/auth/, not under a reader's path, so that other kinds of account join without a change to them. server/auth.py holds signing in and the session check, server/accounts.py the admin routes of accounts.

An account signs in through an identity (a LINE user id or an email address; table identity, one account to each identity) and holds one session per browser (table session). reader_auth() of server/auth.py finds the account of a request, by the session cookie or by a link that signs in by itself, and sets req.reader and req.session. Nothing in signing in looks at what the account may read: that is the work of the routes, through GRANTED in server/app.py.

Roles come when the first editor's or translator's account is needed. To add them:

1. A migration adds `role` to the reader table, `TEXT NOT NULL DEFAULT 'reader'`, so every account today stays a reader. Renaming the table to account is not needed and would break the code of every version before; the word "reader" stays the name of the table and the commands.
2. server/common.py gains the roles and what each may do. A route of the dispatch table in server/app.py, or of a feature, names the role it needs as its auth: "reader" stays as it is, and a new auth such as "editor" runs reader_auth() and then refuses an account whose role is not one of those allowed, with 403 and a code of its own. A feature declares such a route in ROUTES like any other; AUTHS in server/features/\_\_init\_\_.py gains the new kind with its own path prefix, as /api/edit/NAME/.
3. invite, the reader list and the admin page gain the role; an editor is invited and signs in exactly as a reader does, so nothing of signing in changes.
4. A document other than a published chapter, such as a chapter file that an editor and the translator take through several turns before the translator commits it to a branch, or the files of a QA round or a raw-translation round, gets tables of its own (document, document_version, document_comment, with a turn and its author's account) and its own grants, as `document_grant (account, document, may)`. The chapter tables, the comment table and the reader routes stay as they are, so readers never meet the new documents. Comments and the discussion on a document carry the account that wrote them, never a name, as reader comments do.
5. Each new role or document gets its tests beside tests/test_auth.py, and the core tests check only their own entries, so readers keep working while the suite grows.

The two-device lock of a link that signs in by itself (reader_device) stays for the readers with "Link signs in". When no reader needs it any more, a later version may drop the lock and its table with a migration.

## The five features planned

**More languages.** Lao: a registry entry and a Lao font (above), a format module for the GC Markdown chapters, and Lao strings for the interface if Lao readers want a Lao interface.

**More book formats.** One module in parsers/ for each, such as gc_markdown.py for the Lao GC chapters or a module for a book kept in another layout. Nothing else changes.

**Bible references as links, with a Bible version per reader.** An annotator `bible_refs` marks each reference as `<span data-kind="bible" data-value="John 3:16">`. A feature `bible` adds a setting `bible.version` (a new setting type: one of a list), so each reader or group chooses a version; a table `bible_verse` filled by an admin route from the translator's Bible files; and a reader route `GET /api/bible/<version>/<reference>` (the sub-pattern `([A-Za-z0-9]+)/(.+)`). The page shows each marked span as a link that opens the verse.

**Glossary and dictionary look-ups.** A feature `glossary` with a table `glossary_term` filled by an admin route from the project's glossary file (th/assets/translation_profile/thai-glossary.txt), a reader route `GET /api/glossary/lookup?term=` (the sub-pattern `lookup`), and a bool setting `glossary.on`. An annotator `glossary_terms` may mark known terms with `data-kind="glossary"`. A dictionary is the same shape with its own table and route.

**How a word was translated in other books, with fuzzy matching.** A feature `search` keeps its index in an SQLite FTS5 table of its own, made by its migration: `CREATE VIRTUAL TABLE search_para USING fts5(book, ch, a, text, en, tokenize='trigram')`. The trigram tokenizer suits Thai and Lao, written without spaces between words, but it finds only exact runs of three or more characters: a phrase query for a word with one vowel changed finds nothing. A near match comes from the query's own trigrams joined with OR and ranked by bm25, which put the paragraph with the right word first in a trial on SC01-08; a word of one or two characters needs LIKE on the table, since it has no trigram. The other books are published like any book but granted to nobody, so they are in the chapter table without reaching readers. The index is rebuilt from the chapter table, with server/content.py's plain() taking the HTML out, by an admin route that `review.py search reindex` would call; keeping it current at every publish needs one new hook in the registry, `on_publish`, added with that feature. A route `GET /api/search/?q=` (the sub-pattern empty) answers the matching paragraphs with their text and English, ranked by FTS5's bm25, from the books the reader may search.
