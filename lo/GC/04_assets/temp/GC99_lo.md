---
chapter:
  number: 99
  title:
    lo: ບົດທົດສອບ
    en: Test Chapter
  url: https://example.com/test
---
\begin{verbatim}
## {GC 1.1}

### ການທົດສອບຕົວໜັງສື

This is a test paragraph with **bold text**, *italic text*, and ***bold italic text***. We can also use __alternative bold__ and _alternative italic_ and ___alternative bold italic___. {GC 1.1}

## {GC 1.2}

Testing ++underlined text++ and ~~strikethrough text~~ in the middle of a paragraph. These should convert properly to LaTeX commands. {GC 1.2}

## {GC 1.3}

Here's a paragraph with a footnote reference[^1] in the middle, and another one at the end.[^2] {GC 1.3}

[^1]: This is a simple footnote with *italic text* inside it.
[^2]: ມິນມານ, *ປະຫວັດຊາວຢິວ*, ເຫຼັ້ມທີ 13

## {GC 1.4}

Testing combinations: **bold followed by a footnote**[^3] and *italic with reference at end*. {GC 1.4}

[^3]: Footnote with **bold** and *italic* and ***bold italic*** formatting.

## {GC 1.5}

### Multi-line Footnotes (Future Feature)

This paragraph has a complex footnote[^multi] that will span multiple lines when we implement that feature. {GC 1.5}

[^multi]: This is the first line of a multi-line footnote.
    It continues on the second line with proper indentation.
    And even a third line with *emphasis* included.

## {GC 1.6}

### Block Quotes

Regular paragraph before the quote. 

> This is a block quote. It should be indented and formatted differently.
> It can span multiple lines.
> 
> And even have multiple paragraphs within the quote. {GC 1.6}

Back to regular text after the quote. {GC 1.7}

## {GC 1.8}

### Nested Block Quotes

Testing nested quotes. 

> Level one quote here.
> 
> > Level two nested quote with **bold text**.
> > Continuing the nested quote.
> 
> Back to level one quote.

Regular text after nested quotes. {GC 1.8}

## {GC 1.9}

### Line Breaks

There is an extra blank line between these paragraphs. {GC 1.9}

<br/>

There is an extra blank line between these paragraphs. {GC 1.10}

## {GC 1.11}

### Lists (Unordered)

Introduction to unordered list. {GC 1.12}

* First item
* Second item with **bold**
* Third item with *italic*
  * Nested item 1
  * Nested item 2
* Fourth item

Text after the list. {GC 1.13}

## {GC 1.14}

### Lists (Ordered)

Introduction to ordered list. {GC 1.14}

1. First numbered item
2. Second item with a footnote[^4]
3. Third item
   1. Nested numbered item
   2. Another nested item
4. Fourth item

[^4]: Footnote from a list item.

Text after ordered list. {GC 1.15}

## {GC 1.16}

### Mixed Lists

Testing mixed list types. {GC 1.16}

1. First ordered item
   * Unordered sub-item
   * Another unordered sub-item
2. Second ordered item
   1. Ordered sub-item
   2. Another ordered sub-item

End of mixed list section. {GC 1.17}

## {GC 1.18}

### Complex Combinations

Here's a paragraph with **bold with *nested italic* inside** and a footnote[^complex] with formatting. {GC 1.18}

> A blockquote with ***bold italic text*** and formatting.
> 
> * List item in a quote
> * Another item with **bold**

[^complex]: A footnote with **bold**, *italic*, ~~strikethrough~~, and ++underline++.

End of complex section. {GC 1.19}

## {GC 1.20}

### Edge Cases

Testing escaped symbols for math etc. that shouldn't be converted: 2 \* 3 = 6 and 4\*5=20, 2 \+ 2 = 4, This is a \~ "tilde". {GC 1.21}

Testing underscores in code\_like\_this and file\_names_here.txt shouldn't converted because the underscores are escaped. {GC 1.22}

Testing footnote at end of bold: **text with footnote[^5]** {GC 1.23}

[^5]: Final test footnote.

## {GC 1.24}

### Lao Text with Formatting

ປະໂຫຍກລາວທີ່ມີ **ຕົວໜັງສືເຂັ້ມ** ແລະ *ຕົວໜັງສືເອນ* ພ້ອມກັບ ***ຕົວໜັງສືເຂັ້ມແລະເອນ*** ໃນປະໂຫຍກດຽວກັນ. {GC 1.24}

ທົດສອບ ++ຂີດເສັ້ນໃຕ້++ ແລະ ~~ຂີດທັບ~~ ກັບພາສາລາວ. {GC 1.25}

### Scripture references

Test scripture references: 1 ຊາມູເອນ 3:16, 18–20; 4:1. ໂຢຮັນ 14:1–3

