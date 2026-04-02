# Translation Profile: Ellen G. White Writings

<!-- STRUCTURAL NOTE: Split into three parts. Part 1 is language-agnostic philosophy. Part 2 is Lao-specific. Part 3 is a Thai placeholder for future profiling. When the AI translator receives this profile, it should apply Part 1 + the relevant Part 2 or 3. -->

# Part 1: Universal Translation Philosophy

These rules apply regardless of target language.

## 1. Tone & Register

* **Dismantle Victorian Syntax:** Restructure convoluted 19th-century sentence patterns into clear, direct prose. The priority is clarity and readability, not preserving archaic English structure.
* **Use Reverent Language for Deity:** Employ formal ecclesiastical terminology appropriate to the target language's Christian tradition.
* **Use Degrading Language for Satan/Demons:** Use the target language's lowest-register pronoun or equivalent (animal/object class) when referring to Satan, Lucifer, or evil spirits. Never use polite or human-register pronouns for them. This applies regardless of narrative timeframe — even when describing Lucifer's pre-fall glory, use the degrading pronoun.
* **Retain Effective Rhetoric:** If a complex rhetorical structure from the English translates naturally into the target language without awkward phrasing, keep it. Never force the target language into unnatural shapes to mimic English rhetoric.
* **Eliminate First-Person Plural Bias:** When the English "we," "our," or "us" reflects a Western or American perspective, replace it with language appropriate to the universal reader (e.g., "our fathers" → the target-language equivalent of "America's pioneer generation"; "the world is no more ready" → address the global readership directly).

## 2. Syntactic Strategy

* **Apply Dynamic Equivalence:** Freely restructure, split, or combine sentences to favor natural target-language narrative flow. There is no requirement for 1:1 sentence correspondence with the English.
* **Evaluate Passives Contextually:** Do not default to either active or passive. If the agent is known and an active sentence is clearer, convert to active. If a passive construction is more natural in the target language for that context, keep it passive.
* **Eliminate Em-Dashes:** Replace em-dashes with conjunctions, relative clauses, or full sentence breaks. Restructure the logic so that an em-dash becomes unnecessary.
* **Never Split Paragraphs:** Maintain the exact paragraph block structure of the source text.
* **Use Numbered Lists for Complex Enumerations:** When the source contains a dense list embedded in prose, convert to a numbered list if it aids comprehension.
* **Unpack Dense Appositive Chains:** When the English stacks multiple appositives or parenthetical qualifiers into a single sentence, break them into separate clauses or sentences in the target language.
* **Use Numbered Decomposition for Parallel Elements:** When the source text discusses multiple prophetic passages, types, or arguments that point to the same event, the translator may organize them into a numbered list within the paragraph for clarity.

## 3. Contextual Clarification Strategy

When the English text contains ambiguous pronouns, implicit metaphors, or culture-specific perspectives, choose the lightest intervention that makes the meaning clear:

1. **Inline Adaptation (default):** Translate the intended meaning directly if it flows naturally and maintains readability (e.g., "our fathers" → the target-language equivalent of "America's pioneer generation").
2. **Bracketed Clarification:** Use brackets `[ ]` for brief inline context when a direct translation would obscure the original noun but the reader needs immediate help (e.g., `[referring to the Pope]`).
3. **Footnote:** Use footnotes for longer historical context, difficult concepts, or where any inline addition would disrupt narrative flow. (See §4.C for footnote types.)

## 4. Citation & Footnote Protocol

### 4.A. Biblical Citations

