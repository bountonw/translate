// =============================================================================
// Dictionary — Thai Word Protection
//
// Two complementary mechanisms:
//
//   1. protected-words / protect-words
//      Wrap whole words (or morpheme parts) in box[] so ICU4X segmentation
//      cannot break them. Use for words you NEVER want broken arbitrarily.
//      With `parts:`, the only allowed break is a soft hyphen between parts.
//
//   2. soft-hyphen-words / apply-soft-hyphens
//      Insert a soft hyphen at a preferred break point. Parts are NOT boxed —
//      Thai segmentation may still break elsewhere; the soft hyphen just
//      provides a hint the line-breaker can use when needed.
//
// ORDERING RULE: longest terms first within each list. Shorter substrings
// (e.g. "พระ") must appear after every compound that contains them.
// =============================================================================

// -----------------------------------------------------------------------------
// 1. Protected words — boxed (no breaks except optional soft hyphen between parts)
//
// Entry format:
//   (word: "...", parts: none)        → single unbreakable box
//   (word: "...", parts: ("a","b"))   → boxes joined by soft hyphens;
//                                        hyphen appears only when a line
//                                        break actually occurs there
// -----------------------------------------------------------------------------

#let protected-words = (
  // Long compounds and proper names — 4+ syllables
  (word: "พระผู้ช่วยให้รอด",    parts: ("พระผู้ช่วย", "ให้รอด")),
  (word: "พระวิญญาณบริสุทธิ์", parts: ("พระวิญญาณ", "บริสุทธิ์")),
  (word: "พระเยซูคริสต์",      parts: ("พระเยซู", "คริสต์")),
  (word: "อัครทูตเปาโล",       parts: ("อัครทูต", "เปาโล")),
  (word: "ผู้เผยพระวจนะ",       parts: ("ผู้เผย", "พระวจนะ")),   // must precede พระวจนะ
  (word: "แผ่นดินสวรรค์",      parts: ("แผ่นดิน", "สวรรค์")),
  (word: "พระหัตถกิจ",          parts: none),
  (word: "พระเมสสิยาห์",        parts: none),
  (word: "องค์สันติราช",        parts: none),
  (word: "สิ้นพระชนม์",         parts: ("สิ้น", "พระชนม์")),
  (word: "นาธานาเอล",           parts: none),
  (word: "บุตรมนุษย์",          parts: ("บุตร", "มนุษย์")),
  // 3-syllable พระ compounds
  (word: "พระสุรเสียง",         parts: none),
  (word: "พระราชกิจ",           parts: none),
  (word: "พระผู้สร้าง",         parts: ("พระผู้", "สร้าง")),
  (word: "พระผู้ไถ่",           parts: ("พระผู้", "ไถ่")),
  (word: "พระลักษณะ",           parts: none),
  (word: "พระชนม์ชีพ",          parts: ("พระชนม์", "ชีพ")),
  (word: "พระบัลลังก์",         parts: none),
  (word: "พระประสงค์",          parts: none),
  (word: "พระรัศมี",            parts: none),
  (word: "พระวิหาร",            parts: none),
  (word: "พระกุมาร",            parts: ("พระ", "กุมาร")),
  (word: "พระสัญญา",            parts: none),
  (word: "พระโลหิต",            parts: none),
  (word: "พระวิญญาณ",           parts: none),
  (word: "พระบัญญัติ",          parts: none),
  (word: "พระคัมภีร์",          parts: none),
  // สวรรค์ compounds — must precede standalone สวรรค์
  (word: "ทูตสวรรค์",           parts: ("ทูต", "สวรรค์")),
  (word: "สรวงสวรรค์",          parts: ("สรวง", "สวรรค์")),
  (word: "ฟ้าสวรรค์",           parts: ("ฟ้า", "สวรรค์")),
  (word: "ชาวสวรรค์",           parts: ("ชาว", "สวรรค์")),
  // Remaining พระ terms
  (word: "พระนิเวศ",            parts: none),
  (word: "พระเมตตา",            parts: none),
  (word: "พระกรุณา",            parts: none),
  (word: "พระปัญญา",            parts: none),
  (word: "พระสิริ",             parts: none),
  (word: "พระวจนะ",             parts: none),
  (word: "พระบิดา",             parts: none),
  (word: "พระคริสต์",           parts: none),
  (word: "พระธรรม",             parts: none),
  (word: "พระองค์",             parts: none),
  (word: "พระหัตถ์",            parts: none),
  (word: "พระพักตร์",           parts: none),
  (word: "พระเยซู",             parts: none),
  (word: "พระบุตร",             parts: none),
  (word: "พระเจ้า",             parts: none),
  (word: "พระคุณ",              parts: none),
  (word: "พระพร",               parts: none),
  (word: "พระบาท",              parts: none),
  (word: "พระทัย",              parts: none),
  // Standalone สวรรค์ (after all compounds containing it)
  (word: "สวรรค์",              parts: none),
  // Religious roles, objects & rites
  (word: "ธรรมบัญญัติ",         parts: none),
  (word: "ธรรมาจารย์",          parts: none),
  (word: "ธรรมศาลา",            parts: none),
  (word: "มหาปุโรหิต",          parts: ("มหา", "ปุโรหิต")),      // must precede ปุโรหิต
  (word: "ปุโรหิต",             parts: none),
  (word: "บรรณาการ",            parts: none),
  (word: "แท่นบูชา",            parts: none),
  (word: "มดยอบ",               parts: none),
  (word: "กำยาน",               parts: none),
  // Proper names — people & places
  (word: "เยรูซาเล็ม",          parts: none),
  (word: "ปาเลสไตน์",           parts: none),
  (word: "กันดารวิถี",          parts: none),
  (word: "เบธเลเฮม",            parts: none),
  (word: "อิสราเอล",            parts: none),
  (word: "สะมาเรีย",            parts: none),
  (word: "นาซาเร็ธ",            parts: none),
  (word: "เอเฟซัส",             parts: none),
  (word: "โครินธ์",             parts: none),
  (word: "อิสยาห์",             parts: none),
  (word: "สิเมโอน",             parts: none),
  (word: "มัทธิว",              parts: none),
  (word: "กาลิลี",              parts: none),
  (word: "ฟาโรห์",              parts: none),
  (word: "อียิปต์",             parts: none),
  (word: "ยูเดีย",              parts: none),
  (word: "เฮโรด",               parts: none),
  (word: "โมเสส",               parts: none),
  (word: "ดาวิด",               parts: none),
  (word: "โยเซฟ",               parts: none),
  (word: "มารีย์",              parts: none),
  (word: "อันนา",               parts: none),
  (word: "ปัสกา",               parts: none),
  (word: "รับบี",               parts: none),
  (word: "ลูกา",                parts: none),
  (word: "ซาตาน",               parts: none),
  (word: "ยาโคบ",               parts: none),
  (word: "เอซาว",               parts: none),
)