### Lao Ellipsis and Lao Repeat

ການສຶກສາໆ ແມ່ນສຳຄັນ…ແຕ່ການເຮັດວຽກໆໆ ກໍມີຄວາມສຳຄັນເຊັ່ນກັນ. ລາວເຮົາມັກເວົ້າວ່າ “ຮຽນໆ, ເຮັດໆ” ແລະ!…ບາງເທື່ອເຮົາເຫັນ ການໆ… ຫຼື ວຽກໆ; ເຊິ່ງແມ່ນປົກກະຕິ? ເວລາທີ່ມີໆໆໆ ຫຼາຍເກີນໄປ?… ມັນອາດຈະ: ບໍ່ດີ! ແຕ່ວ່າ “ເຮັດໆໆ”…(ຢ່າງຕໍ່ເນື່ອງ) ກໍເປັນສິ່ງທີ່ດີ. ການໃຊ້ໆ ຢູ່ທ້າຍປະໂຫຍກ… ແມ່ນຮູບແບບທົ່ວໄປ,…ແລະຄຳວ່າ “ຊັ້ນໆ”? ກໍມີໃນພາສາລາວ! ສຸດທ້າຍແລ້ວ.…

### Test \s and \S spacing conversion

ທ້າວສົມສັກໄດ້ເດີນທາງໄປຫາຕະຫຼາດໃນຕອນເຊົ້າ\sເພື່ອຊື້ເຄື່ອງໃຊ້ໃນຄົວເຮືອນ\Sແລະ\sຜັກໃສ່ສຳລັບອາຫານທ່ຽງ\sທີ່ລາວຈະຕ້ອງກະກຽມໃຫ້ຄອບຄົວ. ໃນຂະນະທີ່ລາວກຳລັງຊື້ໝາກໄມ້\sຈາກແມ່ຄ້າຄົນນຶ່ງ\Sລາວໄດ້ພົບກັບເພື່ອນເກົ່າ\sທີ່ບໍ່ໄດ້ເຫັນມາເປັນເວລາຫຼາຍປີ\sແລະພວກເຂົາໄດ້ນັ່ງລົມກັນ\Sກ່ຽວກັບຊີວິດການເຮັດວຽກ. ຫຼັງຈາກລົມກັນແລ້ວ\sທ້າວສົມສັກໄດ້ຊື້ປາສົດ\Sແລະເຂົ້າໜຽວ\sຈາກຮ້ານຂາຍເຄື່ອງກິນ\sແລະໄດ້ຕໍ່ລອງລາຄາ\Sຈົນກວ່າຈະໄດ້ລາຄາທີ່ເໝາະສົມ. ໃນທີ່ສຸດ\sລາວກໍໄດ້ກັບບ້ານ\Sໂດຍຖືຖົງຂອງທີ່ເຕັມໄປດ້ວຍອາຫານແລະຂອງໃຊ້\sພ້ອມດ້ວຍຄວາມພໍໃຈ\Sທີ່ໄດ້ພົບເພື່ອນເກົ່າ.

ທ້າວສົມສັກ\sໄດ້ເຫັນ\salvation ຂອງພຣະເຈົ້າ\Sແລະ\scommand ໃຫ້ລາວ\Sຮູ້ສຶກດີ.

### Test \cs{} compound phrase replacement

ທ້າວສົມສັກໄດ້ເດີນທາງໄປຊັງ ຫຼຸຍສ໌ເພື່ອພົບກັບລູກສາວທີ່ກຳລັງສຶກສາຢູ່ມະຫາວິທະຍາໄລ ແລະຫຼັງຈາກນັ້ນພວກເຂົາໄດ້ບິນໄປຊັງ ແອນເຈໂລເພື່ອຢ້ຽມຢາມຍາດຕິມິດ. ໃນຊຸມຊົນລາວທີ່ຊັງ ແອນເຈໂລ ລາວໄດ້ພົບກັບເພື່ອນໝູ່ຫຼາຍຄົນທີ່ໄດ້ຍ້າຍມາຈາກຊັງ ຫຼຸຍສ໌ແລະເມືອງອື່ນໆໃນລັດຄາລິຟໍເນຍ.
\end{verbatim}

### Math Mode Protection Tests
Regular text with spaces should convert. But inline math $a + b = c$ should keep spaces. Display math $$\int_0^1 x dx = \frac{1}{2}$$ also protected.

Bracket math \(E = mc^2\) and display \[\sum_{i=1}^n i = \frac{n(n+1)}{2}\] should preserve spaces.

Math environments:
\begin{equation}
f(x) = ax^2 + bx + c
\end{equation}

\begin{align}
x &= a + b \\
y &= c + d
\end{align}

