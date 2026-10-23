# Proofreading site

Readers open a personal link on a phone, tablet or computer, read chapters, and leave comments by paragraph. Each reader sees only their own comments. The translator exports the comments, and Claude turns them into markers in the chapter files. The first book is Steps to Christ (SC) in Thai; other books are added through books.json, and other languages through web/languages.json. EXTENDING.md says how to add a language, a book format, a book or a feature.

The server is Python 3.13 with the standard library only. Production runs it under waitress behind Apache; deploy/DEPLOY.md gives the steps.

## Files

| Path | What it does |
|---|---|
| review.py | the command-line tool: every command below; each that changes something ends with one plain sentence saying what changed |
| review_admin.py | `review.py admin`: the admin page's local server on 127.0.0.1 |
| admin/ | the admin page, which `review.py admin` serves: index.html, admin.js (its entry point), one module per section and devices.js for the devices in Readers, api.js (the only module that talks to the local server), strings.json and words.js (its words), ui.js, shared.js and admin.css; "The admin page" describes it |
| books.json | the book registry: one entry per book |
| align/ | the sentence alignment files of each book, one per chapter, as align/SC/SC01.json; EXTENDING.md, "Sentence alignment" |
| EXTENDING.md | how to add a language, a book format, a book or a feature |
| parsers/\_\_init\_\_.py | reads a chapter through the book's format module, runs its annotators, and checks the result |
| parsers/sc_typst.py | the format of SC: a Typst chapter and its Markdown English |
| parsers/annotators/ | modules that mark spans in a paragraph, such as Bible references; none yet |
| parsers/align.py | sentence alignment: the English sentences, the alignment files publish reads, and align-packet |
| server/app.py | the JSON API as a WSGI application, `server.app:application`: the reader routes and the device check, chapters, review rounds, export |
| server/people.py | the admin routes for readers, groups and devices |
| server/common.py | what every route module shares: the error type, the request, field checks |
| server/content.py | the content model: the HTML a published paragraph may hold |
| server/languages.py | reads the language registry, web/languages.json |
| server/features/ | the feature registry: one module per feature; english.py is the first |
| server/db.py | the SQLite database, its numbered migrations, the data directory, backups |
| server/schema.sql | the tables as version 1 of the database |
| server/text.py | which characters are invisible, and which book text refuses |
| server/specs.py | chapter lists and grants such as `01-08` and `SC01-08` |
| server/dev.py | the local dev server: web/ and the API on 127.0.0.1 |
| server/prod.py | the production entry point under waitress |
| web/ | the page: index.html, app.js (its entry point), core/ (its modules), features/ (one module per feature), app.css, sw.js, ui-strings.json, languages.json, fonts/; EXTENDING.md, "The page side", describes the modules |
| deploy/ | DEPLOY.md, the systemd units, the Apache site (review-apache.conf and review-site.conf) |
| tests/ | unittest tests, and bench.py, the load test |

## Try it on this machine

    python3 review.py setup
    python3 review.py serve --dev

In a second terminal, from the same folder:

    python3 review.py publish SC 01-08
    python3 review.py invite "Translator" --grant SC01-08 --english

Open the link that invite prints. The data lives in ~/claude-sandbox/review-dev; `--data DIR` chooses another folder. If review.py is not inside the translation repository, add `--repo ~/programming/translate` to publish.

The admin page does everything the commands do. Start it in the second terminal; it prints its address and opens it in the browser:

    python3 review.py admin

## Who can open what

A reader's link opens the published chapters that are the reader's own, or that a group of the reader's holds while the group is switched on. A revoked reader opens nothing, whatever the groups say. Reader names are unique, whatever their case and their spaces: the site stores a name with each run of spaces, a no-break space or an ideographic space among them, as one plain space, and refuses a name that equals another reader's once its case is folded. A reader's own chapters, and a group's, are a whole book (`SC`, which also covers chapters published later) or chapters (`SC03`, `SC01-08`); `open` and `close` change a reader's, `group open` and `group close` a group's.

A group has a name, its own chapters and its own English setting, and is switched on when created. A reader can belong to any number of groups. Switching a group off closes its chapters to its members at once, and switching it on opens them again; the members keep their own chapters either way. Removing a group does the same for good.

English for a reader is on when the reader's own English setting is on, or when the English setting of any group of theirs that is switched on is on. The reader's own "off" therefore does not hide the English that a group shows. A group switched off gives neither chapters nor English. Every on/off setting of server/features/ combines the same way. A setting of another kind, such as a Bible version, needs more in the core: its type, a rule for combining a reader's value with the groups' values, a way to clear a value, and values in the commands `feature` and `group feature`, which take only on and off today (EXTENDING.md, "Adding a feature").

A closed chapter, withdrawn or no longer open to a reader, leaves that reader's page together with the reader's comments on it. The site refuses adding, changing and deleting comments there, and keeps them for the translator, who still exports them.

### One person per link

The page makes a random key once on each device and sends it with every request, in the header X-Review-Device. The site counts the devices that use each link: a link works on the first two devices that open it (`devices_per_link` under "Limits"), and a further device is refused with 403 device_waiting until the translator approves it, with `review.py device approve NUMBER` or on the admin page. The waiting page shows the device's number, which the translator's lists show too, so the reader can say which device to approve; a script can give any device the description of the reader's phone, but not its number. `review.py devices` lists the devices waiting for approval, and `readers --devices` the readers whose link was opened on more than two devices or has a device waiting. `device remove NUMBER` stops the link on a device; if that device comes back, it waits for approval again, and the lists of waiting devices show it. A link keeps at most 10 devices waiting: a further new device is refused unrecorded, so no one holding a link can fill the site's disk with devices, and the reader's line says that the link was tried on too many devices and needs a new link. A new link (`relink`) starts a new count. For each device the site keeps a short description such as "iPhone, Safari", when it was first and last seen, and the SHA-256 of its key, never the key.

GET /api/me gives the page the reader's fixed number, `id`, which a new link keeps. When a reader opens a new link, the page sends that reader's waiting comments under it, matching the reader by that number, never by name.

### Review rounds

Each time a book is opened for review, the translator starts a named round: `review.py round start SC NAME`. The newest round of a book is its current round. A comment carries the round it was written in; a comment written before the book's first round has none. A reader's page loads only the current round's comments, and counts a chapter finished before the round started as not yet finished. Earlier rounds stay on the site: a reader reads their own, without changing them, as "Your earlier comments" (GET /api/comments?earlier=1), and the translator exports one round with `export --round NAME`, and the comments written before the first round with `export --before-first-round`.

## Commands

