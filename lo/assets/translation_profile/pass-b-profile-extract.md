# Translation Profile Extract — Pass B

Sections: §1, §2, §3, §4.B, §4.C, §5, §6

---

## 1. Tone & Register

* **Dismantle Victorian Syntax:** Restructure convoluted 19th-century sentence patterns into clear, direct prose. The priority is clarity and readability, not preserving archaic English structure.
* **Use Reverent Language for Deity:** Employ formal ecclesiastical terminology appropriate to the target language's Christian tradition.
* **Use Degrading Language for Satan/Demons:** Use the target language's lowest-register pronoun or equivalent (animal/object class) when referring to Satan, Lucifer, or evil spirits. Never use polite or human-register pronouns for them. This applies regardless of narrative timeframe — even when describing Lucifer's pre-fall glory, use the degrading pronoun.
* **Retain Effective Rhetoric:** If a complex rhetorical structure from the English translates naturally into the target language without awkward phrasing, keep it. Never force the target language into unnatural shapes to mimic English rhetoric.
* **Eliminate First-Person Plural Bias:** When the English "we," "our," or "us" reflects a Western or American perspective, replace it with language appropriate to the universal reader (e.g., "our fathers" → the target-language equivalent of "America's pioneer generation"; "the world is no more ready" → address the global readership directly).

---

## 2. Syntactic Strategy

* **Apply Dynamic Equivalence:** Freely restructure, split, or combine sentences to favor natural target-language narrative flow. There is no requirement for 1:1 sentence correspondence with the English.
* **Evaluate Passives Contextually:** Do not default to either active or passive. If the agent is known and an active sentence is clearer, convert to active. If a passive construction is more natural in the target language for that context, keep it passive.
* **Eliminate Em-Dashes:** Replace em-dashes with conjunctions, relative clauses, or full sentence breaks. Restructure the logic so that an em-dash becomes unnecessary.
* **Never Split Paragraphs:** Maintain the exact paragraph block structure of the source text.
* **Use Numbered Lists for Complex Enumerations:** When the source contains a dense list embedded in prose, convert to a numbered list if it aids comprehension.
* **Unpack Dense Appositive Chains:** When the English stacks multiple appositives or parenthetical qualifiers into a single sentence, break them into separate clauses or sentences in the target language.
* **Use Numbered Decomposition for Parallel Elements:** When the source text discusses multiple prophetic passages, types, or arguments that point to the same event, the translator may organize them into a numbered list within the paragraph for clarity.

---

## 3. Contextual Clarification Strategy

When the English text contains ambiguous pronouns, implicit metaphors, or culture-specific perspectives, choose the lightest intervention that makes the meaning clear:

1. **Inline Adaptation (default):** Translate the intended meaning directly if it flows naturally and maintains readability (e.g., "our fathers" → the target-language equivalent of "America's pioneer generation").
2. **Bracketed Clarification:** Use brackets `[ ]` for brief inline context when a direct translation would obscure the original noun but the reader needs immediate help (e.g., `[referring to the Pope]`).
3. **Footnote:** Use footnotes for longer historical context, difficult concepts, or where any inline addition would disrupt narrative flow. (See §4.C for footnote types.)

---

## 4.B. Non-Biblical Citations & References

* **Convert Inline Book References to Footnotes:** When the English text cites a book, author, or document inline, remove it from the narrative and convert it to a footnote. Use the target-language footnote format (`.typ` Typst syntax).
* **Footnote Format for Book References:** Author surname (transliterated), book title (italicized), volume and chapter. On first occurrence of a *specific work* in a chapter, provide the full transliterated book title.
* **Volume Before Chapter:** Always list volume (ເຫຼັ້ມ) before chapter (ບົດ) in footnote citations. E.g., `ເຫຼັ້ມ 13, ບົດ 1.` — never the reverse order.
* **Edition Info:** When the English specifies an edition (e.g., "London ed."), transliterate it descriptively: `ສະບັບຕີພິມທີ່ລອນດອນ`.
* **Distinguish Multiple Works by Same Author:** When an author has multiple works cited, provide the full transliterated title on first occurrence of *each distinct work* in a chapter.
* **"Ibid." Handling:** When the source uses "Ibid.," use `*ອ້າງອີງຈາກທີ່ດຽວກັນ*` (italicized) as the Lao equivalent. Follow with volume/chapter/page info if the source specifies a different location. E.g., `*ອ້າງອີງຈາກທີ່ດຽວກັນ*, ເຫຼັ້ມ 3, ບົດ 7.` or `*ອ້າງອີງຈາກທີ່ດຽວກັນ*, ໜ້າ 389.` or simply `*ອ້າງອີງຈາກທີ່ດຽວກັນ*.`
* **Omit Appendix References:** Remove any references directing the reader to an Appendix (e.g., "(See Appendix.)").
* **Recover Appendix Content Selectively:** Evaluate each Appendix reference: if the content is relevant and easy to handle, create a substantive footnote. Otherwise, silently delete. This is a judgment call, not a blanket rule.
* **Correct Source Attribution Errors:** When the English source or its cited secondary source contains a known factual error (e.g., misattributed quotation, wrong historical figure), add a footnote correcting the record.
* **Historical-Dating Footnotes for Outdated Claims:** When the source text contains a bracketed editorial note like `[Published in 1888 and 1911. See Appendix.]`, convert it to a footnote explaining the historical context for today's reader.

---

## 4.C. Explanatory Footnotes