### Code and Verbatim Protection Tests
Normal text here. Then \verb|code with spaces| should stay literal.

\begin{verbatim}
This is verbatim text
  with preserved   spaces
\end{verbatim}

Inline code: \lstinline|var x = "hello world"| and \lstinline{function test() { return true; }}

Minted example: \mintinline[style=colorful]{python}{def hello(): print("world")}

### URL Protection Tests
Visit \url{https://example.com/path with spaces} for more info.

Use \path{/home/user/my documents/file.txt} as the file path.

Link example: \href{https://site.com/page with spaces}{click here for the link}

### Mixed Protection Tests
Regular text $math = x + y$ more text \verb|code here| and \url{http://test.com/a b c}.

Nested protection: Text before \begin{equation} x = \verb|should this work?| + y \end{equation} text after.

### Edge Cases
Empty math: $$ $$ and empty verb: \verb|| 

Escaped dollars: \$5.99 and \$10.00 should convert spaces normally.

Multiple math on line: $a = 1$ and $b = 2$ with text between.

### Control Word Spacing Tests  
Commands like \section{Title With Spaces} should convert argument spaces.

Footnotes \footnote{This footnote has spaces that should convert} in text.

Source reference: \source{Book Title With Spaces} should convert.

### Lao Text with Protections
ທ້າວສົມສັກ ໄດ້ເຮັດ $x + y = z$ ແລະ \verb|ລາວ ພິມ| ໃນຄອມພິວເຕີ.

ການຄິດໄລ່ \begin{equation} \sum ລາວ = ດີ \end{equation} ສຳລັບການສຶກສາ.

ເວັບໄຊຕ໌: \url{https://laos.com/ຂ່າວ ມື້ນີ້} ມີຂໍ້ມູນດີ.

### Test poetry

## {GC 1.1}

ທຳມະຊາດຂອງພຣະເຈົ້າແມ່ນຄວາມຮັກ ແລະຄວາມສະຫວ່າງທີ່ບໍ່ມີວັນສິ້ນສຸດ. ດັ່ງທີ່ຂຽນໄວ້ວ່າ:

> ພຣະເຈົ້າຊົງເປັນຄວາມຮັກ
>
> ຜູ້ທີ່ຢູ່ໃນຄວາມຮັກກໍຢູ່ໃນພຣະເຈົ້າ
>
> ແລະພຣະເຈົ້າຊົງຢູ່ໃນລາວ
> > > > (1 ໂຢຮັນ 4:16) {GC 1.1}

## {GC 1.2}

ນີ້ແມ່ນບົດກະວີທີ່ມີຫຼາຍບົດ:

> ແສງສະຫວ່າງຂອງພຣະຜູ້ເປັນເຈົ້າ
>
> ສ່ອງສະຫວ່າງໃນຄວາມມືດ
>
> ນຳພາທາງໃຫ້ຜູ້ທີ່ຫຼົງທາງ
>
>
> ຄວາມຮັກຂອງພຣະອົງບໍ່ມີທີ່ສິ້ນສຸດ
>
> ຄວາມເມດຕາຂອງພຣະອົງຍັງຄົງຢູ່ຕະຫຼອດໄປ
>
> ທຸກມື້ເຊົ້າມີຄວາມຊື່ສັດໃໝ່
> > > > (ພະນັກງານຄົນ 3:22-23) {GC 1.2}

## {GC 1.3}

ຕົວຢ່າງຂອງການຍ່ອຫນ້າແບບຊັ້ນໆ:

> ພຣະບິດາໃນສະຫວັນໄດ້ກ່າວວ່າ:
> > ເຮົາຮັກເຈົ້າດ້ວຍຄວາມຮັກນິລັນດອນ
> > > ເພາະສະນັ້ນເຮົາຈຶ່ງດຶງເຈົ້າ
> > > ດ້ວຍຄວາມຮັກມັ່ນຄົງ
> > ເຮົາຈະບໍ່ປະຖິ້ມເຈົ້າ
> > ຫຼືລືມເຈົ້າຈັກເທື່ອ
> > > > (ເຢເຣມີຢາ 31:3) {GC 1.3}

## {GC 1.4}

ນີ້ແມ່ນຂໍ້ຄວາມປົກກະຕິທີ່ບໍ່ແມ່ນບົດກະວີ. ມັນມີຄຳເວົ້າທຳມະດາກ່ຽວກັບພຣະຄຳພີ. {GC 1.4}

## {GC 1.5}

ບົດກະວີສັ້ນໆ:

> ພຣະເຈົ້າຊົງເປັນທີ່ລີ້ໄພຂອງເຮົາ
> > > > (ເພງສັຣເສີນ 46:1) {GC 1.5}