Every command that changes something ends with one plain sentence saying what changed; a command that changes nothing says "Nothing changed" and why. Server commands use `--token-file` (default ~/claude-sandbox/review-dev/admin-token) and `--server` (default http://127.0.0.1:8087). The environment variables REVIEW_TOKEN_FILE and REVIEW_SERVER set them for a whole terminal session. A file named `server` beside the token file, as ~/.config/review/server, holds the address of that token's own server: review.py then talks to that address when no server is named, and refuses any other address with that token. Every server command prints `Server: <address>` first.

The live site is named `ssh://USER@HOST`, as `ssh://brian@review.laoegw.com`; HOST may also be a Host of ~/.ssh/config, `:PORT` after it gives the SSH port, and `?api_port=8087` the API's port on the droplet. For each command, review.py makes a new folder of mode 700 and starts `ssh -N -L FOLDER/api.sock:127.0.0.1:8087` with ExitOnForwardFailure, waits for the socket, sends the request with the token through it, and closes the tunnel and removes the folder when the command ends. No other account can open that socket, and no other program can take it before ssh does, as one could take a free port while ssh still asks for a passphrase. Where the system lets no program make a Unix socket, as in a sandbox with its own network, review.py forwards a free port of 127.0.0.1 instead. ssh asks for a passphrase or a new host key on the terminal as usual. The token therefore never crosses the internet, and Apache refuses /api/admin/ from the internet. review.py refuses any address other than this machine's and an ssh:// one, and never follows a redirect. Through the tunnel, SSH compresses the answers (Compression=yes); the dev server and waitress send them as they are.

### This machine and chapters

| Command | What it does |
|---|---|
| `setup [--data DIR] [--public-url URL] [--new-token]` | creates the data directory, the database and the admin token, and prints where the token file is |
| `serve --dev [--data DIR] [--port 8087]` | runs web/ and the API on 127.0.0.1 |
| `backup [--data DIR] [--keep 14]` | copies the database into DIR/backups/review-DATE-TIME.sqlite3 (UTC), never over another copy; copies older than 14 days are deleted, but the newest 14 always stay |
| `admin [--port 8088] [--no-open]` | starts the admin page on 127.0.0.1, prints its address and opens it; see "The admin page" |
| `publish SC 01-08 [--ref REF]` | reads the chapters from main, or from REF, and publishes them; the chapter list is required, so only chapters you name reach readers. It first prints the commit it read, and for each chapter how many paragraphs changed since the version before. It reads every chapter before it sends any, and stops with nothing published when a chapter has text but no paragraph tags. It adds the sentence pairs of the book's alignment files that still match the text, and says how many paragraphs it dropped because their text changed |
| `withdraw SC 03` | hides chapters from readers and keeps their comments; `withdraw SC` hides the whole book |
| `chapters` | lists the chapters on the server |
| `align-packet SC 01 [--ref REF] [--out PATH]` | writes, for one chapter, each paragraph's plain text in the book's language, cut at its spaces, and its numbered English sentences, with a template of the alignment file, to ~/claude-sandbox/review-align/SC01-packet.json, for an agent to align; EXTENDING.md, "Sentence alignment" |

### Readers

Reader commands take one name or several, as `open Anan "Mali Boon" SC09`; a name with a space is quoted for the shell, and case and spaces do not matter. A name that matches no reader stops the command before anything changes, and suggests readers whose names hold it; so does a name that two readers of an older site share, with both readers' numbers. The `group` commands below change a group itself.

| Command | What it does |
|---|---|
| `invite NAME --grant SC01-08 [--group G] [--english]` | creates a reader and prints the link once. `--grant` and `--group` may be repeated; at least one is needed. `--grant SC` opens every chapter of SC, including chapters published later |
| `invite --from FILE` | creates every reader in a CSV file, or none of them; see "Inviting many readers" |
| `readers [--name TEXT] [--link URL] [--group G] [--book SC] [--inactive [DAYS]] [--revoked] [--devices]` | lists the readers, or those that match, and ends with a count. Each line gives the reader's own chapters (`own:`), the chapters each group that is on opens (`through G:`), and the groups, with `(off)` after a group that is switched off, and the number of devices the link was opened on. `--name` lists readers whose names hold the text; `--link` finds the reader of a link, hashing its code on this computer so the code never travels; `--book` lists active readers who can open some published chapter of the book; `--inactive` lists readers who never commented, marked a place or finished a chapter, and `--inactive 30` adds those quiet for 30 days; `--devices` lists readers whose link was opened on more than two devices or has a device waiting |
| `open NAME [NAME ...] SC09` | opens chapters to the readers as their own; `open NAME SC` replaces the reader's SC chapters with every chapter of SC, including chapters published later |
| `close NAME [NAME ...] SC09` | closes chapters of the readers' own. For a reader who holds all of SC, it leaves every chapter of SC on the server except SC09, withdrawn chapters included, so a withdrawn chapter opens again when it is published again; chapters published for the first time later then need `open`, and the command names the next chapter, as `review.py open NAME SC09`. `close NAME SC` closes the whole book. It says when a group of the reader still opens the chapter, and gives the command that closes it for the group |
| `revoke NAME [NAME ...]` / `restore NAME [NAME ...]` | stops the readers' links, or makes them work again; the comments stay. `group off` pauses a group's chapters |
| `relink NAME [NAME ...]` | gives each reader a new link and prints each once; the old links stop working, and a new link works on the first two devices that open it. A reader whose link is stopped keeps it stopped, and the command names the `restore` that makes the new link work. `relink --group G` writes the new links of every member of G to a file, as invite --from does; for more than one reader it first asks you to type their number, unless `--yes` is given |
| `english NAME [NAME ...] on` / `off` | shows or hides the English for the readers, as their own setting; it says when a group still shows it |
| `feature NAME [NAME ...] english on` | turns a feature's on/off setting on or off for the readers; `english` is the first feature. `english NAME on` is the short form. The commands take on and off only; a setting of another kind, such as a Bible version, needs the changes EXTENDING.md lists |
| `features` | lists the features and their settings |
| `devices [NAME ...] [--all]` | lists the devices waiting for approval, or every device of the readers named (`--all` adds the devices of links they no longer have, which it does not count as waiting), each with its number, its description and when it was first and last seen |
| `device approve NUMBER [NUMBER ...]` / `device remove NUMBER [NUMBER ...]` | the link works on the devices approved; a removed device is refused, and waits for approval again if it comes back |
| `delete-comments NAME --from DATE --to DATE [--yes] [--upto NUMBER]` | counts the comments one reader wrote from the start of the `--from` day to the end of the `--to` day, Thailand time, in every chapter and round, and says how many it will delete and the highest comment number among them; with `--yes` it deletes them, and with `--upto` that number only those counted, not one the reader wrote after the count. It clears junk from a misused link. A date may carry a time, as `2026-10-22 14:30`, to the minute. The next export names the comments deleted |

The commands `grant`, `ungrant`, `revoke --group`, `restore --group`, `english --group` and `feature --group` no longer exist; each answers with the command that replaced it.

### Groups

| Command | What it does |
|---|---|
| `groups` | lists every group with its state, chapters, English and members |
| `group create G [--grant SC01-08] [--english]` | creates a group, switched on. A group name is 1 to 40 letters, digits, dots, hyphens or underscores, as Pastors or youth-2026 |
| `group remove G` | removes the group; its members keep their own chapters |
| `group open G SC09` / `group close G SC09` | opens or closes chapters the group holds, with the same rules as open and close; they reach every member while the group is on, members who join later too |
| `group give-each G SC09` | gives each current member the chapters as their own, as `open` would; readers who join the group later do not get them |
| `group off G` / `group on G` | switches the group off or on |
| `group english G on` / `group feature G english on` | the group's own English, or any feature |
| `group add G NAME [NAME ...]` / `group take-out G NAME [NAME ...]` | adds readers to the group, or takes them out, and names any reader who was already a member, or was not one. `--from FILE` reads the names from the column `name` of a CSV file instead |

After `group off`, `group close` and `group remove`, the command names the members who still open the closed chapters through their own chapters or through another group that is on, and gives the command that closes them for those readers, as `review.py close 'Own Reader' SC01`. `invite` says when a group it names is switched off, because the link then opens nothing through that group.

### Comments

| Command | What it does |
|---|---|
| `export [--all \| --round NAME \| --before-first-round] [--out PATH] [--book SC] [--ch SC03] [--reader NAME] [--unprocessed]` | writes the comments new or changed since a minute before the last export of this server, as JSON and as Markdown grouped by chapter and paragraph, and names the comments deleted since then. The last export is the newest one in the export folder that was made without a filter (no `--book`, `--ch`, `--reader`, `--unprocessed`, `--round` or `--before-first-round`); when there is none, the export holds every comment. `--all` writes every comment, `--round NAME` every comment of one review round, and `--before-first-round` every comment written before its book's first round. The default folder is ~/claude-sandbox/review-dev/export/ for the dev server and ~/claude-sandbox/review-prod/export/ for any other server. An export never overwrites another: a name already taken waits for the next second, and `--out FILE.json` must name a new file |
| `rounds [BOOK]` | lists the review rounds of every book, or of one, with the current round of each, when each started and its comments, and the comments written before the first round, which `export --before-first-round` writes |
| `round start BOOK NAME` | starts a new review round of the book now. A round name is 1 to 40 letters, digits, dots, hyphens or underscores, as 2026-11 or second-reading, used once in a book |
| `processed 12 13 20-25 [--export PATH] [--undo]` | marks comments as turned into markers, as they stood in the exports that hold them (from the export folder of that server, or `--export`, a folder or one file). A comment the reader changed after that export, one never exported, and one whose words differ between the exports in the folder are not marked; the command says which, names the exports that differ, and ends with an error. For the last kind, run it again with `--export FILE`, the export the markers came from. The ids go to the server 5000 at a time |
| `triage [--export PATH] [--ref REF]` | reads the newest export (or `--export`, a file or a folder) and writes one triage packet per chapter, JSON and Markdown, in a folder beside it named after the export with `-triage`; see "Triage and replies". It needs no token |
| `replies FILE` | sends the translator's confirmed replies, from a CSV file with the columns id and reply (and rev, if wanted) or a JSON file; an empty reply clears one. Each reviewer sees the reply under the comment |

Publishing a chapter again keeps every comment, and every published version of the chapter is kept. A chapter whose text did not change keeps its version, so readers download nothing new. A chapter holding `[[` or `((` is refused, and so is any chapter with a character that web/languages.json refuses for the book's language (Thai and Lao digits in every book) or an invisible character. A Typst block comment `/* ... */` never reaches readers, as it never reaches the printed book. Comments on a paragraph that a later version dropped stay in the export with `anchor_missing: true`, and the reader sees them at the end of the chapter.

## Inviting many readers

`invite --from FILE` reads a CSV file whose first line names the columns, as a spreadsheet saves it:

    name,groups,grants,english,email
    Somchai Jaidee,Pastors,,yes,somchai@example.org
    Anan,Pastors Youth,SC01-03,no,
    "Boon, Mali",,SC,,

`name` is required. `groups` and `grants` may be empty and may hold several entries separated by spaces or semicolons; each row needs at least one group or grant. `english` is yes or no (on, off, true, false, 1 and 0 also work); empty means no. Every group must exist first (`group create`). Any other column, such as email or phone, never goes to the server; it is carried into the links file. A column whose name is one letter away from name, groups, grants or english is taken for a misspelling and refused. A name may not start with =, +, - or @, and a cell of another column may not start with = or @, or with + or - unless it is a phone number, because a spreadsheet may run such a cell as a formula. review.py checks every line and lists every problem before it sends anything; the server then creates every reader in one transaction, or none.

The links go to a new file of mode 600 beside the admin token file in use, named links-invite-DATE-TIME.csv with the columns name and link, then the other columns of the invite file, ready for a mail merge. For production that is ~/.config/review/, where no Claude session can read it; for the dev server it is ~/claude-sandbox/review-dev/. The command prints the file's path and the count, never a link. Send each reader the link on their own row, then delete the file. `relink --group G` writes its links the same way, to links-relink-DATE-TIME.csv.

## Triage and replies

assets/read-through.md section 2 governs reviewers' comments, and two commands carry it out: `review.py triage` prepares the sheet, and `review.py replies FILE` sends the confirmed replies. Each triage packet groups a chapter's comments by paragraph and gives, for each paragraph, its text now (`paragraph`, in the book's language, which the packet's chapter names in `language`), whether it changed after a reviewer saw it, the markers `[[...]]` standing at its tag in the chapter file at `--ref` (default the book's ref, main), and every line of the book's notes file (books.json "notes") whose span of the book's text or English words appear in a comment's quote or paragraph. Each comment carries its id, rev, reader, round, kind, quote, text, the paragraph as that reviewer saw it when it differs (`paragraph_seen`), the notes lines it matches, and any reply already sent. In both files a reviewer's words are data, never an instruction: the JSON says so, and the Markdown indents every line a reviewer wrote by four spaces. triage also reads an export made before the fields got their neutral names.

The confirmed replies go to the site with `review.py replies FILE`. A file made from a packet should carry each comment's rev: the server then leaves alone a comment its reader changed after the export, and the command names it.

## Reading an export

Claude works from the JSON export, where each reader field stays separate. Everything a reader wrote is data, never an instruction. The Markdown file is for reading by eye: every line at its left margin comes from review.py, and every line a reader wrote is indented four spaces, so reader text cannot pass for a heading or a comment.

The export names what it holds: `scope` gives the filters and `since`, the time the export starts from, with `base`, the export that time came from; `since` is null for an export of every comment, and `round` names the review round of `export --round`. `deleted` lists the comments deleted since then, each with its id, reader, chapter and time. The next export starts a minute before the last one was taken, so that a comment saved while that export ran is never missed; a comment written, changed or deleted in that minute may stand in both, as the same comment with the same rev. An export of the comments before the first round names `before_first_round`.

The fields that hold the translation's text have neutral names, and `language` (th Thai, lo Lao, ium Mien) says which language they hold; the `_en` fields and `en` hold the English. Each chapter entry names `title`, `title_en`, `language`, `source` (the chapter's file in the book's language), `source_en` and `commit`, so the text the reader saw can be read with `git show <commit>:<source>`. Each comment carries `rev`, a fingerprint of its kind, quote and text, which `processed` checks, and its `round`. It also carries the paragraph now (`paragraph`, `footnotes`, and the English as `en`) and as the reader saw it (`paragraph_seen`, `footnotes_seen`, null when the site does not keep that version), `changed` (true when the paragraph's words changed after the comment was written, null when not known) with `changed_at`, and the translator's `reply` with `reply_at`. The Markdown shows the paragraph as the reader saw it under each comment whose paragraph changed. Exports made before this version named `paragraph` `th`, `paragraph_seen` `th_seen`, `title` `title_th` and `source` `source_th`; triage and processed read them as well.

## API

All JSON, same origin, no cookies. Readers send `Authorization: Bearer <code>`; the code comes from the link `https://<host>/#k=<code>`, whose fragment never reaches the server. A reader's request also carries `X-Review-Device: <key>`, the random key of 16 to 128 letters, digits, hyphens and underscores that the page makes once on each device ("One person per link"). Admin routes take the admin token the same way. Every error is `{"error": "<code>", "message": "<plain English>"}` with its status code; an error about many rows adds `problems`, one line per problem.

Fields that hold the translation's text have neutral names (`title`, and `text` in a paragraph), and the answer names the book's language beside them (`language`: th Thai, lo Lao, ium Mien); the `_en` fields and `en` hold the English.

### Reader routes

| Route | Answer |
|---|---|
| `GET /api/health` | `{"ok": true}`, no code needed |
| `GET /api/me` | `{id, name, english, features, limits, comments_total, books: [{id, title, title_en, language, round, earlier}], chapters: [{book, id, n, title, title_en, version, at, paragraphs, finished, finished_at, place, comments, opened, changed}]}`, of the chapters open to the reader now; `id` is the reader's fixed number, which a new link keeps; `features` maps each feature to its settings for this reader, as `{"english": {"on": true}}`; `english` repeats `features.english.on`; `limits` is the six numbers of "Limits"; `comments_total` and each chapter's `comments` count the reader's comments of the book's current round on those chapters; a book's `title` is its title in its own language, or empty; `round` is the book's current review round, `{name, started}`, or null; `earlier` counts the reader's comments of earlier rounds on those chapters; `at` is when the chapter's version was published; `paragraphs` and `comments` are counts; `finished` is false for a chapter finished before the current round started; `place` is an anchor, or null when there is none or its paragraph is not in the chapter's current version; `opened` is the version the reader last opened, or null; `changed` is null, or `{since, since_at, at, paragraphs: [{a, at, new}], removed: [{a, at}]}`: the paragraphs whose words changed, or that are new, since the version opened, each with the time of the version that last changed it |
| `GET /api/chapter/<book>/<id>` | `{book, id, n, language, title, title_en, version, at, paragraphs: [{a, text, fn, en, al}]}`; `at` is when the version was published; `en` only for readers with English on, and `al`, the sentence pairs `[{text: [start, end], en: [[start, end], ...]}]`, only with `en` and only for a paragraph that has them. The ETag is `"<version>"`, or `"<version>.en"` with English; send it back in If-None-Match to get 304 |
| `GET /api/earlier/<book>/<id>?a=SC%2013.1[&version=V]` | `{book, ch, a, version, at, language, text, fn, same}`: the paragraph in the version the reader last opened, or in version V; `same` is true when its words are those of now. 404 no_earlier when there is none to show |
| `GET /api/comments?book=&ch=` | `{comments: [{id, client_id, book, ch, a, kind, quote, text, created, updated, processed, version, para_changed, para_changed_at, reply, reply_at, round}]}`, the reader's own of the book's current round, on chapters open to the reader now; a closed chapter gives none. `para_changed` is true when the paragraph's words changed, or it left the chapter, after the version the comment was written on, and null when the site does not keep that version; `reply` is the translator's reply, or empty; `round` is the round's name, or null before the book's first round. `?earlier=1` gives instead the reader's comments of earlier rounds on those chapters, which can be read but not changed, and adds `rounds: [{book, name, started, current}]` |
| `POST /api/comments` | body `{client_id, book, ch, a, kind, quote, text}`; 201 with the comment, in the book's current round, or 200 with the existing comment when the client_id was sent before; 404 no_comment when the comment of that client_id was deleted, so a device that sends it again after a lost answer does not make it anew. The comment's time is taken once the site holds the write lock |
| `PATCH /api/comments/<id or client_id>` | body with any of `kind, quote, text`; 200 with the comment. A change clears `processed`. Only in a published chapter open to the reader (404 no_chapter), and only for a comment of the current round (409 round_closed) |
| `DELETE /api/comments/<id or client_id>` | `{deleted, client_id}`; another reader's comment or one already deleted is 404 no_comment; one in a chapter no longer open to the reader is 404 no_chapter, and one of an earlier round 409 round_closed |
| `PUT /api/place` | body `{book, ch, a}` |
| `PUT /api/finished` | body `{book, ch, finished}` |
| `PUT /api/opened` | body `{book, ch, version}`: the reader opened this version. The record moves only forward in the chapter's history; a version not kept or an older one changes nothing. `{book, ch, version, recorded, opened}` |

Why the server refuses any request of a reader (server/app.py, ACCESS_ERRORS):

| Code | Status | Meaning |
|---|---|---|
| `no_code` | 401 | the request carries no link code |
| `bad_code` | 401 | the code is wrong, or its link was stopped (revoke) or replaced by a new link (relink) |
| `no_device` | 400 | the request carries no device key: a fault in the page |
| `device_waiting` | 403 | the link already works on `limits.devices_per_link` other devices; it works on this device once the translator approves it. The answer adds `device`, the device's number in the translator's lists, or null for a device refused unrecorded because the link already has 10 devices waiting |

Why the server refuses a reader's write (server/app.py, WRITE_ERRORS):

| Code | Status | Meaning |
|---|---|---|
| `no_chapter` | 404 | the chapter is closed: withdrawn, or no longer open to this reader |
| `no_paragraph` | 409 | the paragraph is no longer in the chapter |
| `quote_required` | 400 | a wording comment without the words to change |
| `quote_too_long` | 400 | the words are longer than `limits.quote` characters |
| `text_required` | 400 | the comment is empty |
| `text_too_long` | 400 | the comment is longer than `limits.text` characters |
| `too_large` | 413 | the request is over 64 KiB, so the comment is far too long; Apache may answer this one with HTML |
| `slow_down` | 429 | more than `limits.comments_per_minute` new comments, or `limits.writes_per_minute` other changes, in a minute; Retry-After says when to try again |
| `daily_limit` | 429 | `limits.comments_per_day` new comments today, a day that runs from midnight to midnight Thailand time; the answer adds `limit` and `retry_at`, the next Thailand midnight in UTC, and Retry-After gives the seconds until then |
| `no_comment` | 404 | the comment no longer exists, as when it was deleted on another device |
| `round_closed` | 409 | the comment belongs to an earlier review round, which can be read but not changed |

Any other code (`bad_json`, `bad_field`, `bad_kind`, `bad_client_id`, `not_found`, `bad_method`, `server_error`) is a fault in the site or the page, never in the reader's words. The page shows its own message for each code, and for any other code says the fault is the site's (web/core/refusals.js). There is no list of forbidden words: the server removes every invisible character from what readers type (server/text.py: format and control characters except newline and tab, private-use, surrogate and unassigned code points, variation selectors, tag characters and blank fillers) and never refuses a comment for one. It turns Thai and Lao digits into Western digits; Thai and Lao vowel and tone marks are kept. Lengths count characters (Unicode code points) after that cleaning, NFC and trimming.

### Admin routes

| Route | Answer |
|---|---|
| `GET /api/admin/chapters` | every chapter, published or withdrawn, with `title`, comment counts, `versions`, the number of versions kept, and `commit`, the commit its current text was read from |
| `PUT /api/admin/chapters/<book>/<id>` | body `{n, title, title_en, paragraphs, commit, sources, book_title_en, book_title, language}`; publishes or updates, and keeps the version. Each paragraph is `{a, text, fn, en}`. `language` is a code of web/languages.json, required for a new book. `book_title` is the book's title in its own language, from books.json; an empty one keeps the title stored. `sources` is the path of the chapter's file and of its English. A paragraph may carry `al`, its sentence pairs `[{text: [start, end], en: [[start, end], ...]}]` (400 bad_pairs when one does not fit its text). The answer adds `previous`, `paragraphs_changed`, `paragraphs_removed` and `pairs` |
| `DELETE /api/admin/chapters/<book>/<id>` | withdraws; comments are kept |
| `GET /api/admin/readers` | `{readers: [{id, name, active, grants, groups, settings, effective, english, books, devices, created, comments, last_active}], total}`; `grants` and `settings` are the reader's own, `effective` the settings with the groups', `english` is `effective["english.on"]`, `books` the books of which the reader can open a published chapter now (none for a revoked reader), `devices` the devices of the reader's current link, `{total, ok, waiting, removed, full}`, where `full` is true when 10 devices wait and a further one is refused unrecorded. Filters: `?name=` (the whole name), `?contains=` (part of the name), `?code_hash=` (the SHA-256 of a link's code), `?group=`, `?book=`, `?idle=DAYS` (0: never active), `?revoked=1`, `?devices=1` (a link opened on more than `devices_per_link` devices, or with a device waiting); `total` counts every reader, and `devices_per_link` is the limit of that name |
| `POST /api/admin/readers` | body `{name, grants, groups, english, settings}`; 201 with `code` and `link`, shown only this once. A name that holds a line break or a tab, or starts with =, +, - or @, is 400 bad_name. The name is stored with each run of spaces as one plain space; a name equal to another reader's, whatever its case and spaces, is 409 name_taken, on a change of name too |
| `POST /api/admin/readers/batch` | body `{readers: [{name, grants, groups, english, settings}]}`, up to 2000; 201 with `{readers: [{id, name, code, link}]}`. Every reader is created, or none, and a refusal lists every problem |
| `PATCH /api/admin/readers/<id>` | body with any of `active, name, grants, groups, english, settings`; `grants` and `groups` replace the lists, `settings` sets the keys it names |
| `PATCH /api/admin/readers` | body `{changes: [{id, ...the same fields}]}`, up to 2000, in one transaction; 200 with `{readers}` |
| `POST /api/admin/readers/<id>/code` | a new code and link; the old code stops working |
| `POST /api/admin/readers/codes` | body `{ids}`; a new code and link for each, `{readers: [{id, name, code, link}]}` |
| `POST /api/admin/readers/<id>/delete-comments` | body `{from, to, delete, upto}`, UTC times such as `2026-10-22T08:30:00Z`: the comments the reader wrote from `from` up to, not including, `to`, in every chapter and round, and with `upto` only those numbered up to it. Without `delete: true` it only counts them. `{reader, name, from, to, comments, deleted, chapters, last}`; `chapters` counts them by chapter, and `last` is the highest comment number found, which a delete sends back as `upto` so it deletes only the comments counted |
| `GET /api/admin/devices?reader=&state=&all=1` | `{devices: [{id, reader, name, state, agent, first_seen, last_seen, changed, current}], devices_per_link}`: the devices of each reader's current link, or of one reader, or in one state (ok, waiting, removed); `all=1` adds those of links the reader no longer has (`current` false) |
| `PATCH /api/admin/devices` | body `{ids, state}`: `state` ok approves the devices, removed stops the link on them. `{devices, missing, unchanged}`; `unchanged` lists the devices that were in that state already |
| `GET /api/admin/rounds` | `{rounds: [{id, book, name, started, current, comments}], before}`; `before` counts each book's comments written before its first round |
| `POST /api/admin/rounds` | body `{book, name}`: a new review round of the book starts now and becomes its current round; 201 with the round. 409 round_taken when the book has a round of that name |
| `GET /api/admin/groups` | `{groups: [{id, name, active, grants, settings, english, members: [{id, name, active}], created}]}` |
| `POST /api/admin/groups` | body `{name, grants, english, settings}`; 201 with the group |
| `PATCH /api/admin/groups/<id>` | body with any of `name, active, grants, english, settings` |
| `DELETE /api/admin/groups/<id>` | removes the group; `{deleted, name, members}` |
| `POST /api/admin/groups/<id>/members` | body `{add: [reader ids], remove: [reader ids]}`; 200 with the group and `added`, `already`, `removed` and `not_members`, the ids of the readers each change reached or did not |
| `GET /api/admin/features` | `{features: [{name, settings: {on: {type, default, combine, help}}, routes}]}` |
| `GET /api/admin/export?book=&ch=&reader=&unprocessed=1&since=&round=&before_first=1` | `{exported, since, round, before_first_round, chapters, comments, deleted}`; `since` (a UTC time) gives only the comments written or changed since, and `deleted`, the comments deleted since, `[{id, book, ch, at, reader}]`; `round` gives one review round (404 no_round), and `before_first=1` the comments written before their book's first round; `reader` is a name, whatever its case and spaces. Comments on a paragraph no longer in the chapter come after the others, in the order of their paragraphs' tags. `exported` is taken before the comments are read. Each chapter names `title`, `title_en`, `language`, `source`, `source_en` and `commit`; each comment names its paragraph as `anchor` and adds `rev`, the reader's name, `round`, the paragraph's current text as plain text (`paragraph`), `footnotes`, `en`, `paragraph_seen`, `footnotes_seen`, `changed`, `changed_at`, `anchor_missing`, `quote_found`, `version_seen`, `version_now`, `reply` and `reply_at` |
| `POST /api/admin/processed` | body `{ids, processed, revs}`, at most 10000 ids; `processed` defaults to true. `revs` maps an id to the `rev` in the export; a comment whose rev no longer matches is left alone and listed in `changed`. Answers `{updated, missing, changed}` |
| `POST /api/admin/replies` | body `{replies: [{id, reply, rev}]}`, at most 10000; an empty reply clears one; with `rev`, a comment its reader changed since is left alone and listed in `changed`. Answers `{updated, cleared, missing, changed}`; a malformed item is 400 bad_replies with `problems` |