* **Hunt for Implicit Quotes:** Identify implicit biblical quotations or uncited KJV references in the English and provide the explicit chapter and verse in the target text.
* **Citation Format:** Place citations in parentheses at the end of the sentence or quote: `(Book Chapter:Verse Version)`. For implicit allusions, prefix with the target-language equivalent of "See": e.g., `(ເບິ່ງ Book Chapter:Verse)`.
* **Default Bible Version Rule:** Each book project declares a default Bible version. Omit the version abbreviation when quoting from the default version.
* **Version Selection:** When a non-default version is needed, select the target-language translation (checking standard digital sources such as bible.com) that best conveys the theological point without introducing side issues. Exclude archaic/obsolete versions unless no modern alternative captures the meaning. The translator may also use versions that are not digitized (e.g., physical books in the translator's possession); the AI translator should treat these version labels as authoritative when they appear in the reference translation.
* **Adaptation Label:** When a verse is adapted (not quoted verbatim) from a non-default version, mark it with the target-language equivalent of "adapted from [Version]" — e.g., `(ດັດແປງຈາກສະບັບ TKJV)`.
* **Source-Language Notes:** When a translation point depends on the original biblical language, note this inline — e.g., `(ແປຈາກພາສາກຣີກ)` ("translated from Greek").
* **Direct Translation from Original Languages:** When no existing target-language version conveys the necessary meaning, the translator may translate directly from the original biblical language (e.g., Hebrew, Greek) or from the KJV. Label such verses with `(ແປຈາກສະບັບ KJV)`.
* **Convert Poetry to Prose:** Format quoted biblical poetry or prophecy as standard prose blocks. Remove original stanza line breaks.
* **Inline Cross-References:** Use `(ເບິ່ງ Book Chapter:Verse)` for all cross-references. Do not use ອ່ານ in this context.

### 4.B. Non-Biblical Citations & References

* **Convert Inline Book References to Footnotes:** When the English text cites a book, author, or document inline (e.g., `—William Tyndale, Preface...`), remove it from the narrative and convert it to a footnote. Use the target-language footnote format (`.md` or `.typ` as appropriate).
* **Footnote Format for Book References:** Author surname (transliterated), book title (italicized), volume and chapter. E.g., `ໄວລີ, ເຫຼັ້ມ 16, ບົດ 1.` On first occurrence of a *specific work* in a chapter, provide the full transliterated book title. E.g., `ໂດບິນເຍ, *ປະຫວັດການປະຕິຮູບສາສະໜາໃນເອີຣົບໃນສະໄໝຂອງຄາວິນ*, ເຫຼັ້ມ 2, ບົດ 16.`
* **Volume Before Chapter:** Always list volume (ເຫຼັ້ມ) before chapter (ບົດ) in footnote citations. E.g., `ເຫຼັ້ມ 13, ບົດ 1.` — never the reverse order.
* **Edition Info:** When the English specifies an edition (e.g., "London ed."), transliterate it descriptively: `ສະບັບຕີພິມທີ່ລອນດອນ`.
* **Distinguish Multiple Works by Same Author:** When an author has multiple works cited (e.g., D'Aubigné's 16th-century history vs. Calvin-era history), provide the full transliterated title on first occurrence of *each distinct work* in a chapter.
* **"Ibid." Handling:** When the source uses "Ibid.," use `*ອ້າງອີງຈາກທີ່ດຽວກັນ*` (italicized) as the Lao equivalent. Follow with volume/chapter/page info if the source specifies a different location. E.g., `*ອ້າງອີງຈາກທີ່ດຽວກັນ*, ເຫຼັ້ມ 3, ບົດ 7.` or `*ອ້າງອີງຈາກທີ່ດຽວກັນ*, ໜ້າ 389.` or simply `*ອ້າງອີງຈາກທີ່ດຽວກັນ*.`
* **Omit Appendix References:** Remove any references directing the reader to an Appendix (e.g., "(See Appendix.)").
* **Recover Appendix Content Selectively:** Evaluate each Appendix reference: if the content is relevant and easy to handle, create a substantive footnote. Otherwise, silently delete. This is a judgment call, not a blanket rule. E.g., the Tertullian reference at GC 240.3 is recovered as a full footnote: `ສາມາດສຶກສາເພີ່ມເຕີມໄດ້ຈາກ *ບົດຖະແຫຼງຂອງເທີທູລຽນ* (Tertullian's Apology) ວັກ 50.`
* **Correct Source Attribution Errors:** When the English source or its cited secondary source contains a known factual error (e.g., misattributed quotation, wrong pope), add a footnote correcting the record. E.g., at GC 565.2, the source quotes Josiah Strong who incorrectly attributes a statement to Pius IX; the footnote corrects this to Gregory XVI with the actual date (August 15, 1832).
* **Historical-Dating Footnotes for Outdated Claims:** When the source text contains a bracketed editorial note like `[Published in 1888 and 1911. See Appendix.]`, convert it to a footnote explaining the historical context for today's reader. E.g., at GC 565.3, the claim that Catholics are "not allowed access to His word" receives a footnote explaining Vatican II's policy change (1962–1965).

### 4.C. Explanatory Footnotes

* **Add Historical-Context Footnotes:** If the English text makes a historical claim that has changed significantly in the modern era, or cites a decree/law, add a footnote clarifying the historical context for today's reader. (E.g., Constantine's Sunday law receives a footnote with the full decree text and source.)
* **Royal-Vocabulary Footnotes:** When a royal-register word (ຣາຊາສັບ) appears for the first time, add a brief footnote defining it. E.g., `*ພຣະໂອດ*: ຣາຊາສັບ ໝາຍເຖິງປາກ.`
* **Cross-Reference Footnotes:** When the English text includes a parenthetical Bible reference that is not a direct quotation, convert it to a footnote with `ເບິ່ງ `. E.g., `[^2]: ເບິ່ງ 1 ຂ່າວຄາວ 28:12, 19.`
* **Cross-Chapter References:** When the translator cross-references another chapter in the same book, use `ເບິ່ງ ບົດທີ [N].`
* **Doctrinal-Explanation Footnotes:** When the English mentions a doctrine or practice unfamiliar to the target audience, add a brief footnote explaining it. E.g., purgatory explained at GC 248.3: `ຄຣິສຕະຈັກກາໂຕລິກສອນວ່າ…`
* **Repeat Essential Footnotes per Chapter:** Footnotes that provide vital context (e.g., the day-year prophetic principle: `ໜຶ່ງວັນແຫ່ງຄຳພະຍາກອນເທົ່າກັບໜຶ່ງປີ. ເບິ່ງ ຈົດບັນຊີ 14:34; ເອເຊກຽນ 4:6.`) should be repeated each time the concept is contextually relevant in a new chapter, not just once per book.
* **Vocabulary Footnotes:** When the chosen Bible version uses a word that many readers will not understand, add a brief footnote defining it. E.g., a footnote defining ຖະຫຼຸງ ("refine/smelt") when the word appears in a quoted verse.
* **Inline Clarification Footnotes:** Use footnotes to clarify terms, currency, people, or places that the target reader may not recognize. E.g., `ຫຼຽນມາກເປັນສະກຸນເງິນຊະນິດໜຶ່ງ.` (explaining "marks"), `ໝາຍເຖິງສັນຕະປາປາ.` (clarifying an ambiguous pronoun), `ຫໍຄອຍທີ່ໃຊ້ຂັງລູກສິດຂອງທ່ານໄວຄຼິບ.` (explaining "Lollard tower").
* **Metaphor-Explanation Footnotes:** When the English uses a figurative title or metaphor that may not be obvious to the target reader, add a brief footnote. E.g., "Sun of Righteousness" → footnote: `ໝາຍເຖິງພຣະຄຣິສ.` (GC 475.3).
* **Theological-Identity Footnotes:** When a biblical figure's identity is ambiguous or theologically significant (e.g., "the Angel of the covenant" = the pre-incarnate Christ), add a brief footnote clarifying. E.g., at GC 616.3: `ໃນບົດນີ້…ທູດແຫ່ງພັນທະສັນຍາ ຄືພຣະຄຣິສກ່ອນທີ່ພຣະອົງສະເດັດມາບັງເກີດເປັນມະນຸດ.`
* **Narrative-Structure Footnotes:** When the author's literary technique (e.g., flashback, chronological reordering) might confuse the reader, add a brief footnote orienting the reader. E.g., at GC 653.1: footnote explaining the author returns to describe events from the perspective of the lost after narrating the ascension of the saved.
* **Bible-Reading-Instruction Footnote (book opener only):** On the very first citation of the book, add a footnote explaining how to read the citation format aloud in the target language. E.g., `ອ່ານວ່າ ລູກາ ບົດທີສິບເກົ້າ ຂໍ້ສີ່ສິບສອງເຖິງສີ່ສິບສີ່.` This is a one-time addition, not repeated per chapter.
* **"Consideration List" for Rare Words:** Do not add translation footnotes for vocabulary inside the translation block itself. Instead, list rare or potentially unknown words at the end of the section for the editor to decide on.

