# SC side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many SC side quests are open and in what order, this file is the answer and no agent answers from memory. An issue he defers rather than decides is added here in the same reply that defers it, and an entry is deleted when its work is finished, not marked done, because a finished quest is in the commit history. Each entry says what the job is, where its detail lives, and roughly how big it is. It sits under a numbered-stage assets directory because the linter excludes those from every check.

## 4. Google Docs round trip

The translator's editor and reviewers work in Google Docs while the repository stays authoritative. The agreed design is th/SC/04_assets/planning/gdocs-workflow.md, distilled on 16 August; its minimal alternative, uploading the marker-laden file and letting the Doc's own comparison show the differences, is to be tested before anything larger is built. Until something is built, a chapter that passes check SCNN is uploaded by hand.

Detail: th/SC/04_assets/planning/gdocs-workflow.md. Medium.

## 8. A site from the SC01 studies for SC11

{SC 94.2} "the way to the mercy seat" stands without พระที่นั่งกรุณา, for SC11's qa2.

Detail: this entry. Small.

## 13. Standardize sons of God in SJ

SJ is unedited and its sons of God sites take one form under the row when SJ is edited.

Detail: this entry. Small.

## 15. SC12 note for qa2: the authority sentence at {SC 109.3}

{SC 109.3} "reason must acknowledge an authority superior to itself" reads พระคัมภีร์มีอำนาจเหนือความคิดของเรา, the editor's wording, which stands until qa2 weighs the sentence. The editor rejected สิทธิอำนาจ here as personifying the Bible too much and sounding political; the editor check found that อำนาจเหนือความคิดของเรา can read as control over our thoughts. The drill's two candidates, which the editor has not seen: ยังมีอำนาจที่สูงกว่าความคิดของเราเอง, which leaves the authority unnamed as the English does, and พระคัมภีร์อยู่เหนือความคิดของเราเอง, which can also be heard as "beyond our thinking".

Detail: ~/claude-sandbox/sc-audit/sc12-drill-2-editor.md. Small.

## 16. Feed the Thai GC hyphenation candidates into the Thai typesetting break list

Moved from the GC queue on 9 October. SC no longer keeps its own dictionary.typ list: break points now live in th/assets/typeset/thai-breaks.txt, which build_breaks.py turns into each book's dictionary.typ. The joined form of 77 of the 133 candidates already occurs in thai-breaks.txt, so about 56 remain to review, and the figures below for SJ and SC predate that change.

Thai running text has no word spaces, so the Typst pipeline has to be told where a long word may break. Both Thai projects do this with `04_assets/template/dictionary.typ`, and the two files are separate copies of the same mechanism at very different stages: SJ carries 457 entries and SC carries 92.

The Thai printed edition of GC supplies 133 more, taken from the places its own typesetter chose to break a word. They are in `th/GC/04_assets/editions/print/HYPHEN-CANDIDATES.tsv`, one per line, giving the break as `คริสต-จักร`, the joined word, how often the print breaks it, how often the word occurs unbroken elsewhere in the book, the first page it appears on, and a confidence note. Converting a row to an entry is mechanical: `คริสต-จักร` becomes `(word: "คริสตจักร", parts: ("คริสต", "จักร"))`.

Only 17 of the 133 are already in SJ and 5 in SC, so this roughly doubles SC's dictionary.

Two things need judgment. 125 rows are confirmed by the word appearing unbroken elsewhere in the book, but eight occur once only and their boundary was supplied by a reader rather than by evidence: อาชญา-กรรม, นักขัต-ฤกษ์, คริสตธรรม-กิตติคุณ, อสังหา-ริมทรัพย์, วิทเทม-บาก, พระราช-ชนนี, กรีน-แลนด์ and คอนเนต-ทิกัต. Those eight want a Thai reader before they go in. And the existing entries often break a word into every syllable, as `("พระ", "วิญ", "ญาณ", "บริ", "สุทธิ์")`, where these rows give a single morpheme boundary; settle whether the two styles coexist or whether the new rows should be broken further.

The larger question the quest should answer is whether the two projects keep separate dictionaries at all. Hyphenation is a fact about Thai words rather than about a book, so a shared file with each project importing it would stop SC and SJ diverging, and would give SC the benefit of SJ's 457 entries at once.