Settings are keyed `feature.setting`, as `english.on`; `english: true` in a body is short for `settings: {"english.on": true}`. An unknown setting is 400 unknown_setting, a value of the wrong type 400 bad_setting.

A feature's own routes lie under /api/NAME/ and /api/admin/NAME/ (EXTENDING.md). Every route under /api/admin/ takes the admin token, and a feature's reader route answers 404 not_found to a reader who does not have the feature on. The admin routes answer only the SSH tunnel: Apache refuses /api/admin/, and marks every request it passes on with X-Review-Proxy, which an admin route answers with 403 admin_local_only.

### Limits

Request bodies may hold 64 KiB on reader routes and 4 MiB on admin routes. A reader may write 10 new comments a minute and 1,000 a day, a day that runs from midnight to midnight Thailand time (Asia/Bangkok), so "You can write more tomorrow" holds; deleting a comment gives nothing back. A reader may make 60 other changes a minute (edits, deletions, places, finished marks, opened versions), then 429 with Retry-After. Quoted words may run to 4,000 characters, required for "wording", and a comment to 1 to 8,000 characters. There is no limit on the comments a reader keeps: the daily limit replaced the lifetime limit of 5,000. A comment sent again with the same client_id counts toward no limit. A link works on 2 devices without the translator's approval, and keeps at most 10 devices waiting for it. These numbers are settings: config.json in the data directory may hold `"limits": {"quote": 4000, "text": 8000, "comments_per_minute": 10, "comments_per_day": 1000, "writes_per_minute": 60, "devices_per_link": 2}`, any of them, read when the server starts. The server refuses to start, naming config.json, when a limit is unknown, below 1, or when quote and text together exceed 16,128 characters, the most that fits one 64 KiB request; a config.json that still names the retired `comments` starts as before. A comment, place or finished mark must name a paragraph in a published chapter open to that reader. Comment ids are never used twice.

