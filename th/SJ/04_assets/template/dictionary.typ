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
  (word: "พระวิญญาณบริสุทธิ์", parts: ("พระ", "วิญญาณ", "บริสุทธิ์")),
  (word: "พระเยซูคริสต์",      parts: ("พระ", "เยซู", "คริสต์")),
  (word: "อัครทูต",       parts: ("อัคร", "ทูต")),
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
  (word: "พระนิเวศ",             parts: ("พระ", "นิเวศ")),
  (word: "พระเมตตา",            parts: ("พระ", "เมตตา")),
  (word: "พระกรุณา",             parts: ("พระ", "กรุณา")),
  (word: "พระปัญญา",             parts: ("พระ", "ปัญญา")),
  (word: "พระสิริ",               parts: ("พระ", "สิริ")),
  (word: "พระวจนะ",             parts: ("พระ", "วจนะ")),
  (word: "พระบิดา",              parts: ("พระ", "บิดา")),
  (word: "พระคริสต์",             parts: ("พระ", "คริสต์")),
  (word: "พระธรรม",             parts: ("พระ", "ธรรม")),
  (word: "พระองค์",              parts: ("พระ", "องค์")),
  (word: "พระหัตถ์",              parts: ("พระ", "หัตถ์")),
  (word: "พระพักตร์",             parts: ("พระ", "พักตร์")),
  (word: "พระเยซู",              parts: ("พระ", "เยซู")),
  (word: "พระบุตร",              parts: ("พระ", "บุตร")),
  (word: "พระเจ้า",              parts: ("พระ", "เจ้า")),
  (word: "พระคุณ",               parts: ("พระ", "คุณ")),
  (word: "พระพร",               parts: ("พระ", "พร")),
  (word: "พระบาท",              parts: ("พระ", "บาท")),
  (word: "พระทัย",               parts: ("พระ", "ทัย")),
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