Order matters here. SC goes to print first and has a worktree already started, so SC is where the work lands and is proved. SJ has the larger dictionary and is the better source to merge from.

Detail: none written; this entry is the whole brief. `gc_th_hyphens.py` in `th/GC/04_assets/scripts/` is what produced the file and shows how each boundary was decided. Small if the two dictionaries stay separate, medium if they are merged.

## 17. Rebuild the SC break dictionary after the SC09–SC13 qa2 and qa3 rounds

th/SC/04_assets/template/dictionary.typ is stale against th/assets/typeset/thai-breaks.txt and the SC chapters as they now stand, so the resolution sheet of every SC round prints a FAIL line for it. The translator ruled that it is rebuilt once the qa2 and qa3 rounds of SC09 to SC13 are done, with python3 th/assets/scripts/build_breaks.py --book SC. Until then the sheet's stale-dictionary line and the rebuild in the check step, th/SC/CLAUDE.md 5.B, are left alone and reported as this entry.

Detail: this entry. Small.

## 18. Retire the temporary claude.ai reading page

The translator reads SC01 to SC08 for flow on a private claude.ai page until the proofreader site carries his reading: https://claude.ai/artifact/2V3onQqicn2FdzgPvNnMvG. His notes, his place in each chapter and his finished marks are kept in that page's own database, in the collections notes, progress and chapters, and Claude reads them with the ArtifactData tool. th/SC/04_assets/scripts/sc_read_page.py on SC-read rebuilds the page. The translator reads SC01 to SC08 on it and SC09 onward on the site. The SC-read session processes the page's notes. Once SC08 is processed, move every note on the page to the site, as the translator's comments, so that he keeps their history and the chapters show as already read: notes already processed go into an archived earlier round, kept but never marked again, and the rest arrive as open comments; his place and finished marks move too. Then delete the page and this entry.

Detail: this entry. Small.

## 19. Put the proofreader site live

The proofreader site gives each reader a personal link to read chapters and comment by paragraph; each reader sees only their own comments. It is built on SC-review under assets/review/. Going live on the droplet (Debian 13, Apache 2.4, Python 3.13.5) needs a DNS A record for review.laoegw.com, the commands in assets/review/deploy/DEPLOY.md and certbot for HTTPS. Claude walks the translator through each step. The translator ruled that the admin token is kept only in ~/.config/review/admin-token on his computer, where no Claude session can read it, so he runs the site's commands himself; at that step Claude reminds him of this and gives him the commands that set it up. He also ruled that admin commands reach the live site only through SSH, which review.py opens itself, and that Apache refuses /api/admin/ from the internet.

Detail: assets/review/README.md and assets/review/deploy/DEPLOY.md. Medium.

## 20. A readability round for the proofreader site

Reviewers who play an outside code reviewer meeting the code for the first time judge how the code under assets/review/ on SC-review is structured, how its functions and parameters are named, and how much documentation it carries, and propose changes that let such a reviewer follow it without confusion and without wading through more documentation than the code needs. The changes keep every behaviour and every test. The round also rewrites assets/review/README.md so that it says, in plain words, only what the translator needs to run and use the site; detail meant for agents moves to EXTENDING.md or into the code. The section "The translator's rulings" stays. The standard is the translator's: six months on, both he, with little coding experience, and a professional programmer read the code and understand it without decoding terse lines or wading through wordy ones, and neither finds the code rude. Up to 8 agents may work on this round. One more reviewer checks that nothing in the code base should stay private, such as names, addresses, tokens, paths on the translator's computer or notes meant for agents, before any of it is public. The round runs after the panel round and the remaining round 4 items.

Detail: this entry. Medium.

## 21. Grow the proofreader site into a translation suite

The translator's goal is one system for the whole translation. An editor and the translator work on one file over several turns: the editor comments, the translator processes the comments, both discuss them, and the translator then commits the result to a branch. The QA rounds and raw-translation rounds now run in this repository, such as th/SC's qa1 to qa3 and th/DA's drafting, also run in it. The proofreader site under assets/review/ on SC-review is the base, and every round of it is built so that these additions stay possible.