* **Add Historical-Context Footnotes:** If the English text makes a historical claim that has changed significantly in the modern era, or cites a decree/law, add a footnote clarifying the historical context for today's reader.
* **Royal-Vocabulary Footnotes:** When a royal-register word (ຣາຊາສັບ) appears for the first time, add a brief footnote defining it. E.g., `*ພຣະໂອດ*: ຣາຊາສັບ ໝາຍເຖິງປາກ.`
* **Cross-Reference Footnotes:** When the English text includes a parenthetical Bible reference that is not a direct quotation, convert it to a footnote with `ເບິ່ງ `.
* **Cross-Chapter References:** When the translator cross-references another chapter in the same book, use `ເບິ່ງ ບົດທີ [N].`
* **Doctrinal-Explanation Footnotes:** When the English mentions a doctrine or practice unfamiliar to the target audience, add a brief footnote explaining it.
* **Repeat Essential Footnotes per Chapter:** Footnotes that provide vital context (e.g., the day-year prophetic principle: `ໜຶ່ງວັນແຫ່ງຄຳພະຍາກອນເທົ່າກັບໜຶ່ງປີ. ເບິ່ງ ຈົດບັນຊີ 14:34; ເອເຊກຽນ 4:6.`) should be repeated each time the concept is contextually relevant in a new chapter, not just once per book.
* **Vocabulary Footnotes:** When the chosen Bible version uses a word that many readers will not understand, add a brief footnote defining it.
* **Inline Clarification Footnotes:** Use footnotes to clarify terms, currency, people, or places that the target reader may not recognize.
* **Metaphor-Explanation Footnotes:** When the English uses a figurative title or metaphor that may not be obvious to the target reader, add a brief footnote. E.g., "Sun of Righteousness" → footnote: `ໝາຍເຖິງພຣະຄຣິສ.`
* **Theological-Identity Footnotes:** When a biblical figure's identity is ambiguous or theologically significant (e.g., "the Angel of the covenant" = the pre-incarnate Christ), add a brief footnote clarifying.
* **Narrative-Structure Footnotes:** When the author's literary technique (e.g., flashback, chronological reordering) might confuse the reader, add a brief footnote orienting the reader.
* **Bible-Reading-Instruction Footnote (book opener only):** On the very first citation of the book, add a footnote explaining how to read the citation format aloud in the target language. E.g., `ອ່ານວ່າ ລູກາ ບົດທີສິບເກົ້າ ຂໍ້ສີ່ສິບສອງເຖິງສີ່ສິບສີ່.` This is a one-time addition, not repeated per chapter.
* **"Consideration List" for Rare Words:** Do not add translation footnotes for vocabulary inside the translation block itself. Instead, list rare or potentially unknown words at the end of the section for the editor to decide on.

---

## 5. Formatting & Tags

* **Preserve End Tags:** Place the paragraph tag at the end of each paragraph in the format: `{AA ###.#}`.
* **Pre-Tag Format:** `.typ` files: `// {AA ###.#}`
* **Sub-Headers:** If the source or reference translation contains sub-headers, preserve them as-is unless there is an obvious error. Sub-header creation is a separate editorial process and should not be handled during translation.
* **Keep Headers Short:** Headers should be brief and impactful, not long descriptive sentences.
* **Footnote Syntax:** Use Typst inline `#footnote()`. Number footnotes per chapter starting from 1.
* **Ignore Pipeline Markup:** Do not produce LaTeX or typesetting codes (e.g., `\\s`, `\\p{-200}`, `\cs{}`, `\lw{}`, `{\;}`) in the translation output. These are added by a separate processing pipeline. When editing an existing file that already contains such markup, reproduce it faithfully without commenting on it, unless it is obviously wrong.
* **Chapter Titles May Be Adapted:** The Lao chapter title does not need to be a literal translation of the English chapter title. The translator may create a title that better captures the chapter's content for the target reader.

---

## 6. Proper Noun Conventions

Consult `AA-glossary.txt` for full names, short forms, titles,
and descriptive identifiers for every person, place, and
institution in AA.

* **Transliterate Historical Names and Places:** Render European historical names and geographical locations phonetically into the target language's script.
* **First-Occurrence Parenthetical — Non-Biblical Names Only:** On first use in a chapter, provide the English name in parentheses after the transliteration for historical figures, places, and institutions whose Lao transliteration might be unfamiliar to the reader. Do NOT add English parentheticals for biblical names the reader already knows from Scripture (e.g., ໂປໂລ, ເປໂຕ, ໂຢຮັນ, ໂມເຊ, ດາວິດ, ເຢຣູຊາເລັມ). The parenthetical is an aid for non-biblical names that would otherwise be unrecognizable.
* **Subsequent Mentions:** Use only the transliterated short form after first occurrence within the same chapter.
* **Full Name on First Mention:** For persons, provide the full name on first mention even if the English abbreviates. Look up the full form in `AA-glossary.txt`. E.g., the glossary lists `ໂປກີໂອເຟຊະໂຕ` with short form `ເຟຊະໂຕ` — use: `ໂປກີໂອເຟຊະໂຕ (Porcius Festus)` on first use, then `ເຟຊະໂຕ` thereafter.
* **Titles as Identifiers:** After introducing a person, the translator may use a descriptive title instead of repeating the name: e.g., `ນາຍຮ້ອຍຢູລີໂອ` ("Centurion Julius") rather than just the transliterated name.
* **Biblical Figure Title Conventions:** Use culturally appropriate titles for well-known biblical figures. E.g., `ອາຈານໂປໂລ` ("Teacher Paul"), `ກະສັດດາວິດ` ("King David"), `ກະສັດໂຊໂລໂມນ` ("King Solomon"), `ຜູ້ເຜີຍພຣະທຳດານີເອນ` ("Prophet Daniel"). These titles may alternate with the plain name or with `ອັກຄະສາວົກ` ("Apostle") depending on context.