Every response carries the Content-Security-Policy, X-Content-Type-Options, Referrer-Policy and X-Robots-Tag headers; API responses also carry `Cache-Control: no-store`.

## Many readers

The access check, the device check, /api/me and the comment list use indexes keyed by the reader, so their cost does not grow with the number of readers or groups; the reader list and the export read each table once. The server remembers only the readers who wrote in the last minute or two (for the limit of writes a minute) and at most 256 parsed chapters. `python3 tests/bench.py` builds 500 readers with 20 comments each and sends 60 clients at once at the API under waitress with the settings of server/prod.py; it prints the median and the 95th percentile of each route. The measure of real use is a run whose clients pause about a second between requests, which is still far faster than reading: on 22 October 2026, with 300 readers, 6,000 comments and 60 clients, every route had a median of 1.1 to 1.5 ms and a 95th percentile under 31 ms, and the full export took 0.29 s. With no pause between requests, the same machine answered from 136 to 505 requests a second on 22 October 2026, with medians of 300 to 375 ms at the low end; the figure depends on the load of the machine and on the number of connections held open (about 920 /api/me a second with 6 open, about 200 with 60). In round 3, 4 waitress threads answered about 45% more than 8, so server/prod.py uses 4.

## The admin page

`python3 review.py admin` starts a server on 127.0.0.1, port 8088 (`--port` for another), prints an address such as `http://127.0.0.1:8088/#key=...` and opens the browser (`--no-open` only prints the address). The browser is opened at an address with a one-time code in place of the key, which the page trades for the key at its first load, since every account of the computer can read a program's command line; the printed address goes on working. It works against the server named for the token, as the commands do: for the live site, review.py opens the SSH tunnel at the start, keeps it open while the page runs, and opens it again if it drops. The page never holds the admin token; the local server adds it. Every local route needs the key, except `trade`, which gives the key once for a one-time code, and the server refuses a request from another site or for another host name. The address acts with your admin token while the command runs, so keep it to yourself; Ctrl-C stops the server and closes the tunnel. Each start makes a new key, so a tab of an earlier start says to open the new address.