//
// คุณ.ภาพ
// พระ.องค์
// พระ.ยาห์.เวห์
// พระ.เย.โฮ.วาห์
// องค์.พระ.ผู้.เป็น.เจ้า
// พระ.ผู้.เป็น.เจ้า
// ตะ.วัน.ออก
// ตะ.วัน.ตก
// พระ.นาม
// ทะ.ลัก
// หน้า.ต่าง
// โน.อาห์
// ภรร.ยา
// พันธ.สัญ.ญา
// อับ.ราม
// อับ.รา.ฮัม
// เบธ.เอล
// คา.เดช
// หัว.เราะ
// อิส.อัค
// อิช.มา.เอล
// ละ.เอียด
// ซา.ราห์
// กระ.ทำ
// คำ.นับ
// ข้าพ.เจ้า
// อา.บี.เม.เลค
// มล.ทิน
// คา.นา.อัน
// เฮ.โบรน
// กรรม.สิทธิ์
// เร.เบ.คาห์
// เบธูเอล
// ประ.ทาน
// เอ.ซาว
// ปฏิ.ญาณ
// ประ.ชา.ชาติ
// กัน.ดาร
// นมัส.การ
// ระ.หว่าง
// อา.รัม
// สาร.ทิศ
// ศักดิ์.สิทธิ์
// ยา.โคบ
// สรร.เสริญ
// ฉะ.นั้น
// คุก.คาม
// บรร.ดา
// ประ.จำ
// รุน.แรง
// ประ.เทศ
// เมต.ตา
// อิส.รา.เอล
// ปรา.กฏ
// โค.ราห์
// เอ.โดม
// โย.เซฟ
// กระ.ชาก
// กระ.สอบ
// รัก.ษา
// ยู.ดาห์
// ทา.มาร์
// เซ.ลาห์
// ประ.ทาน
// พนัก.งาน
// ฟา.โรห์
// ตำ.แหน่ง
// ข้า.พระ.บาท
// ประ.หาร
// อี.ยิปต์
// ราช.การ
// ประ.เทศ
// พระ.ชนม์
// ครอบ.ครัว
// อัน.ตราย
// อา.หาร
// อา.รมณ์
// ราช.สำนัก
// ราช.บริ.พาร
// เช.เขล
// เบ.เออร์.เช.บา
// เอ.ฟรา.อิม
// สา.มารถ
// สา.บาน
// นัฟ.ทา.ลี
// ประ.ชา.กร
// ปก.ครอง
// บริ.สุทธิ์
// บริ.การ
// บริ.โภค
// บรรพ.บุรุษ
// อัศ.จรรย์
// อา.โรน
// เอล.คา.นาห์
// เอ.เล.อา.ซาร์
// ข้า.ราช.การ
// พระ.บาท
// ฝ่า.พระ.บาท
// ประ.ชา.กร
// พระ.ราช.วัง
// โม.เสส
// พระ.พักตร์
// มรณ.ภัย
// อนุ.ญาต
// ปริ.มาณ
// ราช.บุตร
// ราช.ธิดา
// รำ.มะ.นา
// สะ.บา.โต
// ตุลา.การ
// เหตุ.การณ์
// ยุติ.ธรรม
// ทอง.สัม.ฤทธิ์
// นมัส.การ
// เค.รูป
// คัน.ประ.ทีป
// กระ.ถิน.เทศ
// จัตุ.รัส
// วิสุทธิ.สถาน
// สถา.ปนา
// กระ.จาด
// โม.อับ
// ข้า.พระ.องค์
// อา.โม.ไรต์
// ผลิต.ผล
// เทศ.กาล
// พระ.บัญ.ญัติ
// เข็ม.กลัด
// พระ.ที่.นั่ง
// กรุ.ณา
// คัน.ประ.ทีบ
// เอ.โฟด
// น้ำ.เงิน
// พลับ.พลา
// ธัญ.บูชา
// พัง.ผืด
// แม่.เท้า
// อภิ.สุทธิ.สถาน
// พระ.โม.เลค
// โม.เลค
// ประ.ชา.ชน
// ประ.กาศ
// ประ.ชุม
// ชั่ว.คราว
// ศต.วรรษ
// นา.ดับ
// ตระ.กูล
// ภา.ชนะ
// คุณ.สม.บัติ
// อุ.ทิศ
// กิโล.กรัม
// สิ.เม.โอน
// เอฟ.รา.อิม
// นัฟ.ทา.ลี
// กระ.ถาง
// น้ำ.เงิน
// พระ.เกียรติ
// ปฏิ.บัติ
// ชุม.ชน
// จอร์.แดน
// บา.ลา.อัม
// ฟี.เน.หัส
// อา.เล.อา.ซาร์
// เย.รี.โค
// พระ.ทัย
// ประ.มาณ
// ปฏิ.ญาณ
// สา.บาน
// รู.เบน
// พระ.พิโรธ
// ทะ.เล
// แม่.น้ำ
// มหา.ปุ.โร.หิต
// ปุ.โร.หิต
// ยา.โคบ
// คา.เดช.บา.เนีย
// บา.ชาน
// รูป.พรรณ
// กิล.กาล
// พระ.เนตร
// พระ.บัญ.ชา
// บัญ.ชา
// พระ.วจนะ
// กรรม.สิทธิ์
// เศ.บู.ลุน
// อา.เชอร์
// ยู.ดาห์
// ปฏิ.ญาณ
// ยู.เฟร.ติส
// กระ.เจิง
// อา.รา.บาห์
// โย.ชู.วา
//
//
//
//
//
//
// เจ็ด.สิบ
// สิบ.สอง
// สิบ.ห้า
//
// เบ.โอร์
// รับ.บาห์
// ปา.ราน
// เม.รา.รี
// เกอร์.โชน
// ชัด.ดัย
// กา.มา.ลิ.เอล
// เบ.ซา.เลล
// อา.บี.ฮู
// เอล.ซา.ฟาน
// นาห์.โชน
// เย.บุส
// เร.อู.เอล
// พิส.ทา.ชิ.โอ
// มัส.เร.คาห์
// โอ.โฮ.ลี.บา.มา
// บา.เส.มัท
//เบน.ยา.มิน
// บิล.ฮาห์
// เล.อาห์
// อา.หุส.ซัท
// ฮิต.ไทต์
// เอ.เฟอร์
// เศ.เมอร์
// ซา.ราย
// โยก.ทาน
// อาบี.มาเอล
// เส.ฟาร์
// ฮา.ราน
// สิด.ดิม
// ปา.ราน
//
//
//
//
//
#let apply-soft-hyphens(body) = soft-hyphen-words.fold(body, (it, word) => {
  show word.replace("-", ""): word.replace("-", sym.hyph.soft)
  it
})