#let protect-words(body) = {
  let result = body
  for entry in protected-words {
    let replacement = if entry.parts == none {
      box(entry.word)
    } else {
      entry.parts.map(box).join("\u{00AD}")
    }
    result = {
      show entry.word: _ => replacement
      result
    }
  }
  result
}

// -----------------------------------------------------------------------------
// 2. Soft-hyphen hints — preferred break points (no boxing)
//
// Format: each entry uses "-" to mark the split point. The rule replaces the
// joined form (with "-" stripped) with the same word containing a soft hyphen
// at that position.
//
// Note: if a word here also appears in protected-words above, the box wins
// and the soft hyphen has no effect (since the box prevents all breaks).
// -----------------------------------------------------------------------------

#let soft-hyphen-words = (
  // 5-syllable compounds
  "ความชื่นชม-ยินดี",
  "ความเจริญ-ก้าวหน้า",
  // 4-syllable compounds
  "สิทธิบุตร-หัวปี",
  "สัมพันธ-ไมตรี",
  "ความปีติ-ยินดี",
  "การสื่อ-สัมพันธ์",
  "การเปลี่ยน-แปลง",
  "การล่วง-ละเมิด",
  "การ-อธิษฐาน",
  "การ-พิพากษา",
  "การ-ประพฤติ",
  "ความเห็น-แก่ตัว",
  "ความ-สัมพันธ์",
  "ความ-บริสุทธิ์",
  "ความ-ชอบธรรม",
  "ความ-กลมเกลียว",
  "ความ-สามารถ",
  "ความ-พยายาม",
  "ความ-สมบูรณ์",
  "ความ-เสื่อมทราม",
  "แรกเริ่ม-เดิมที",
  "ฤทธา-นุภาพ",
  // 3-syllable compounds
  "อาณา-จักร",
  "มนุษย-ชาติ",
  "สามัคคี-ธรรม",
  "การ-สนิทสนม",
  "ฤทธิ์-อำนาจ",
  "จิต-วิญญาณ",
  "อุป-นิสัย",
  "ความ-สอดคล้อง",
  "ความ-ใฝ่ฝัน",
  "ความ-สำคัญ",
  "ความ-มุ่งหมาย",
  "คุณ-ความดี",
  "การ-ฟื้นฟู",
  "การสื่อ-สาร",
)

#let apply-soft-hyphens(body) = soft-hyphen-words.fold(body, (it, word) => {
  show word.replace("-", ""): word.replace("-", sym.hyph.soft)
  it
})