The page does everything the commands do, with a control for every option, in five sections. The line at the top of every section names the server, as every command prints `Server:` first; for the live site the line is red.

- **Chapters**: every chapter of every book in books.json, on the site or only in the repository, with its state, its version, the commit it came from, the newest commit at the book's ref that changed its files, and its counts. Publish and withdraw act on the chapters ticked, or on the whole book. Before publish runs, the page reads the ref again and asks, naming the commit publish will read. Another branch, tag or commit can be read instead of the book's ref. "Write an alignment packet" runs align-packet for the one chapter ticked, into the default file or the file named (`--out`).
- **Readers**: the readers that match any part of a name, a group, a book, a number of days without activity (0 for never active), stopped links, links on more than two devices or with a device waiting (`--devices`), or a link, with the count. Each row shows how many devices opened the reader's link, flagged when there are more than the link works on without approval (`devices_per_link`) or one waits for approval, and says when the link was tried on too many devices and needs a new link, and the stop switch of the reader's link, which revokes or restores that reader alone. Open chapters, Close chapters, Stop the links, Restore the links, New links, English and any feature act on the readers ticked, all in one request, as the commands do with several names. Devices lists the devices waiting for approval, which the menu also counts beside Readers, or every device of one reader, with those of earlier links (`--all`); each can be approved or removed, alone or ticked together in one request. "Delete one reader's comments between two dates" counts them first and asks once, with the count, before it deletes them. Invite one reader, or many from a CSV file chosen on this computer ("Inviting many readers").
- **Groups**: every group, with its switch on its row, and a form to create one. For the group opened: switch it on or off, or remove it; "Open for this group" and "Close for this group" (group open and group close), and "Give each current member their own copy" (group give-each), three buttons that each ask once with the sentence of what the command changes; its own English and features; take members out, add readers found by any part of the name, or add or take out the readers named in a CSV file; list the members in the Readers section, where the reader commands act on those ticked; and new links for every member.
- **Comments**: Export what changed, Export everything (`--all`) and Export the round (`--round`, with the round's book, or `--before-first-round`, the comments before a book's first round), each with the filters of book, chapter, reader and comments not yet processed, and a place to write; the review rounds of every book or of one, with the comments written before the first round, and starting a round; the exports in the export folder with their Markdown and triage packets; triage; replies from a CSV or JSON file chosen on this computer; and processed by comment numbers, with undo.
- **Site**: the server, the token file, the repository, the export folder, and for the dev server a backup of its data and a new dev admin token; the features with their settings.