## 5. Formatting & Tags

* **Preserve End Tags:** Place the paragraph tag at the end of each paragraph in the format: `{<book code> ###.#}`.
* **Pre-Tag Format by File Type:**
  * `.md` files: `## {<book code> ###.#}`
  * `.typ` files: `// {<book code> ###.#}`
* **Sub-Headers:** If the source or reference translation contains sub-headers, preserve them as-is unless there is an obvious error. Sub-header creation is a separate editorial process and should not be handled during translation. When translating a new chapter from scratch, the translator may place `###` sub-headers at natural narrative shifts as a draft, but these are subject to later editorial review.
* **Keep Headers Short:** Headers should be brief and impactful, not long descriptive sentences.
* **Footnote Syntax:** Footnote format depends on the target file type (`.md` uses `[^N]` / `[^N]: text`; `.typ` uses Typst footnote syntax). Number footnotes per chapter starting from 1. Place footnote definitions immediately after the paragraph's end tag, separated by a blank line, for `.md` files. Place inline for `.typ` files.
* **Ignore Pipeline Markup:** Do not produce LaTeX or typesetting codes (e.g., `\\s`, `\\p{-200}`, `\cs{}`, `\lw{}`, `{\;}`) in the translation output. These are added by a separate processing pipeline. When editing an existing file that already contains such markup, reproduce it faithfully without commenting on it, unless it is obviously wrong.
* **Chapter Titles May Be Adapted:** The Lao chapter title does not need to be a literal translation of the English chapter title. The translator may create a title that better captures the chapter's content for the target reader, especially when the English title is vague or euphemistic. E.g., English "The First Great Deception" → Lao ຄວາມຈິງເລື່ອງຄວາມຕາຍ ("The Truth About Death").

## 6. Proper Noun Conventions

* **Transliterate Historical Names and Places:** Render European historical names and geographical locations phonetically into the target language's script.
* **First-Occurrence Parenthetical:** On first use in a chapter or major section, provide the English name in parentheses after the transliteration.
* **Subsequent Mentions:** Use only the transliterated form after first occurrence within the same chapter.
* **Full Name on First Mention:** For persons, provide the full name on first mention even if the English abbreviates. E.g., English "Cestius" → `ໄກອຸສ ເຊຕຽວ ກາລຸສ (Gaius Cestius Gallus)` on first use, then `ແມ່ທັບເຊຕຽວ` thereafter.
* **Titles as Identifiers:** After introducing a person, the translator may use a descriptive title instead of repeating the name: e.g., `ແມ່ທັບຕີໂຕ` ("General Titus") rather than just the transliterated name.
* **Biblical Figure Title Conventions:** Use culturally appropriate titles for well-known biblical figures. E.g., `ອາຈານໂປໂລ` ("Teacher Paul"), `ກະສັດດາວິດ` ("King David"), `ກະສັດໂຊໂລໂມນ` ("King Solomon"), `ຜູ້ເຜີຍພຣະທຳດານີເອນ` ("Prophet Daniel"). These titles may alternate with the plain name or with `ອັກຄະສາວົກ` ("Apostle") depending on context.

---

# Part 2: Lao-Specific Rules (ພາສາລາວ)

Apply these rules in addition to Part 1 when the target language is Lao.

## 7. Lao Register & Vocabulary

* **Royal Vocabulary (ຣາຊາສັບ) for Deity Only:** Apply terms such as ສະເດັດ, ພຣະໂອດ, ພຣະຫັດ, ສິ້ນພຣະຊົນ, ປະທັບ, ສະເຫວີຍ, ພຣະສຸຣະສຽງ, ນ້ຳພຣະໄທ, ພໍພຣະໄທ, ພຣະໄທ, ພຣະພັກ, ພຣະບາດ, ພຣະປະສົງ, ພຣະປັນຍາ exclusively to God and Christ. Never apply them to human royalty or any other figure.
* **Pronoun for Satan/Demons:** Always use ມັນ. This applies to all forms: ຊາຕານ, ມານຊາຕານ, ພະຍາມານ, ຜີສາດມານຮ້າຍ, ຜີມານ, ລູຊີເຟີ. Use ມັນ even when narrating Lucifer's pre-fall status and glory.
* **Honorific for Major Figures (ເພິ່ນ):** Use ເພິ່ນ for popes, emperors, kings, generals, major reformers, prophets, apostles, and other persons of significant narrative prominence, when speaking of them in a neutral narrative voice. This is distinct from the royal vocabulary reserved for deity.
* **Standard Pronoun for Minor or Negative Figures (ລາວ):** Use ລາວ for minor narrative figures, persons of humble social standing, and antagonists or morally negative characters (e.g., traitors, unnamed persons, minor functionaries).
* **ພຣະ- Prefix:** Use ພຣະ as a prefix for sacred objects and concepts associated with deity: ພຣະວິຫານ (temple), ພຣະຄຳພີ (Bible/Scripture), ພຣະຄຣິສ (Christ), ພຣະບັນຍັດ (commandment), ພຣະສັນຍາ (promise/covenant), ພຣະໂລຫິດ (blood of Christ), ພຣະຄຸນ (grace), ພຣະເມດຕາ (divine mercy), ພຣະຣາຊບັນຍັດ (royal law, specifically for James 2:8), ພຣະຣາຊບັນລັງ (throne of God), ພຣະເມສານ້ອຍ (the Lamb — salvific/Revelation context).
* **Lao Idioms for Theological Concepts:** Use natural Lao idioms when they capture the theological meaning vividly. E.g., "conversion/repentance" may be rendered as ການຖິ້ມໃຈເກົ່າເອົາໃຈໃໝ່ ("throw away the old heart, take a new heart") or ການປະໃຈເກົ່າເອົາໃຈໃໝ່ alongside the more literal ການກັບໃຈໃໝ່. Choose whichever fits the tone of the passage.