Detail: this entry, and the last line of "The translator's rulings" in assets/review/README.md. Large.

## 22. A wording round for the proofreader site

Reviewers who play first-time readers and an outside expert judge every word the site shows a reader or the translator, in English and Thai, and mark what is confusing, misleading or unlike what well-known sites say in the same situation, each with a proposal. The translator's note from his SC03 reading belongs to their brief: the reading page's note box asked "What is wrong, in a few words", which is not accurate when the note is simply a question, and wording that is less negative is wanted. The round runs before the translator shares reader links.

Detail: this entry. Medium.

## 23. Protection of the droplet against take-down floods

The translator chose DigitalOcean's firewall and the hardening of FIX2 in /home/ton/claude-sandbox/review-build-reports/90-takedown.md for now, and does not want a service that reads the sites' traffic. Two options stay open: Cloudflare kept in reserve, with its protection switched on only during a flood, and the proofreading site on a droplet of its own. A further study, 95-takedown-private.md, weighs protection that reads no traffic.

The translator set these aside until SC is in production: moving www.laoegw.com to its own small server at OVHcloud, a GitHub Pages copy, or a pass-through server of his own (95-takedown-private.md item 2); whether to move laoegw.com's DNS to Cloudflare with its protection off (item 4); and setting SSH's PermitRootLogin to no, since SSH passwords are already off. He ruled that www.laoegw.com serves its Lao font itself instead of loading it from Google (item 7), a change for the GC website's worktree, ~/claude-sandbox/wt-GC-website.

Detail: 90-takedown.md and 95-takedown-private.md in /home/ton/claude-sandbox/review-build-reports/. Medium.

## 24. Move the proofreader site into its own repository

The translator ruled that assets/review/ leaves the translation repository after the readability round of entry 20. The translation repository, bountonw/translate, is public, so the branch SC-review is never pushed to it. Open choices: a private GitHub repository (recommended), a public one or a self-hosted Forgejo; a fresh first commit from git archive (recommended) or the old history carried across. Before the move: a private backup repository, review-site-backup; the Kingston USB disk, which did not mount, checked with lsblk -f. With the move: review.py reads the translation repository from REVIEW_REPO, DEPLOY.md's rsync lines leave out .git, .github and .claude, tests run on GitHub at every push, and assets/read-through.md names the new folder.

Detail: /home/ton/claude-sandbox/review-build-reports/91-repo-hosting.md and 88-privacy.md. Medium.

## 25. Where the mail-check reports for review.laoegw.com go

The DMARC record of the site's mail can ask receiving mail servers for daily reports on the mail sent as review.laoegw.com. Such reports reach only an address under laoegw.com, and they arrive as one file a day from each large provider. The translator decides which address receives them, how they are kept out of his inbox, and how they are read. Until then the record carries no report address.

Detail: /home/ton/claude-sandbox/review-build-reports/100-runbook-check.md item 12. Small.

## 26. Questions from the translator to chosen editors and reviewers

The translator puts a question on chosen paragraphs to one editor, chosen readers or a group, open or as a poll; the editor sees those paragraphs with their context and answers; the two discuss until the translator closes the question; the answers reach the triage of assets/read-through.md. The translator ruled that it is built after round 4c, from a study.

Detail: /home/ton/claude-sandbox/review-build-reports/101-editor-questions-study.md, 97-direction-review.md item 5 and 98-check-and-premortem.md item 15. Medium.

## 27. Mail in each reader's language, and the reader's choice of how to be contacted

Each language of the proofreader site gets its own mail words and its own sender name, and each reader chooses in the settings how the site contacts them. The translator ruled it a future plan, worked on when other work is done or tokens are free at the end of a week.

Detail: /home/ton/claude-sandbox/review-build-reports/110-lao-fb-on-the-site.md on the mail words and the sender name. Medium.

## 28. Prepare SJ and PP for the proofreader site

SJ and PP are reviewed on the site once SC is done. Each book's preparation runs in its own worktree. SJ needs paragraph tags and English files in its sources and no new site code; PP needs one round of work on the publishing step and source corrections.

Detail: /home/ton/claude-sandbox/review-build-reports/109-sj-pp-on-the-site.md. Medium.