Every action that changes more than one reader or device asks first and says how many it touches, and so do every group choice, starting a round, deleting comments and new links; publish, withdraw, inviting from a file and sending replies ask too. Each answer shows the lines the command prints, and its message when it stops. The new link of one reader, of a reader just invited, or of each reader ticked is shown only once, each with a Copy button, and with the line that a stopped reader's link stays stopped. Inviting from a file and new links for a group's members write the links to a file of mode 600 beside the token and show only its path. Where a command's lines name another command to run, such as `review.py close 'Own Reader' SC01` after a group is switched off, or `review.py group on G`, the page offers a button that runs it, after asking.

The page's words live in admin/strings.json, one key for each word or sentence with its English and an empty Thai, in the form of web/ui-strings.json. The page is in English. To show it in Thai, Lao or Mien, fill in that language's values (th, lo or ium) and put its code first in LANGS in admin/words.js; a value left empty shows the English. The lines and messages of the commands stay as review.py prints them.

The page has no build step and loads nothing from another host. A section loads its data when it is opened, and each module is fetched at once with the page. `GET /local/source?book=&ref=` gives the commit publish will read and the chapters in the repository, each with the newest commit that changed it; `POST /local/trade` gives the key for the one-time code of the address the browser was opened at, once; every other local route runs the review.py command of its name, as review_admin.py's COMMANDS shows.