## 8. Lao Orthography

* **Ligatures:** Always use ຫຼ, ໜ, ໝ. Never use ຫລ, ຫນ, ຫມ.
* **"ຣ" vs "ລ" in Religious/Pali/Sanskrit Roots:** Use ຣ for religious and formal roots per the glossary below. Exceptions are explicitly mapped.

## 9. Lao Theological & Historical Term Glossary

<!-- This glossary grows as new text is profiled. -->

| English | Lao | Notes |
|---|---|---|
| The Reformation | ການປະຕິຮູບສາສະໜາ | |
| Indulgences | ໃບລ້າງບາບ | |
| Purgatory | ແດນຊຳລະ | |
| Heretics | ພວກນອກຮີດ | |
| Papacy / Popery | ລະບອບສັນຕະປາປາ / ຝ່າຍສັນຕະປາປາ | |
| Reign of Terror | ສະໄໝທີ່ຄວາມໂຫດຫ້ຽມສະຫຍອງຂວັນຄອງເມືອງ | |
| Sanctuary | ສະຖານບໍຣິສຸດ / ສະຖານນະມັດສະການ | |
| Investigative Judgment | ການພິພາກສາແບບສືບສວນ | |
| Day of Atonement | ວັນລຶບລ້າງບາບອັນຍິ່ງໃຫຍ່ | |
| Scapegoat | ແບ້ຮັບບາບ | |
| Spiritualism | ລັດທິຕິດຕໍ່ກັບວິນຍານ | |
| Mediums / Spirit channelers | ພວກໝໍຜີ ແລະ ນາງທຽມ | |
| Universalism | ຄວາມເຊື່ອທີ່ວ່າມະນຸດທຸກຄົນຈະລອດພົ້ນ | |
| Immortal soul | ຈິດວິນຍານເປັນອະມະຕະ | |
| Second Advent | ການສະເດັດມາຄັ້ງທີສອງຂອງພຣະຄຣິສ | |
| Waldenses / Vaudois | ຊາວໂວດົວ | Used interchangeably |
| Sabbath | ວັນສະບາໂຕ | |
| Sunday (as false sabbath) | ວັນອາທິດ | |
| Sunday sacredness | ຄວາມສັກສິດຂອງວັນອາທິດ | [tentative] |
| Roman Catholic Church | ຄຣິສຕະຈັກໂຣມັນກາໂຕລິກ / ນິກາຍກາໂຕລິກ | |
| Protestantism / Protestants | ນິກາຍໂປຣແຕັສຕັງ / ພວກໂປຣແຕັສຕັງ | |
| Protestant | ໂປຣແຕັສຕັງ | Uses ຣ |
| Dark Ages | ຍຸກມືດ / ສະໄໝຍຸກມືດ | |
| Paganism | ລັດທິຂາບໄຫວ້ຮູບເຄົາລົບ | Descriptive rendering |
| Apostasy | ການພັດຫຼົງໄປຈາກຄວາມເຊື່ອ | |
| Apostle(s) | ອັກຄະສາວົກ | |
| Passover | ປັດສະຄາ / ເທດສະການປັດສະຄາ | |
| Feast of Tabernacles | ເທດສະການ "ປຸກຕູບຢູ່" | Quotes around Lao term |
| Catacombs | ຄອງອຸບມຸງ | |
| Inquisition | ສານຄະດີນອກຮີດ | |
| Idol worship | ການຂາບໄຫວ້ຮູບເຄົາລົບ | |
| Mercy seat | ພຣະທີ່ນັ່ງແຫ່ງກະລຸນາ / ພຣະທີ່ນັ່ງກະລຸນາ | |
| Gospel | ຂ່າວປະເສີດ | |
| Bishop of Rome | ຜູ້ນຳຄຣິສຕະຈັກໃນນະຄອນໂຣມ | Descriptive |
| Dragon (Rev.) | ພະຍານາກ | |
| Beast (Rev.) | ສັດຮ້າຍ | |
| Second death | ຄວາມຕາຍຄັ້ງທີສອງ | |
| Mendicant friars | ພວກພຣະກາໂຕລິກ | Generic "Catholics" used |
| Lollards | ໂລລາດ | Wycliffe's followers |
| Hussites | ຊາວຮັສ | Huss's followers |
| Crusade (religious war) | ສົງຄາມສາສະໜາ | |
| Council (of the church) | ສະພາຄຣິສຕະຈັກ / ປະຊຸມສະພາ | |
| 95 Theses | ຄຳປະທ້ວງ 95 ຂໍ້ | |
| Diet (assembly) | ສະພາ | E.g., Diet of Worms |
| Mass (Catholic) | ພິທີສິນລະນຶກ | [tentative] |
| Confession of faith | ຄຳປະກາດແຫ່ງຄວາມເຊື່ອ | |
| Excommunication | ການຕັດຊື່ອອກຈາກຄຣິສຕະຈັກ | Descriptive |
| Safe-conduct | ໃບຮັບຮອງຄວາມປອດໄພ | |
| Anathema | ຄຳສາບແຊ່ງ | |
| Cardinal | ພຣະຄາດີນັນ | |
| Satan / the Devil | ຊາຕານ / ມານຊາຕານ / ພະຍາມານ / ຜີສາດມານຮ້າຍ | Always ມັນ |
| Jesuits | ຄະນະສົງເຢຊຸອິດ / ເຢຊຸອິດ | |
| Transubstantiation | (describe, do not transliterate) | |
| Thirty Years' War | ສົງຄາມ 30 ປີ | |
| Goddess of Reason | ເທບທິດາແຫ່ງການໃຊ້ເຫດຜົນ | |
| Huguenots | ຮູເກີໂນ | |
| Puritans | ປູຣິຕັນ | [tentative] |
| Methodists / Methodist Connection | ຊາວເມທໍດິສ / ເຄືອຂ່າຍກຸ່ມເມທໍດິສ | |
| Antinomianism | (describe: teaching that God's law is abolished) | |
| Quakers / Quakerism | ຄະນະຄະເວເກີ | [tentative] |
| Albigenses | ຊາວອັນບີເຈນ | |
| Moravians | ຊາວໂມເຣເວຍ | |
| Baptism | ບັບຕິສະມາ | |
| Rebaptism | ການຮັບບັບຕິສະມາໃໝ່ | |
| "The end justifies the means" | ການບັນລຸເປົ້າໝາຍລ້ວນແຕ່ສ້າງຄວາມຊອບທຳໃຫ້ແກ່ວິທີການ | Jesuit principle |
| Adventists | ແອັດເວັນຕິສ | |
| Midnight Cry | ສຽງຮ້ອງຍາມທ່ຽງຄືນ | |
| Cleansing of the sanctuary | ການຊຳລະສະຖານບໍຣິສຸດ | |
| Cherubim | ເຄຣຸບ | |
| Seraphim | ເສຣາຟິມ | |
| High Priest | ມະຫາປະໂຣຫິດ | |
| Priest | ປະໂຣຫິດ | |
| Holy Communion | ມະຫາສະໜິດ | [tentative] |
| First fruits (wave sheaf) | ຟ່ອນເຂົ້າຜົນທຳອິດ / ຜົນແລກ | |
| Mark of the beast | ເຄື່ອງໝາຍຂອງສັດຮ້າຍ | |
| Image to the beast | ຮູບຈຳລອງຂອງສັດຮ້າຍ | |
| Rationalism | ລັດທິເຫດຜົນນິຍົມ | |
| Sacramentarianism | ການນິຍົມພິທີກຳ | [tentative] |
| Presbyterian | ເປຣສະບິເທີຣຽນ | [tentative] |
| Lutheran | ລູເທີແຣນ | |
| Sanctification | ການຊຳລະໃຫ້ບໍຣິສຸດ | |
| Conversion (spiritual) | ການກັບໃຈໃໝ່ / ການຖິ້ມໃຈເກົ່າເອົາໃຈໃໝ່ | Lao idiom alternates with literal |
| New birth | ການບັງເກີດໃໝ່ | |
| Mediator | ຜູ້ເປັນກາງ (ລະຫວ່າງພຣະເຈົ້າກັບມະນຸດ) | Descriptive |
| Advocate / Intercessor | ຜູ້ວິງວອນ / ຜູ້ອ້ອນວອນ / ຜູ້ແກ້ຄວາມ | Context determines choice |
| Covering cherub | ເຄຣຸບຜູ້ພິທັກ | |
| Book of life | ທະບຽນແຫ່ງຊີວິດ / ໜັງສືແຫ່ງຊີວິດ | |
| Book of remembrance | ໜັງສືທີ່ລະລຶກ | |
| Ancient of Days | ອົງຜູ້ດຳລົງຊີວິດຢັ້ງຢືນຕະຫຼອດການ / ຜູ້ດຳລົງຢູ່ຕັ້ງແຕ່ດຶກດຳບັນ | [tentative] Varies by Bible version quoted |
| Decalogue / Ten Commandments | ພຣະບັນຍັດສິບປະການ | |
| Royal law (James 2:8) | ພຣະຣາຊບັນຍັດ | Uses ຣາຊ prefix |
| Counterfeit | ຂອງປອມ / ການຟື້ນຟູປອມ | Context-dependent |
| Guardian angel | ທູດສະຫວັນຜູ້ປົກປ້ອງ | [tentative] |
| Eternal torment / Hell | ການທໍລະມານຕະຫຼອດນິຣັນ / ຂຸມນະຣົກ | |
| Immortality of the soul (doctrine) | ຄວາມເຊື່ອວ່າຈິດວິນຍານເປັນອະມະຕະ | Also: ດວງວິນຍານທີ່ອະມະຕະ |
| Consciousness in death | ຄົນຍັງມີສະຕິຮູ້ສຶກຕົວຫຼັງຈາກຕາຍ | Descriptive |
| Familiar spirits | ຄົນຊົງເຈົ້າເຂົ້າຜີ | GC 556.2 |
| Tree of life | ຕົ້ນໄມ້ແຫ່ງຊີວິດ | |
| Resurrection | ການຟື້ນຄືນຊີບ / ການເປັນຄືນມາຈາກຕາຍ | |
| Lamb (Rev./salvific) | ພຣະເມສານ້ອຍ | [tentative] |
| Sheol / Grave (realm of dead) | ແດນມໍຣະນາ | |
| Papal infallibility | (describe: claiming the church never erred and never will) | |
| Encyclical letter | ຈົດໝາຍອະທິບາຍຄວາມເຊື່ອ | [tentative] |
| Vicar of Christ | ຜູ້ແທນຂອງພຣະຄຣິສ | [tentative] |
| Monastery / Convent | ສຳນັກສົງ / ສຳນັກແມ່ຊີ | [tentative] |
| Stake (execution) | ຫຼັກປະຫານ | [tentative] |
| Mark of the beast | ເຄື່ອງໝາຍຂອງສັດຮ້າຍ | |
| Seal of God | ຕາປະທັບຂອງພຣະເຈົ້າ | |
| Latter rain | ຝົນປາຍລະດູ | Prophetic symbol |
| Former rain | ຝົນຕົ້ນລະດູ | Prophetic symbol |
| Time of trouble | ເວລາແຫ່ງຄວາມທຸກຍາກລຳບາກ | Daniel 12:1 |
| Jacob's trouble | ເວລາແຫ່ງຄວາມທຸກຍາກຂອງຢາໂຄບ | Jeremiah 30:7 [tentative] |
| Seven last plagues | ໄພພິບັດ (7 ຢ່າງສຸດທ້າຍ) | [tentative] |
| Angel of the covenant | ທູດແຫ່ງພັນທະສັນຍາ | = pre-incarnate Christ |
| New Jerusalem | ນະຄອນເຢຣູຊາເລັມໃໝ່ | |
| Holy City | ນະຄອນບໍຣິສຸດ | |
| New earth | ໂລກທີ່ໄດ້ຮັບການສ້າງຂຶ້ນໃໝ່ | [tentative] |
| Close of probation | ໂອກາດສິ້ນສຸດ / ເວລາແຫ່ງໂອກາດສິ້ນສຸດ | [tentative] |
| Great controversy | ການຕໍ່ສູ້ມະຫາກາບ / ສົງຄາມການຕໍ່ສູ້ | |

## 10. Lao Spelling Glossary

| Word | Correct | Incorrect | Notes |
|---|---|---|---|
| Holy / Pure | ບໍຣິສຸດ | ບໍລິສຸດ | ຣ root |
| Epidemic / Plague | ໂຣກລະບາດ | ໂລກລະບາດ | ຣ root |
| Glory / Radiance | ສະຫງ່າຣາສີ | ສະຫງ່າລາສີ | ຣ root |
| Christian | ຄຣິສຕຽນ | ຄລິດສະຕຽນ / ຄິດສະຕຽນ | |
| Holy (prefix) | ພຣະ | ພະ | |
| Power / Authority | ຣິດອຳນາດ / ຣິດເດດ | ລິດອຳນາດ / ລິດເດດ | |
| Eternal | ນິຣັນ | ນິລັນ | |
| Israel | ອິດສະຣາເອນ | ອິດສະລາເອນ | |
| Heritage | ມໍລະດົກ | ມໍຣະດົກ | Exception: ລ |
| Miracle | ອັດສະຈັນ | ອັດສະຈັນຍ໌ | |
| Protestant | ໂປຣແຕັສຕັງ | ໂປລແຕັສຕັງ | ຣ root |
| Radiance (divine) | ຣັດສະໝີ | ລັດສະໝີ | ຣ root |
| Church (institution) | ຄຣິສຕະຈັກ | ຄລິສຕະຈັກ | |
| Christ | ພຣະຄຣິສ | ພຣະຄລິສ | |
| Royal vocabulary | ຣາຊາສັບ | ລາຊາສັບ | ຣ root |
| Sovereign power | ຣິດທານຸພາບ | ລິດທານຸພາບ | ຣ root |
| Complete / Perfect | ບໍຣິບູນ | ບໍລິບູນ | ຣ root |
| Realm of the dead | ແດນມໍຣະນາ | | ຣ root; used for Sheol/grave |

## 11. Lao Proper Noun Glossary

<!-- GC-specific. Proper nouns from other EGW books (PP, AA, MB, Ed, etc.) should be added in separate tables or merged as needed. -->

| English | Lao | Notes |
|---|---|---|
| Jerusalem | ເຢຣູຊາເລັມ | |
| Mount of Olives / Olivet | ພູເຂົາໝາກກອກເທດ | |
| Gethsemane | ເຄັດເຊມາເນ | |
| Calvary | ຄານວາຣີ | |
| Titus | ຕີໂຕ | Often: ແມ່ທັບຕີໂຕ |
| Josephus | ໂຢເຊຟັດ | |
| Cestius Gallus | ໄກອຸສ ເຊຕຽວ ກາລຸສ | Short: ແມ່ທັບເຊຕຽວ |
| Pella | ເປລາ | |
| Moriah | ໂມຣິຢາ | |
| Ornan | ອາໂຣນາ | |
| Nero | ເນໂຣ | |
| Constantine | ຄອນສະຕັນຕິນ | |
| Gregory VII | ເກຼັກກໍຣີທີ 7 | |
| Wycliffe | ໄວຄຼິບ | |
| Martin Luther | ມາຕິນ ລູເທີ | |
| Solomon | ໂຊໂລໂມນ | |
| David | ດາວິດ | |
| Nebuchadnezzar | ເນບູກາດເນັດຊາ | |
| Haggai | ຮັກກາຍ | |
| Isaac | ອີຊາກ | |
| Jacob | ຢາໂຄບ | |
| Herod | ເຮໂຣດ | + ມະຫາຣາດ for "the Great" |
| Milman | ມິນມານ | |
| Wylie | ໄວລີ | |
| Tertullian | ເທີທູລຽນ | |
| Liberalis | ລີເບຣາລິດ | |
| Perea | ເປເຣຍ | |
| Lutterworth | ລັດເຕີເວີດ | [tentative] |
| Oxford | ອັອກຟອດ | |
| John Huss | ຈອນ ຮັສ | Short: ຮັສ |
| Jerome (of Prague) | ເຈໂຣມ | |
| Bohemia | ໂບຮີເມຍ | |
| Prague | ປຣັກ | |
| Constance | ຄອນສະຕັນ | (the city) |
| Sigismund | ຊີກີມົງ | |
| Bethlehem Chapel | ໂບດເບັດເລເຮັມ | |
| Ziska | ຊິສກາ | [tentative] |
| Moravia | ໂມເຣເວຍ | |
| United Brethren | ກຸ່ມພີ່ນ້ອງຜູ້ເປັນໜຶ່ງດຽວ | Descriptive |
| Staupitz | ສະເຕົາພິດ | |
| Rome (city) | ນະຄອນໂຣມ | |
| Erfurt | ແອີຟຸດ / ເອີເຟີດ | Two forms observed |
| Wittenberg | ວິດເທນເບີກ / ວິດເທັນເບີກ | Two forms observed |
| Tetzel | ເທດເຊລ | [tentative] |
| Augsburg | ອອກເບີກ | |
| Worms | ວອມ / ເວີມ | Two forms observed |
| Saxony | ແຊັກຊັນນີ | |
| Netherlands | ເນເທີແລນ | |
| Spain | ແອັດສະປາຍ | |
| Zwingli | ສວິງລີ | Short: ອຸນຣິກ ສວິງລີ |
| Zurich | ຊູຣິກ | |
| Melanchthon | ເມລັງໂທນ | |
| D'Aubigné | ໂດບິນເຍ | Author citation |
| Bonnechose | ບອນໂຊດ | Author citation |
| Neander | ນຽນເດີ | Author citation |
| Foxe | ຟັອກ | Author citation |
| Lenfant | ລອງຟອງ | Author citation |
| Lefevre | ເລີເຟວ | French reformer |
| William Farel | ວິນລຽມ ແຟໂຣ | Short: ແຟໂຣ |
| John Calvin | ຈອນ ຄາວິນ | Short: ຄາວິນ |
| Olivetan | ໂອລີເວຕັນ | Calvin's cousin |
| Louis de Berquin | ຫຼຸຍສ໌ ແຫ່ງເບີຄວິນ | Short: ເບີຄວິນ |
| Beza | ເບຊາ | |
| Erasmus | ເອີຣັສມາສ | |
| Beda | ເບດາ | |
| Francis I | ຟຣານຊິສທີ 1 | King of France |
| Margaret (princess) | ມາກາເຣັດ | ເຈົ້າຍິງ |
| Meaux | ເມືອງໂມ | City |
| Paris | ນະຄອນປາຣີ | |
| France | ປະເທດຝຣັ່ງ | |
| Germany | ປະເທດເຢຍລະມັນ | |
| Switzerland | ສວິສເຊີແລນ | |
| Poitiers | ພົວເຈ | |
| Geneva | ນະຄອນເຈນີວາ | |
| Basel | ບາເຊັນ | [tentative] |
| Charles V | ຊານສ໌ທີ 5 | Emperor |
| Holland | ຮໍແລນ | |
| Menno Simons | ເມັນໂນ ຊີໂມນ | Short: ເມັນໂນ |
| Münster | ມຸນສະເຕີ | [tentative] |
| William of Orange | ວິນລຽມແຫ່ງອໍເຣນ | |
| Tausen | ທາວເຊັນ | Reformer of Denmark |
| Cologne | ໂຄໂລນ | |
| Denmark | ເດນມາກ | |
| Sweden | ສະວີເດັນ | |
| Olaf Petri | ໂອລັບ ເປຕຣີ | |
| Laurentius Petri | ໂລເຣັນທີອັດ ເປຕຣີ | |
| Orebro | ໂອເຣໂບ | |
| Cappel | ກາເປນ | Battle site |
| Oecolampadius | ເອໂກລຳພາດິອັດ | |
| Froment | ໂຟມົງ | |
| Morat | ໂມຣັດ | |
| Neuchatel | ນິວຊາແຕວ | |
| Philip II | ຟີລິບທີ 2 | |
| Louis XVI | ຫຼຸຍສ໌ທີ 16 | |
| Scandinavia | ສະແກນດິເນເວຍ | |
| Tyndale / William Tyndale | ທິນເດວ / ວິນລຽມ ທິນເດວ | |
| Latimer | ລາຕິເມີ | |
| Barnes | ບາເນດ | |
| Frith | ຟຣິດ | |
| Ridley | ຣິດລີ | |
| Cranmer | ເຄນເມີ | |
| Columba | ໂຄລຳບາ | |
| Scotland | ສະກັອດແລນ | |
| Hamilton | ແຮມິນຕັນ | |
| Wishart | ວີຊາດ | |
| John Knox | ຈອນ ນັອຄຊ໌ | |
| Mary (Queen of Scots) | ຣາຊິນີມາຣີ | |
| John Bunyan | ຈອນ ບັນຍັນ | |
| Bedford | ເບດຟອດ | |
| Baxter | ແບັກສະເຕີ | |
| Flavel | ຟຼາເວວ | |
| Alleine | ອາເລນ | |
| Whitefield | ວິດຟຽວ | |
| John Wesley | ຈອນ ເວສະລີ | Short: ເວສະລີ |
| Charles Wesley | ຊານສ໌ ເວສະລີ | |
| Savannah | ສະແວນນາ | |
| London | ລອນດອນ / ນະຄອນລອນດອນ | |
| Durham | ເດີຮາມ | |
| England | ອັງກິດ / ປະເທດອັງກິດ | |
| America | ອາເມຣິກາ | |
| Piedmont | ພີດມົງ | |
| Louis XV | ຫຼຸຍສ໌ທີ 15 | [tentative] |
| Voltaire | ໂວລແຕ | [tentative] |
| Walter Scott | ວອນເຕີ ສະກັອດ | Author citation |
| Anderson | ແອນເດີສັນ | Author citation |
| Martyn | ມາຕິນ | Author citation |
| Bancroft | ບານຄອຟ | [tentative] |
| Whitehead | ໄວເຮດ | Author citation |
| Robinson | ໂຣບິນສັນ | [tentative] |
| Roger Williams | ໂຣເຈີ ວິນລຽມ | [tentative] |
| William Miller | ວິນລຽມ ມິນເລີ | Short: ມິນເລີ |
| Lisbon | ລິສບອນ | [tentative] |
| Wolff / Joseph Wolff | ໂຈເຊັບ ວໍຟ໌ | Short: ວໍຟ໌ |
| Bengel | ເບນເກນ | |
| Gaussen | ໂກເຊັນ | |
| Lacunza | ລາຄູນຊາ | |
| Mourant Brock | ໂມຣານ ບຣອກ | |
| Robert Winter | ໂຣເບີດ ວິນເທີ | |
| Charles Fitch | ຊານສ໌ ຟິດ | |
| Artaxerxes | ອາກຕາເຊເຊັດ | |
| Finney | ຟິນນີ | [tentative] |
| Spurgeon | ສະເປີເຈນ | |
| Guthrie | ກຸດຣີ | |
| Hopkins | ຮົບກິນສ໌ | |
| Challoner | ຊານໂລເນີ | |
| Rollin | ໂຣລິນ | |
| Habakkuk | ຮາບາກຸກ | |
| Malachi | ມາລາກີ | |
| Würtemberg | ເວີດເທັມເບີກ | [tentative] |
| Bokhara | ບູຄາຣາ | [tentative] |
| Yemen | ເຢເມນ | |
| Tatary | ຕາຕາຣີ | [tentative] |
| Wales | ເວລສ໌ | [tentative] |
| Edward A. Park | ເອັດເວີດ ເອ. ພາກ | [tentative] GC 465.2 |
| Balaam | ບາລາອາມ | [tentative] GC 529.2 |
| Lucifer | ລູຊີເຟີ | Always ມັນ |
| Adam | ອາດາມ | ເພິ່ນ pronoun |
| Eve | ເອວາ | |
| Eden | ເອເດນ / ສວນເອເດນ | |
| Cain | ກາອິນ | |
| Abel | ອາເບັນ | [tentative] |
| Noah | ໂນອາ | |
| Lot | ໂລດ | [tentative] |
| Abraham | ອັບຣາຮາມ | |
| Sodom | ໂຊໂດມ | [tentative] |
| Hezekiah | ເຮເຊກີຢາ | ກະສັດ prefix |
| Amnon | ອຳໂນນ | [tentative] |
| Absalom | ອັບຊາໂລມ | [tentative] |
| Adam Clarke | ອາດາມ ຄລາກ | ດຣ. prefix [tentative] |
| E. Petavel | ອີ. ເປຕາແວນ | Author citation [tentative] |
| Josiah Strong | ໂຢສີຢາ ສະຕອງ | Author citation [tentative] |
| Mosheim | ໂມເຊມ | Author citation [tentative] |
| Pius IX | ປີອູດທີ 9 | Pope [tentative] |
| Gregory XVI | ເກຼັກກໍຣີທີ 16 | Pope [tentative] |
| Eusebius | ເອີເຊບິອັດ | [tentative] |
| Peter II of Aragon | ເປໂຕທີ 2 ແຫ່ງອາຣາກົງ | [tentative] |
| Innocent III | ອິນໂນເຊັນທີ 3 | Pope [tentative] |
| Abyssinia / Ethiopia | ເອທິໂອເປຍ | [tentative] |
| St. Louis (city) | ນະຄອນເຊນຫຼຸຍສ໌ | [tentative] |
| Esau | ເອຊາວ | |
| Bethel | ເບັດເອນ | [tentative] |
| Stephen | ສະເຕຟາໂນ | [tentative] |
| Caiaphas | ໄກອາຟາ | [tentative] |
| Michael (archangel) | ມີຄາເອນ | [tentative] |
| Elijah | ເອລີຢາ | |
| Joseph (OT) | ໂຢເຊັບ | [tentative] |
| Pharaoh | ຟາໂຣ | [tentative] |
| Jezebel | ເຢເຊເບນ | [tentative] |

## 12. Lao Bible Version Priority

When selecting a Bible version for citations, check in this order: LO2015 → LCV → TKJV → THSV → TH1971 → TNCV → NTV → TH1940 → LO1972 → ລາວບູຮານ. Prefer Thai versions (e.g., TKJV) when they capture a theological nuance that existing Lao translations flatten or miss.

The translator may also use versions not available digitally (e.g., LO1972, ລາວບູຮານ) when the translator has access to the physical text and a specific passage's wording uniquely serves the theological point. The AI translator should accept these version labels as authoritative when they appear in the reference translation.

When labeling versions in the text:
* Default version (LO2015): no label.
* Non-default Lao version: label after verse (e.g., `LCV`, `LO1972`).
* Thai version quoted verbatim: label after verse (e.g., `TKJV`).
* Thai version adapted: use `ດັດແປງຈາກສະບັບ TKJV`.
* ລາວບູຮານ adapted: use `ດັດແປງຈາກສະບັບລາວບູຮານ`.
* Direct translation from KJV: use `ແປຈາກສະບັບ KJV`.

---

# Part 3: Thai-Specific Rules (ภาษาไทย)

<!-- PLACEHOLDER: To be built from profiling English-to-Thai work (e.g., chapters from Patriarchs and Prophets, The Ministry of Healing). Will parallel the structure of Part 2: register & vocabulary, orthography, theological glossary, spelling glossary, Bible version priority. -->

*Awaiting text analysis.*