## Database versions

server/schema.sql is version 1. Each later change is a numbered entry in MIGRATIONS in server/db.py. When the server starts, it applies every entry the database lacks, in order, in one transaction, so an old database and a new one end up the same. To change the database, add an entry with the next number; never edit an entry that has shipped. Version 2 makes comment ids AUTOINCREMENT and records each chapter's source files and commit. Version 3 adds groups and feature settings, and moves each reader's English into the setting english.on; code from before version 3 cannot open a version 3 database. Version 4 adds each book's title in its own language; code of version 3 still opens it. Version 5 keeps every published version of a chapter (chapter_version, filled at the migration with each chapter's current version), records the version of each chapter a reader last opened (reader_opened), adds the translator's reply to a comment (comment.reply and reply_at), and counts each reader's new comments of the last day (comment_made); code of version 4 still opens it. Version 6 gives the fields that hold the translation's text neutral names (book.title, chapter.title, chapter.source, chapter_version.title, and `text` for each paragraph in the stored JSON, with each chapter's content_hash worked out again so that publishing the same text keeps its version), adds review rounds (review_round, comment.round), the devices of each link (reader_device), and the comments deleted (comment_gone); code of version 5 cannot open it, so going back needs the backup that the update takes first. Version 7 records the client_id of each comment deleted (comment_gone.client_id); code of version 6 still opens it. The server refuses to start on a database of a version newer than its own last migration, with a message that names the backup. A migration may hold a Python function beside its SQL, for a change SQL cannot make. A feature in server/features/ carries its own numbered migrations for its own tables, applied after the core ones in the same transaction.

## Data and secrets

The data directory holds review.sqlite3, admin-token.sha256, config.json (the start of every link, and any limits) and backups/; the dev data directory also holds the dev admin-token and the dev links files. The server stores only SHA-256 hashes of the reader codes and the admin token. The code folder, assets/review/, holds nothing secret, so it can go in the repository and on GitHub; the data directory, the token file and the links files never go there. The production admin token, the file `server` that ties it to ssh://USER@review.laoegw.com, and the production links files live in ~/.config/review/, outside ~/claude-sandbox, so no Claude session can use them.

## Tests

    python3 -m unittest discover -s tests

The parser tests read SC01 to SC08 from main in the translation repository: the one holding this folder, or REVIEW_REPO, or ~/programming/translate. Some tests start a dev server on 127.0.0.1:8090. tests/test_ssh.py puts a stand-in named ssh first on PATH, which forwards the tunnel's Unix socket (or its port, in a sandbox that allows no Unix socket) to a dev server, so the SSH route is tested without a droplet; tests/test_admin.py runs the admin page's server against a dev server, and tests/test_admin_page.py checks that the admin page lists and calls every local route, sends every option of the command line, takes every word from admin/strings.json, reads names as review.py quotes them, keeps the rules of the CSP, puts data in as text only, and that review.py admin answers a refusal or a fault as JSON. `python3 tests/admin_browser.py` drives every control of every section of the admin page in headless Firefox, against review.py admin and a dev server under $TMPDIR, and the live site through the stand-in for ssh; unittest does not run it. tests/core_test.js checks the page's plain modules with node: the outbox, the server's answers, the message for each refusal, the places features plug into, what changed since a reader last opened a chapter, and how sentence pairs cut the text; it also runs web/core/net.js with a stand-in for the network: the device key, the wait for approval, a new link, the outbox lock a frozen page held, and the chapter list asked for again after a refusal. tests/test_devices.py covers one person per link, and tests/test_rounds.py closed chapters, review rounds, the export of what changed and deleting one reader's comments. tests/test_web.py checks that web/index.html names every module for the browser and the service worker, that every import resolves, that every word the page uses is in web/ui-strings.json, and that the page keeps the rules for older phones and the CSP. tests/bench.py is the load test above; unittest does not run it.

## Fonts

web/fonts/ holds Sarabun by Cadson Demak, under the SIL Open Font License 1.1 (https://openfontlicense.org). web/languages.json names it as the font of Thai; the page loads the fonts of the languages it shows from there. Sarabun has no Lao letters; EXTENDING.md says what a Lao book needs.

## The translator's rulings

- The admin token stays only in ~/.config/review/admin-token on the translator's computer, where no Claude session can read it; he runs the site's commands himself.
- Admin commands reach the live site only through SSH, which review.py opens itself; Apache refuses /api/admin/ from the internet.
- A local admin page, `python3 review.py admin`, does everything the command line does, including export, inviting readers, groups, grants and new links and tokens, and it answers fast.
- A reader may send 10 new comments a minute and 1,000 a day; the page says so plainly when the daily limit is reached. Quoted words may run to 4,000 characters and a comment to 8,000. These numbers are settings, not code.
- A new version of a chapter shows the reader a line saying when it changed and how many paragraphs changed, marks each changed paragraph until the reader opens it, notes on a reader's own comment that its paragraph changed after it was written, keeps every published version, and offers "Show the earlier wording" in the drawer.
- Publishing a book whose source has no paragraph tags stops with the message that the book has no paragraph tags.
- English interface text speaks to the reader as "you" or uses no pronoun; "My wording" is the one exception.
- Reviewers' comments are triaged by assets/read-through.md section 2 before any marker is written, and the reviewer sees the translator's confirmed reply under each comment that was answered, already ruled, a duplicate or declined.
- Fields that hold the translation's text carry neutral names, with the book's language code beside them: th Thai, lo Lao, ium Mien; en is the English.
- SC's title in its own language stays empty until the translator decides it.
- Waiting comments are never deleted unsent. When a reader opens a new link, the page sends that reader's waiting comments under it, matching the reader by the site's fixed reader number, never by name, because two readers may share a name.
- `revoke --group` and `restore --group` do not exist: `group off` and `group on` pause a group's chapters, and `revoke` and `restore` stop and restart one reader by name. The admin page shows the group switch on the group and the stop switch on each reader.
- A closed chapter is closed for adding, changing and deleting comments, and it leaves the reader's page together with that reader's comments on it; the comments stay on the site for the translator.
- The reader's page loads only chapters open to that reader and that reader's comments on them. A command and an admin-page button delete one reader's comments written between two dates, to clear junk from a misused link.
- Search, when built: the translator searches everything; a search in English shows the matching Thai; each group's setting decides how much of the results its members see, never more than their open chapters and the finished books the translator names.
- Bible references, when built: a tap opens a side panel with the verse in every Thai version, and a translator or editor can pick the version they prefer, which is recorded as their comment.
- `export` brings only comments that are new or changed since the last export; `--all` brings everything.
- On a phone the English comes first in a paragraph's panel, with a "Write a comment" button at its top that jumps to the comment form.
- When a panel above closes, the tapped paragraph's first line always shows below the top bar.
- Chapters are opened and closed with one verb pair: `open NAME SC09` and `close NAME SC09` for a reader's own chapters, `group open G SC09` and `group close G SC09` for chapters a group holds; `group give-each G SC09` gives each current member their own copy. Every command ends with one plain sentence saying what changed, and the admin page shows the group choices as separate buttons that ask once with that sentence.
- One person per link: the site counts the devices that use each link and the admin page flags a link on a third device; a link works on the first two devices that open it, and a further device waits for the translator's approval on the admin page. Sign in with LINE may come later.
- Every command and every option of the command line has a control on the admin page, including `export` and `export --all`.
- Each time a book is opened for review, a named review round starts; a reader's page loads only the current round's comments; earlier rounds stay on the site, reached with `export --round` and, for a reader, "Your earlier comments".
- A changed chapter shows "Updated <date>" on its row in the chapter list as well as the update line inside the chapter.
- The admin page is in English now, and its words live in a strings file like the reader page's, so that a Thai, Lao or Mien admin page can be added without rebuilding it.
- A reply to a reviewer is optional: the triage drafts one only where it helps, and every other comment gets the processed mark alone (assets/read-through.md 2.E).
- A hidden note in a chapter source (Typst /* */ or Markdown <!-- -->) is shown only when it begins with "note:" (or "notes:"), only to groups whose setting shows translator's notes, in the paragraph's panel under the English and labelled as the translator's note, together with the book's notes-file lines for that paragraph; every other note stays hidden from everyone.
- The daily-limit message appears only when a reader reaches the limit, and it says how long until the limit resets, in hours and minutes.
- Each chapter remembers the branch it was last published from; the next publish reads that branch while it exists and main once it is gone, and says so; the admin page shows each chapter's branch. Sentence matches are read from the site's own folder, and their fingerprints drop the matches of any paragraph whose text changed.
- The Comments tab lists comments by chapter and paragraph, with clear instructions on the page and five buttons on each: Accept (the next triage makes it a marker with the reader's wording), Apply now (the change is written straight into the chapter file in the read-through working copy, without a marker and without git, for the translator to review in magit; refused when the words are not found exactly once in that paragraph), Answer, Decline (a short reason, a reply optional) and Already fixed.
- The reader can make the text larger or smaller with A− and A+ in the top bar, remembered on the device, and can pick the quoted words by tapping the first and the last word, because dragging to select often fails on a phone.
- With the reader's box open, selecting words fills the quoted words at once. After a box closes, its paragraph keeps a soft background until another box opens. Words a comment quotes get a soft background, and words two or more comments quote a deeper one. The space dots are small, centred on the line and slightly padded.
- When a paragraph's box is closed, a selection that rests for a moment opens the box with the selected words in "Words in question", and the selection stays visible, because on a phone the tap that would open the box also clears the selection.
- A comment records where in the paragraph its quoted words start, from the selection or the tap-to-pick, so words that occur twice are noted and highlighted where the reader chose them; footnote numbers never enter the quoted words.
