# Lao GC glossary: versions on origin/main against the latest row texts

VERDICT: Copy A on origin/main holds the latest text of every one of its 627 heads, and no row in copy B or in any other version is newer, so no row needs to be brought forward.

Copy A is lo/GC/04_assets/translation_profile/GC-glossary.txt. Copy B is lo/assets/translation_profile/GC-glossary.txt. origin/main now stands at 1e3a27c8 (#879); its two blobs are the same as at 9d2ce850 and at GC-instructions adc0fc8b.

## 1. Which copy is complete and recent

1.A. Copy A (blob 6a516591) holds 634 rows under 627 heads. Its text was written by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"); cf07567d, 6c7ff3ac and 42e72e29 carried it without change. Copy A differs from the latest texts in 0 rows.

1.B. Copy B (blob 11a3d4e8) holds 449 rows under 442 heads. Its text is the version of 2026-08-09, first written by 64132ed2 ("Update glossary") and squash-merged to main by 31bcb4b4 (#816). Copy B differs from the latest texts at 275 heads: 58 heads hold an older text (item 2) and 217 heads are missing (item 3.B). A further 19 heads in copy B were renamed, split or merged after 2026-08-09 and survive in copy A under new heads (item 4.B).

1.C. Copy B is old because the glossary moved. On 2026-08-10, 6f28d67b ("Prepare helper files and instructions for audit") moved the file from path B to path A, and every later edit went to path A. On 2026-09-02, 2246b6b6 ("Keep only typesetting inputs in QA3 branch") deleted path A from the QA3 branch, and on 2026-09-03 the squash b5c84956 ("GC QA3 (#860)") deleted path B from main, which left main with no copy. On 2026-09-29, 772b6aba (#870) restored path B with the text main had lost, which was the 2026-08-09 text. On 2026-10-04, 42e72e29 ("Set up the lo/FB project and FB01 (#869)") brought path A to main with the 2026-09-02 text; the FB set-up copied it from the GC-instructions branch, as lo/FB/CLAUDE.md:21 records.

1.D. Method. I read 45 distinct versions of the two paths from the 56 commits that touch them in all refs (git log --all). Rows are keyed by the English head, ignoring case. Rows of one head are compared together across all tables, because some rows moved between tables. Section 12 rows are keyed by their Lao pair. The content forms one line of descent in date order, so the latest text of a head is its text in the last version that holds it, and the introducing commit is the first commit of that unbroken run of text. The versions hold 659 distinct heads in all.

## 2. Heads where a copy on origin/main holds an older text

2.A. Copy A holds an older text at 0 heads.

2.B. Copy B holds an older text at 58 heads. At 38 heads the Lao cell differs, at 15 heads only the Notes cell differs, and at 5 heads one of the two versions holds more than one row under the head. Copy A holds the latest text of all 58. Each line gives the Lao cell of both versions; the full rows stand at the same head in the two files.

2.B.1. Day of Atonement (copy B). Lao in copy B: ວັນລຶບລ້າງບາບອັນຍິ່ງໃຫຍ່. Lao in the latest text: ວັນລຶບລ້າງບາບ / ວັນລຶບລ້າງຄວາມບາບ / ວັນລຶບລ້າງມົນທິນບາບ / ວັນສຳຄັນແຫ່ງການລຶບລ້າງຄວາມບາບ / ວັນແຫ່ງການລຶບລ້າງຄວາມບາບ. The Notes cell differs as well. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.2. Spiritualism (copy B). Lao in copy B: ລັດທິຕິດຕໍ່ກັບວິນຍານ. Lao in the latest text: ລັດທິຕິດຕໍ່ກັບວິນຍານ / ລັດທິຕິດຕໍ່ວິນຍານ / ລັດທິການຕິດຕໍ່ກັບວິນຍານ / ການຕິດຕໍ່ກັບວິນຍານ / ການຕິດຕໍ່ພົວພັນກັບວິນຍານ / ການສື່ສານກັບວິນຍານ / ຄຳສອນເລື່ອງການຕິດຕໍ່ກັບວິນຍານ. The Notes cell differs as well. The latest text was introduced by 2e9db5a7 (2026-08-19, "QA2 GC34"), and copy A holds it.

2.B.3. Dark Ages (copy B). The Lao cell is the same in both: ຍຸກມືດ / ສະໄໝຍຸກມືດ. Only the Notes cell differs. The latest text was introduced by 2263281d (2026-08-11, "Update terms and instructions"), and copy A holds it.

2.B.4. Apostasy (copy B). Lao in copy B: ການພັດຫຼົງໄປຈາກຄວາມເຊື່ອ. Lao in the latest text: ການປະຖິ້ມຄວາມເຊື່ອ / ການພັດຫຼົງໄປຈາກຄວາມເຊື່ອ. The Notes cell differs as well. The latest text was introduced by 2e9db5a7 (2026-08-19, "QA2 GC34"), and copy A holds it.

2.B.5. Mercy seat (copy B). Lao in copy B: ພຣະທີ່ນັ່ງແຫ່ງກະລຸນາ / ພຣະທີ່ນັ່ງກະລຸນາ. Lao in the latest text: ພຣະທີ່ນັ່ງແຫ່ງພຣະກະລຸນາ. The Notes cell differs as well. The latest text was introduced by 39f3b71c (2026-08-13, "QA2 GC20 with side effect updates"), and copy A holds it.

2.B.6. Gospel (copy B). The Lao cell is the same in both: ຂ່າວປະເສີດ. Only the Notes cell differs. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.7. Council (of the church) (copy B). The Lao cell is the same in both: ສະພາຄຣິສຕະຈັກ / ປະຊຸມສະພາ. Only the Notes cell differs. The latest text was introduced by 1577a3e2 (2026-08-28, "Sidequests"), and copy A holds it.

2.B.8. Jesuits (copy B). The Lao cell is the same in both: ຄະນະສົງເຢຊຸອິດ / ເຢຊຸອິດ. Only the Notes cell differs. The latest text was introduced by 2263281d (2026-08-11, "Update terms and instructions"), and copy A holds it.

2.B.9. Midnight Cry (copy B). Lao in copy B: ສຽງຮ້ອງຍາມທ່ຽງຄືນ. Lao in the latest text: ສຽງຮ້ອງປະກາດຍາມທ່ຽງຄືນ. The Notes cell differs as well. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.10. Cleansing of the sanctuary (copy B). Lao in copy B: ການຊຳລະສະຖານບໍຣິສຸດ. Lao in the latest text: ການຊຳລະສະຖານບໍຣິສຸດ / ການຊຳລະສະຖານນະມັດສະການ. The Notes cell differs as well. The latest text was introduced by a1d84a7b (2026-08-16, "QA2 GC24"), and copy A holds it.

2.B.11. Image to the beast (copy B). Lao in copy B: ຮູບຈຳລອງຂອງສັດຮ້າຍ. Lao in the latest text: ຮູບຈຳລອງໃຫ້ແກ່ສັດຮ້າຍ where EN is *to*; ຮູບຈຳລອງຂອງສັດຮ້າຍ where EN is *of*. The Notes cell differs as well. The latest text was introduced by 22a7e280 (2026-08-16, "QA2 GC25"), and copy A holds it.

2.B.12. Lutheran (copy B). Lao in copy B: ລູເທີແຣນ. Lao in the latest text: ລູເທີແຣນ / ຄະນະລູເທີແຣນ. The Notes cell is the same. The latest text was introduced by 4966f405 (2026-08-11, "Update glossary and terms"), and copy A holds it.

2.B.13. Mediator (copy B). The Lao cell is the same in both: ຜູ້ເປັນກາງ / ຄົນກາງ. Only the Notes cell differs. The latest text was introduced by 31914edb (2026-08-11, "Update glossary"), and copy A holds it.

2.B.14. Ancient of Days (copy B). Lao in copy B: ອົງຜູ້ດຳລົງຊີວິດຢັ້ງຢືນຕະຫຼອດການ / ຜູ້ດຳລົງຢູ່ຕັ້ງແຕ່ດຶກດຳບັນ. Lao in the latest text: ອົງຜູ້ດຳລົງຢູ່ຕັ້ງແຕ່ດຶກດຳບັນ (LCV, TNCV) / ຜູ້ມີຊີວິດຢູ່ຕະຫຼອດໄປ (LO2012) / ຜູ້ຈະເລີນດ້ວຍໄວຍະວຸດ (TKJV) / ອົງຜູ້ດຳລົງຊີວິດຢັ້ງຢືນຕະຫຼອດການ (NTV) / ພຣະເຈົ້າອົງນິຣັນ. The Notes cell differs as well. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.15. Guardian angel (copy B). Lao in copy B: ທູດສະຫວັນຜູ້ປົກປ້ອງ. Lao in the latest text: ທູດສະຫວັນຜູ້ປົກປ້ອງ / ທູດສະຫວັນປະຈຳຕົວ. The Notes cell differs as well. The latest text was introduced by 6188065b (2026-08-18, "Update glossary and terms"), and copy A holds it.

2.B.16. Familiar spirits (copy B). The Lao cell is the same in both: ຄົນຊົງເຈົ້າເຂົ້າຜີ. Only the Notes cell differs. The latest text was introduced by 2e9db5a7 (2026-08-19, "QA2 GC34"), and copy A holds it.

2.B.17. Resurrection (copy B). Lao in copy B: ການຟື້ນຄືນຊີບ / ການເປັນຄືນມາຈາກຕາຍ. Lao in the latest text: ຟື້ນຄືນຊີບ / ຟື້ນຄືນຊີວິດ / ຟື້ນຈາກຄວາມຕາຍ / ຄືນມາ / ຄືນພຣະຊົນ / ຟື້ນພຣະຊົນ. The Notes cell differs as well. The latest text was introduced by f377dade (2026-08-24, "QA2 GC41"), and copy A holds it.

2.B.18. Jacob's trouble (copy B). Lao in copy B: ເວລາແຫ່ງຄວາມທຸກຍາກຂອງຢາໂຄບ. Lao in the latest text: ເວລາທຸກຍາກຂອງຢາໂຄບ (period) / ຄວາມທຸກຍາກຂອງຢາໂຄບ (affliction) / ເວລາທຸກໃຈຂອງຢາໂຄບ (TKJV) / ເວລາແຫ່ງຄວາມທຸກຍາກຂອງຢາໂຄບ. The Notes cell differs as well. The latest text was introduced by 3aaf0282 (2026-08-24, "QA2 GC40"), and copy A holds it.

2.B.19. Holy City (copy B). Lao in copy B: ນະຄອນບໍຣິສຸດ. Lao in the latest text: ນະຄອນບໍຣິສຸດ / ນະຄອນສັກສິດ. The Notes cell differs as well. The latest text was introduced by 95b34852 (2026-08-12, "Update terms and glossary"), and copy A holds it.

2.B.20. Close of probation (copy B). Lao in copy B: ໂອກາດສິ້ນສຸດ / ເວລາແຫ່ງໂອກາດສິ້ນສຸດ. Lao in the latest text: ເວລາແຫ່ງພຣະກະລຸນາ. The Notes cell differs as well. The latest text was introduced by a1d84a7b (2026-08-16, "QA2 GC24"), and copy A holds it.

2.B.21. Church (institution) (copy B). Copy B holds 1 row under this head and the latest text holds 2. One of them is the same in both. The latest text adds a row with Lao Correct ຄຣິສຕະຈັກ, Incorrect ຄຣິສຈັກ. The latest text was introduced by 1a891f31 (2026-08-13, "Add side-quest queue"), and copy A holds it.

2.B.22. Martin Luther (copy B). Copy B holds 2 rows under this head and the latest text holds 1. One of them is the same in both. Copy B also holds an older duplicate row with Lao ມາຕິນ ລູເທີ, which the latest text no longer has. The latest text was introduced by 39f3baf0 (2026-08-10, "QA2 GC11"), and copy A holds it.

2.B.23. Germany (copy B). Lao in copy B: ປະເທດເຢຍລະມັນ / ເຢຍລະມັນ. Lao in the latest text: ປະເທດເຢຍລະມັນ / ເຢຍລະມັນ / ອານາຈັກເຢຍລະມັນ. The Notes cell differs as well. The latest text was introduced by 39f3baf0 (2026-08-10, "QA2 GC11"), and copy A holds it.

2.B.24. Philip II (copy B). Lao in copy B: ຟີລິບທີ 2. Lao in the latest text: ກະສັດຟີລິບທີ 2 / ຟີລິບທີ 2. The Notes cell differs as well. The latest text was introduced by 39f3baf0 (2026-08-10, "QA2 GC11"), and copy A holds it.

2.B.25. Barnes (copy B). Lao in copy B: ບາເນດ. Lao in the latest text: ບານສ໌. The Notes cell differs as well. The latest text was introduced by 8c2e778d (2026-08-14, "QA2 GC21 with updated glossary and terms"), and copy A holds it.

2.B.26. Cranmer (copy B). Lao in copy B: ເຄນເມີ. Lao in the latest text: ເຄຼນເມີ. The Notes cell differs as well. The latest text was introduced by 1577a3e2 (2026-08-28, "Sidequests"), and copy A holds it.

2.B.27. Martyn (copy B). Copy B holds 2 rows under this head and the latest text holds 1. The row with Lao ມາຕິນ differs from the latest only in its Notes cell. Copy B also holds an older duplicate row with Lao ມາຕິນ, which the latest text no longer has. The latest text was introduced by 95b34852 (2026-08-12, "Update terms and glossary"), and copy A holds it.

2.B.28. Bancroft (copy B). Lao in copy B: ບານຄອຟ. Lao in the latest text: ບານຄຣອບ. The Notes cell differs as well. The latest text was introduced by 95b34852 (2026-08-12, "Update terms and glossary"), and copy A holds it.

2.B.29. Eusebius (copy B). The Lao cell is the same in both: ເອີເຊບິອັດ. Only the Notes cell differs. The latest text was introduced by ee49c657 (2026-08-21, "QA2 GC39"), and copy A holds it.

2.B.30. Peter II of Aragon (copy B). Lao in copy B: ເປໂຕທີ 2 ແຫ່ງອາຣາກົງ. Lao in the latest text: ປີເຕີທີ 2 ແຫ່ງອາຣາກອນ. The Notes cell differs as well. The latest text was introduced by ee49c657 (2026-08-21, "QA2 GC39"), and copy A holds it.

2.B.31. Abyssinia / Ethiopia (copy B). Lao in copy B: ເອທິໂອເປຍ. Lao in the latest text: ເອທີໂອເປຍ. The Notes cell differs as well. The latest text was introduced by 39f3b71c (2026-08-13, "QA2 GC20 with side effect updates"), and copy A holds it.

2.B.32. Stephen (copy B). Lao in copy B: ສະເຕຟາໂນ. Lao in the latest text: ຊະເຕຟາໂນ. The Notes cell differs as well. The latest text was introduced by 39f3b71c (2026-08-13, "QA2 GC20 with side effect updates"), and copy A holds it.

2.B.33. Priest / Priests / Priesthood / Priestly (copy B). Lao in copy B: ບາດຫຼວງ / ປະໂຣຫິດ / ມະຫາປະໂຣຫິດ. Lao in the latest text: ບາດຫຼວງ / ປະໂຣຫິດ / ມະຫາປະໂຣຫິດ / ຜູ້ນຳສາສະໜາ. The Notes cell differs as well. The latest text was introduced by 39f3b71c (2026-08-13, "QA2 GC20 with side effect updates"), and copy A holds it.

2.B.34. Monk / Monks / Monkish (copy B). The Lao cell is the same in both: ນັກບວດ. Only the Notes cell differs. The latest text was introduced by 1577a3e2 (2026-08-28, "Sidequests"), and copy A holds it.

2.B.35. Friar / Friars (copy B). Lao in copy B: ພຣະກາໂຕລິກ. Lao in the latest text: ພຣະກາໂຕລິກ / ນັກບວດ. The Notes cell differs as well. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.36. Religious order (copy B). The Lao cell is the same in both: ຄະນະນັກບວດ. Only the Notes cell differs. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.37. Clergy (copy B). Lao in copy B: ນັກບວດ / ບາດຫຼວງ / ຜູ້ນຳຄຣິສຕະຈັກ / ສາສະໜາຈານ. Lao in the latest text: ບາດຫຼວງ / ຜູ້ນຳຄຣິສຕະຈັກ / ສາສະໜາຈານ / ຜູ້ສອນສາສະໜາ / ຜູ້ນຳສາສະໜາ. The Notes cell differs as well. The latest text was introduced by 6580f735 (2026-08-21, "QA2 GC37"), and copy A holds it.

2.B.38. Minister / Ministers / Pastor / Pastors (copy B). Lao in copy B: ສາສະໜາຈານ. Lao in the latest text: ສາສະໜາຈານ default and general; ອາຈານປະຈຳໂບດ where the context makes it the better reading. The Notes cell differs as well. The latest text was introduced by ee49c657 (2026-08-21, "QA2 GC39"), and copy A holds it.

2.B.39. Prelate / Prelates / Ecclesiastic / Ecclesiastics (copy B). Lao in copy B: ຜູ້ນຳຄຣິສຕະຈັກ. Lao in the latest text: optional plural marker + ຜູ້ນຳຄຣິສຕະຈັກ + optional Rome tail; attested ຜູ້ນຳຄຣິສຕະຈັກ / ພວກຜູ້ນຳຄຣິສຕະຈັກ / ຜູ້ນຳຄຣິສຕະຈັກໂຣມ / ຜູ້ນຳຄຣິສຕະຈັກຝ່າຍໂຣມ / ຜູ້ນຳຄຣິສຕະຈັກຝ່າຍສັນຕະປາປາ. The Notes cell differs as well. The latest text was introduced by 1577a3e2 (2026-08-28, "Sidequests"), and copy A holds it.

2.B.40. Parish minister / churchman (copy B). The Lao cell is the same in both: ອາຈານປະຈຳໂບດ. Only the Notes cell differs. The latest text was introduced by ee49c657 (2026-08-21, "QA2 GC39"), and copy A holds it.

2.B.41. Idolater / Idolaters (copy B). Lao in copy B: ຄົນທີ່ຂາບໄຫວ້ຮູບເຄົາລົບ. Lao in the latest text: ຄົນ / ຜູ້ / ພວກ / ຊົນຊາດ + ຂາບໄຫວ້ ຫຼື ນັບຖື + ຮູບເຄົາລົບ. The Notes cell differs as well. The latest text was introduced by 1577a3e2 (2026-08-28, "Sidequests"), and copy A holds it.

2.B.42. prophet (Jewish, Christian) (copy B). Copy B holds 2 rows under this head and the latest text holds 2. One of them is the same in both. The row with Lao Correct ຜູ້ເຜີຍພຣະທຳ, Incorrect ຜູ້ທຳນວາຍ differs from the latest only in its Notes cell. The latest text was introduced by ee49c657 (2026-08-21, "QA2 GC39"), and copy A holds it.

2.B.43. National Assembly (French Rev.) (copy B). Lao in copy B: ສະພາແຫ່ງຊາດ. Lao in the latest text: ກອງປະຊຸມແຫ່ງຊາດ. The Notes cell differs as well. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.44. National Convention (French Rev.) (copy B). The Lao cell is the same in both: ກອງປະຊຸມແຫ່ງຊາດ. Only the Notes cell differs. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.45. Church dignitaries (copy B). Lao in copy B: ເຈົ້າໜ້າທີ່ຂອງຄຣິສຕະຈັກ / ເຈົ້າໜ້າທີ່ຄຣິສຕະຈັກ. Lao in the latest text: ເຈົ້າໜ້າທີ່ຂອງຄຣິສຕະຈັກ / ເຈົ້າໜ້າທີ່ຄຣິສຕະຈັກ / ຜູ້ນຳຄຣິສຕະຈັກ. The Notes cell differs as well. The latest text was introduced by 1577a3e2 (2026-08-28, "Sidequests"), and copy A holds it.

2.B.46. Young / Youth (copy B). Lao in copy B: ຊົນໜຸ່ມ / ຊາວໜຸ່ມ / ໜຸ່ມສາວ. Lao in the latest text: ຊາວໜຸ່ມ / ຄົນໜຸ່ມ / ໜຸ່ມສາວ. The Notes cell is the same. The latest text was introduced by 6580f735 (2026-08-21, "QA2 GC37"), and copy A holds it.

2.B.47. Christendom (copy B). Lao in copy B: ຄົນໃນປະເທດຕ່າງໆທີ່ນັບຖືສາສະໜາຄຣິສ / ທຸກປະເທດທີ່ມີການນັບຖືສາສະໜາຄຣິສ / ທຸກປະເທດທີ່ນັບຖືສາສະໜາຄຣິສ / ປະເທດທັງຫຼາຍທີ່ນັບຖືສາສະໜາຄຣິສ / ບັນດາປະເທດທີ່ນັບຖືສາສະໜາຄຣິສ. Lao in the latest text: form follows the passage's sense. The Notes cell differs as well. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.48. Section (citation) (copy B). Lao in copy B: ໝວດ. Lao in the latest text: ໝວດ / ຂໍ້. The Notes cell differs as well. The latest text was introduced by 2e9db5a7 (2026-08-19, "QA2 GC34"), and copy A holds it.

2.B.49. Paragraph (citation) (copy B). The Lao cell is the same in both: ວັກ. Only the Notes cell differs. The latest text was introduced by 2e9db5a7 (2026-08-19, "QA2 GC34"), and copy A holds it.

2.B.50. Church Father (early) (copy B). Lao in copy B: ຜູ້ນຳລຸ້ນບຸກເບີກຂອງຄຣິສຕະຈັກ / ບັນດານັກຂຽນຄຣິສຕຽນໃນສະຕະວັດຕົ້ນໆ. Lao in the latest text: ບັນດາ/ພວກ/ເຫຼົ່າ + ນັກຂຽນຄຣິສຕຽນ + tail; anaphoric short form ນັກຂຽນ + tail, only after the long form is established in the chapter. The Notes cell differs as well. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.51. Magistrate / city dignitary (copy B). The Lao cell is the same in both: ເຈົ້າເມືອງ. Only the Notes cell differs. The latest text was introduced by 66c183eb (2026-08-11, "Update instructions"), and copy A holds it.

2.B.52. Prince / princes (within a kingdom) (copy B). Lao in copy B: ຂຸນນາງ. Lao in the latest text: ຂຸນນາງ / ເຈົ້າຊາຍ. The Notes cell differs as well. The latest text was introduced by ee49c657 (2026-08-21, "QA2 GC39"), and copy A holds it.

2.B.53. Castle (copy B). Lao in copy B: ຜາສາດ. Lao in the latest text: ຜາສາດຫີນ. The Notes cell differs as well. The latest text was introduced by a041af41 (2026-08-11, "Fix spelling GC14"), and copy A holds it.

2.B.54. Scaffold (heretic execution) (copy B). The Lao cell is the same in both: ຫຼັກປະຫານ. Only the Notes cell differs. The latest text was introduced by 2263281d (2026-08-11, "Update terms and instructions"), and copy A holds it.

2.B.55. Decretal / Decretals (copy B). The Lao cell is the same in both: ຄຳຕັດສິນຂອງສັນຕະປາປາ / ຄຳຕັດສິນ. Only the Notes cell differs. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.56. Papal bull (copy B). Lao in copy B: ໃບປະກາດພິເສດຂອງສັນຕະປາປາ / ໃບປະກາດພິເສດ. Lao in the latest text: ໃບປະກາດພິເສດຂອງສັນຕະປາປາ / ໃບປະກາດພິເສດ / ຄຳປະກາດ. The Notes cell differs as well. The latest text was introduced by 0ce8ecb6 (2026-09-02, "Last minute tweaking from glossary sidequests"), and copy A holds it.

2.B.57. Fanatic / Fanatics / Fanaticism (copy B). Lao in copy B: ພວກທີ່ຄັ່ງໄຄ້ / ຄວາມຄັ່ງໄຄ້. Lao in the latest text: ຄັ່ງໄຄ້ / ຄັ່ງສາສະໜາ / ຄັ່ງໄຄ້ສາສະໜາ / ຄັ່ງໄຄ້ຫຼົງໄຫຼ / ບ້າສາສະໜາ. The Notes cell differs as well. The latest text was introduced by ee49c657 (2026-08-21, "QA2 GC39"), and copy A holds it.

2.B.58. Duke (copy B). Copy B holds 2 rows under this head and the latest text holds 1. The row with Lao ທ່ານດະຍຸກ differs from the latest only in its Notes cell. Copy B also holds an older duplicate row with Lao ທ່ານດະຍຸກ, which the latest text no longer has. The latest text was introduced by 39f3baf0 (2026-08-10, "QA2 GC11"), and copy A holds it.

## 3. Heads that exist in some version but are missing from a copy on origin/main

3.A. Copy A lacks 32 heads. Every one was renamed, split or merged into a row that copy A holds, and in 29 of the 32 the successor row first appeared in the same commit that removed the old head. None is a loss. Each line gives the last text, the removing commit and the successor in copy A.

3.A.1. Paganism. The last text was "| Paganism | ລັດທິຂາບໄຫວ້ຮູບເຄົາລົບ | Descriptive rendering |", last present in 0bed167d (2026-04-02, "Pre-edit round of AA05 (#705)"). It was removed by 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). Copy A holds the successor row "Paganism (the religious system)". Copy B does not hold this head either. The same commit added the interim head Paganism (the system), which 1577a3e2 (2026-08-28, "Sidequests") replaced with the row now in copy A.

3.A.2. Idol worship. The last text was "| Idol worship | ການຂາບໄຫວ້ຮູບເຄົາລົບ |  |", last present in 0bed167d (2026-04-02, "Pre-edit round of AA05 (#705)"). It was removed by 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). Copy A holds the successor row "Idolatry / image worship (the practice)". Copy B does not hold this head either. The same commit added the interim head Idolatry / image worship, which 1577a3e2 (2026-08-28, "Sidequests") replaced with the row now in copy A.

3.A.3. Mendicant friars. The last text was "| Mendicant friars | ພວກພຣະກາໂຕລິກ | Generic "Catholics" used |", last present in 0bed167d (2026-04-02, "Pre-edit round of AA05 (#705)"). It was removed by 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). Copy A holds the successor row "Friar / Friars". Copy B does not hold this head either.

3.A.4. Excommunication. The last text was "| Excommunication | ການຕັດຊື່ອອກຈາກຄຣິສຕະຈັກ | [CHECK] Descriptive |", last present in 784c1e8c (2026-08-04, "Audit glossary"). It was removed by 7ddba2d7 (2026-08-05, "Update glossary"). Copy A holds the successor row "Excommunication / Excommunicate". Copy B does not hold this head either.

3.A.5. Priest. The last text was "| Priest | ປະໂຣຫິດ |  |", last present in 0bed167d (2026-04-02, "Pre-edit round of AA05 (#705)"). It was removed by 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). Copy A holds the successor row "Priest / Priests / Priesthood / Priestly". Copy B does not hold this head either.

3.A.6. Advocate / Intercessor. The last text was "| Advocate / Intercessor | ຜູ້ວິງວອນ / ຜູ້ອ້ອນວອນ / ຜູ້ແກ້ຄວາມ | [CHECK] Context determines choice |", last present in a041af41 (2026-08-11, "Fix spelling GC14"). It was removed by 31914edb (2026-08-11, "Update glossary"). Copy A holds the successor rows "Advocate" and "Intercessor". Copy B still holds this head.

3.A.7. Lamb (Rev./salvific). The last text was "| Lamb (Rev./salvific) | ພຣະເມສານ້ອຍ | [tentative] |", last present in 0bed167d (2026-04-02, "Pre-edit round of AA05 (#705)"). It was removed by 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). Copy A holds the successor row "Lamb (Rev. and salvific)". Copy B does not hold this head either.

3.A.8. Vicar of Christ. The last text was "| Vicar of Christ | ຜູ້ແທນຂອງພຣະຄຣິສ | [CHECK] NOT ຕົວແທນ (reserved for legate and generic representative). Also renders "vicegerent." GC 140.4 |", last present in 2e9db5a7 (2026-08-19, "QA2 GC34"). It was removed by 6580f735 (2026-08-21, "QA2 GC37"). Copy A holds the successor row "Vicar of Christ / vicegerent (papal title)". Copy B still holds this head.

3.A.9. Monastery / Convent. The last text was "| Monastery / Convent | ສຳນັກສົງ / ສຳນັກແມ່ຊີ | [tentative] |", last present in 0bed167d (2026-04-02, "Pre-edit round of AA05 (#705)"). It was removed by 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). Copy A holds the successor rows "Monastery / Monasteries / Cloister / Cloisters" and "Convent / Convents". Copy B does not hold this head either.

3.A.10. Realm of the dead. The last text was "| Realm of the dead | ແດນມໍຣະນາ |  | ຣ root; used for Sheol/grave |", last present in 23bfd623 (2026-08-04, "Update glossary"). It was removed by 784c1e8c (2026-08-04, "Audit glossary"). Copy A holds the successor row "Sheol / Grave (realm of dead)". Copy B does not hold this head either. Realm of the dead was a second head for the same Lao as the Sheol / Grave row, which already existed; the same commit added the note "ຣ root" to the Sheol / Grave row.

3.A.11. Cestius Gallus. The last text was "| Cestius Gallus | ໄກອຸສ ເຊຕຽວ ກາລຸສ | Short: ແມ່ທັບເຊຕຽວ |", last present in 0bed167d (2026-04-02, "Pre-edit round of AA05 (#705)"). It was removed by 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). Copy A holds the successor row "Cestius Gallus / Cestius". Copy B does not hold this head either.

3.A.12. Ornan. The last text was "| Ornan | ອາໂຣນາ |  |", last present in 0bed167d (2026-04-02, "Pre-edit round of AA05 (#705)"). It was removed by 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). Copy A holds the successor row "Ornan / Araunah". Copy B does not hold this head either.

3.A.13. Münster. The last text was "| Münster | ມຸນສະເຕີ | [tentative] |", last present in 0bed167d (2026-04-02, "Pre-edit round of AA05 (#705)"). It was removed by 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). Copy A holds the successor row "Münster / Munsterites". Copy B does not hold this head either.

3.A.14. Würtemberg. The last text was "| Würtemberg | ເວີດເທັມເບີກ | [CHECK] |", last present in 8dbfdd00 (2026-08-12, "QA2 GC17 and GC19"). It was removed by 39f3b71c (2026-08-13, "QA2 GC20 with side effect updates"). Copy A holds the successor row "Württemberg". Copy B still holds this head.

3.A.15. Tatary. The last text was "| Tatary | ຕາຕາຣີ | [CHECK] |", last present in 8dbfdd00 (2026-08-12, "QA2 GC17 and GC19"). It was removed by 39f3b71c (2026-08-13, "QA2 GC20 with side effect updates"). Copy A holds the successor row "Tatary / Tatar". Copy B still holds this head.

3.A.16. Edward A. Park. The last text was "| Edward A. Park | ເອັດເວີດ ເອ. ພາກ | [CHECK] GC 465.2 |", last present in e6740a6e (2026-08-16, "QA2 GC26"). It was removed by f51eaa81 (2026-08-17, "QA2 GC28"). Copy A holds the successor row "Edwards A. Park". Copy B still holds this head.

3.A.17. Paganism (the system). The last text was "| Paganism (the system) | ລັດທິນອກສາສະໜາ | [CHECK] Never the idol phrase. 549.2 |", last present in ea5de9e8 (2026-08-26, "Update Vicor/Representative of Christ"). It was removed by 1577a3e2 (2026-08-28, "Sidequests"). Copy A holds the successor row "Paganism (the religious system)". Copy B still holds this head.

3.A.18. Pagan (attributive). The last text was "| Pagan (attributive) | ນອກສາສະໜາ | ຂອງຄົນນອກສາສະໜາ pattern, 574.1 |", last present in ea5de9e8 (2026-08-26, "Update Vicor/Representative of Christ"). It was removed by 1577a3e2 (2026-08-28, "Sidequests"). Copy A holds the successor row "Pagan / heathen (person or attributive)". Copy B still holds this head.

3.A.19. Pagan / heathen (person). The last text was "| Pagan / heathen (person) | ຄົນນອກສາສະໜາ / ຄົນທີ່ນັບຖືສາສະໜາອື່ນ / ຄົນທີ່ບໍ່ນັບຖືພຣະເຈົ້າ | [CHECK] Context chooses |", last present in ea5de9e8 (2026-08-26, "Update Vicor/Representative of Christ"). It was removed by 1577a3e2 (2026-08-28, "Sidequests"). Copy A holds the successor row "Pagan / heathen (person or attributive)". Copy B still holds this head.

3.A.20. Heathenism (tribal). The last text was "| Heathenism (tribal) | ນັບຖືຜີສາງນາງໄມ້ | Saxons only: 62.3, 63.1 |", last present in ea5de9e8 (2026-08-26, "Update Vicor/Representative of Christ"). It was removed by 1577a3e2 (2026-08-28, "Sidequests"). Copy A holds the successor row "Heathenism (tribal animism)". Copy B still holds this head.

3.A.21. Idolatry / image worship. The last text was "| Idolatry / image worship | ການຂາບໄຫວ້ຮູບເຄົາລົບ | [CHECK] |", last present in ea5de9e8 (2026-08-26, "Update Vicor/Representative of Christ"). It was removed by 1577a3e2 (2026-08-28, "Sidequests"). Copy A holds the successor row "Idolatry / image worship (the practice)". Copy B still holds this head.

3.A.22. Idol / Idols. The last text was "| Idol / Idols | ຮູບເຄົາລົບ | [CHECK] Religious category |", last present in ea5de9e8 (2026-08-26, "Update Vicor/Representative of Christ"). It was removed by 1577a3e2 (2026-08-28, "Sidequests"). Copy A holds the successor row "Idol / Idols / image (the object)". Copy B still holds this head.

3.A.23. Image (physical object). The last text was "| Image (physical object) | ຮູບປັ້ນ | Statue: 172.1, 174.3, 175.1 |", last present in ea5de9e8 (2026-08-26, "Update Vicor/Representative of Christ"). It was removed by 1577a3e2 (2026-08-28, "Sidequests"). Copy A holds the successor row "Idol / Idols / image (the object)". Copy B still holds this head.

3.A.24. False god. The last text was "| False god | ພຣະທຽມ | 49.2, 53.3, 453.1 |", last present in ea5de9e8 (2026-08-26, "Update Vicor/Representative of Christ"). It was removed by 1577a3e2 (2026-08-28, "Sidequests"). Copy A holds the successor row "False god / false gods". Copy B still holds this head.

3.A.25. Legate / nuncio. The last text was "| Legate / nuncio | ຕົວແທນ / ຕົວແທນຂອງສັນຕະປາປາ / ທູດຂອງສັນຕະປາປາ | [CHECK] NOT ທະນາຍ; NOT bare ທູດ (collides with ທູດສະຫວັນ). Bare ຕົວແທນ anaphorically after ຕົວແທນຂອງສັນຕະປາປາ; ທູດຂອງສັນຕະປາປາ only where EN reads "ambassador," never at first mention in a chapter. GC 133.3, 135.1 |", last present in 2e9db5a7 (2026-08-19, "QA2 GC34"). It was removed by 6580f735 (2026-08-21, "QA2 GC37"). Copy A holds the successor row "Legate / nuncio / papal emissary". Copy B still holds this head.

3.A.26. Lawyer. The last text was "| Lawyer | ນັກກົດໝາຍ | [CHECK] ທະນາຍຄວາມ is courtroom-specific |", last present in 2e9db5a7 (2026-08-19, "QA2 GC34"). It was removed by 6580f735 (2026-08-21, "QA2 GC37"). Copy A holds the successor rows "Lawyer (legal profession)" and "Lawyer (teacher of the law of Moses)". Copy B still holds this head.

3.A.27. Territory (pre-modern). The last text was "| Territory (pre-modern) | ເຂດ / ສາຍພູ | [CHECK] NOT ແຂວງ (anachronism) |", last present in 31a388ac (2026-08-02, "Adding GC-glossary used for QA"). It was removed by 21668e5d (2026-08-03, "Update glossary"). Copy A holds the successor rows "Territory (pre-modern, terrain)" and "Territory (pre-modern, polity)". Copy B does not hold this head either.

3.A.28. Hierarchy (papal system). The last text was "| Hierarchy (papal system) | ລະບອບສັນຕະປາປາ | [CHECK] Same form as Papacy row |", last present in 66c183eb (2026-08-11, "Update instructions"). It was removed by 2263281d (2026-08-11, "Update terms and instructions"). Copy A holds the successor rows "Hierarchy (the papal system)" and "Hierarchy (persons, the body of church leaders)". Copy B still holds this head.

3.A.29. Duke / Margrave / Landgrave / Count palatine. The last text was "| Duke / Margrave / Landgrave / Count palatine | ເຈົ້າແຂວງ | [CHECK] Collapse to the class term; DEFER any sentence contrasting two of these ranks |", last present in 64132ed2 (2026-08-09, "Update glossary"). It was removed by 39f3baf0 (2026-08-10, "QA2 GC11"). Copy A holds the successor row "Margrave / Landgrave / Count palatine". Copy B still holds this head.

3.A.30. Royal deputies (envoys of kings). The last text was "| Royal deputies (envoys of kings) | ຄະນະຜູ້ແທນຂອງບັນດາກະສັດ | [CHECK] GC 108.2 |", last present in 2e9db5a7 (2026-08-19, "QA2 GC34"). It was removed by 6580f735 (2026-08-21, "QA2 GC37"). Copy A holds the successor row "Deputy / Deputies / Deputation (civil)". Copy B still holds this head. The Deputy row in copy A names ຄະນະຜູ້ແທນຂອງບັນດາກະສັດ for royal deputies in its Notes cell.

3.A.31. Romanists / Papists. The last text was "| Romanists / Papists | ພວກເຄັ່ງໃນລະບອບສັນຕະປາປາ / ພວກຄົນເຄັ່ງໃນລະບອບສັນຕະປາປາ / ພວກນິຍົມສັນຕະປາປາ | Both forms in use; variation accepted. NOT ພວກຝ່າຍສັນຕະປາປາ. GC 132.3, 135.2, 137.3, 143.1, 143.3 |", last present in 9fc0a762 (2026-08-11, "Reconcile penance"). It was removed by 66c183eb (2026-08-11, "Update instructions"). Copy A holds the successor rows "Romanist / Romanists (persons)" and "Papist / Papists (persons)". Copy B still holds this head.

3.A.32. Edict (imperial). The last text was "| Edict (imperial) | ຣາຊໂອງການ | [CHECK] Distinct from ຄຳສັ່ງ (papal decree, mandate); ຄຳປະກາດ retained at GC 202.1 only, where EN contrasts edict with imperial decree inside one clause. Attested GC 197.3, 202.1, 202.4, 203.1 |", last present in a5fd5cf0 (2026-08-18, "QA2 GC32"). It was removed by 2e9db5a7 (2026-08-19, "QA2 GC34"). Copy A holds the successor row "Edict (royal, imperial)". Copy B does not hold this head either.

3.B. Copy B lacks 217 heads. 204 of them are in copy A; each was first written after 2026-08-09, the date of copy B's text, so no commit removed them from copy B. They are listed in item 4.A. The other 13 are in neither copy; they are items 3.A.1, 3.A.2, 3.A.3, 3.A.4, 3.A.5, 3.A.7, 3.A.9, 3.A.10, 3.A.11, 3.A.12, 3.A.13, 3.A.27, 3.A.32 above, and each has its successor in copy A.

## 4. Heads present in one copy on origin/main and not the other

4.A. 204 heads are in copy A and not in copy B. Grouped by table:

4.A.1. main term table (48): Palace / Mansions; Palace (royal); Vicar of Christ / vicegerent (papal title); Lord of hosts; Almighty (divine title); the Majesty of heaven; Paganism (the religious system); Pagan / heathen (person or attributive); Heathenism (tribal animism); Idolatry / image worship (the practice); Idol / Idols / image (the object); False god / false gods; Image of God / of Christ; Apostolic Fathers; Apostolic days / Apostolic times / Apostolic age (the period); Romanist / Romanists (persons); Papist / Papists (persons); Hierarchy (the papal system); Hierarchy (persons, the body of church leaders); Intercessor; Advocate; Penance; Thousands; Prince of evil / prince of darkness / prince of angels / Prince of Peace / Messiah the Prince / prince of this world; Lawyer (legal profession); Lawyer (teacher of the law of Moses); Legate / nuncio / papal emissary; Christian world; Margrave / Landgrave / Count palatine; Deputy / Deputies / Deputation (civil); Edict (royal, imperial); Confession (Augsburg); Prince (sovereign, in address); Canton (Swiss); Lutheranism; Ambassador (secular envoy); In the capacity of / as (status); On the ground of (charge, offence); Calvinists; Justification by faith; Deist / Deists; Prophet (of another god); Elder / Elders (Jewish council); False sabbath / Spurious sabbath; Bow / bowed down (prostration); Moral / morality; Papal legate / pope's representative; Papal emissary / nuncio.

4.A.2. section 10, spelling (15): Hide / conceal; Diligence / Perseverance; Retinue / Entourage; Encyclopedia / Cyclopedia; Overthrow / fell; Rabbi; Adventure (book title); Low / humble; Magazine / Journal; Water (and AM generally); One another / each other; Palestine; Gamaliel; John the Baptist; kneel.

4.A.3. section 11, proper nouns (133): Ottoman; Württemberg; Tatary / Tatar; Edwards A. Park; Spires; Ferdinand; Simon Grynaeus; Faber; Heidelberg; Coburg; Edward VI; Morin; Italy; Europe; Zechariah (book); 1 Corinthians (book); Paul (the apostle); Palfrey / J. G. Palfrey; Neal / D. Neal; J. Brown; New England; Massachusetts / Massachusetts Bay Colony; Africa; Greenland; West Indies; Madeira; Norway; Ireland; Algiers; Morocco; Marrakesh; Cadiz; Patmos; Enoch; Job; Charles Lyell; Daniel T. Taylor; Salem; Falmouth; Connecticut; Albany; Exeter; New Hampshire; Nathanael Whittaker; Tabernacle church (Salem); R. M. Devens; William Gordon; Isaiah Thomas; Samuel Tenney; Massachusetts Historical Society Collections; Portugal; Bliss / S. Bliss; Gabriel; Cyrus; Darius; Sanhedrin; Cornelius; Caesarea; Elisha; Baptist Church; Silliman; F. Reed; New York; Josiah Litch; Ottoman Empire; Deacozes; Constantinople; Turkey; Bethlehem; Galilee; (periodical and newspaper titles); The Wesleys; Nineveh; James White / J. White; Philadelphia; Oberlin College; Religious Telescope; Babylon; Babel; Gavazzi; Howard Crosby; Washburn; Wisconsin; Robert Atkins; New York Independent; Charles Beecher; Indiana; Fort Wayne; Roman Empire (ancient); Assyria / Assyrian; Sennacherib; Capernaum; Philippi; Silas; Syrophoenician; Gadara / Gadarenes; Simon Magus; Elymas the sorcerer; Baal; Phoenicia; Jehovah; O'Connor / Bishop O'Connor; Second Vatican Council; Michael Geddes; John Dowling; January; February; March; April; May; June; July; August; September; October; November; December; A. E. Waffle; Barnas Sears; Cardinal Wiseman; Ezra Hall Gillett; Francis West; G. A. Townsend; George Elliott; Gerard Brandt; Henry Tuberville; J. N. Andrews; John Lewis; K. R. Hagenbach; Mgr. Segur; Robert Cox; Thomas Morer; W. H. D. Adams.

4.A.4. section 12, word-order pairs (8): ຫານກ້າ / ກ້າຫານ; ຊົມຊື່ນ / ຊື່ນຊົມ; ອົດທົນ / ທົນອົດ; ຊື່ສັດ / ສັດຊື່; ຫຸ້ມຫໍ່ / ຫໍ່ຫຸ້ມ; ປະປ່ອຍ / ປ່ອຍປະ; ກຳລັງເຫື່ອແຮງ / ເຫື່ອແຮງກຳລັງ; ພະຍາດໂຣຄາ / ໂຣຄາພະຍາດ.

4.B. 19 heads are in copy B and not in copy A. Each is a superseded head already listed in item 3: 3.A.6, 3.A.8, 3.A.14, 3.A.15, 3.A.16, 3.A.17, 3.A.18, 3.A.19, 3.A.20, 3.A.21, 3.A.22, 3.A.23, 3.A.24, 3.A.25, 3.A.26, 3.A.28, 3.A.29, 3.A.30, 3.A.31. One of them conflicts with a later ruling: copy B's row "| Vicar of Christ | ຜູ້ແທນຂອງພຣະຄຣິສ | [CHECK] NOT ຕົວແທນ (reserved for legate and generic representative). Also renders "vicegerent." GC 140.4 |" prescribes the form that copy A's Vicar of Christ row forbids ("DECIDED 26 August: NOT ຜູ້ແທນ").

4.C. Copy B has one malformed line. Line 467 holds two rows on one line: "| Frederick (the Elector) | ເຟຣເດີຣິກ | [CHECK] GC 138.1; ທ່ານ prefix | | Augustine | ອໍກັສຕິນ | [CHECK] GC 140.3 |". Copy A has the two rows on separate lines; 39f3baf0 (2026-08-10, "QA2 GC11") split them. This report counts the line as two rows.

## 5. Uncommitted copies

5.A. No uncommitted copy differs from every committed version.

5.B. In ~/claude-sandbox/wt-lao-glossary (branch restore-lao-gc-glossary), path B is byte-identical to blob 11a3d4e8. Path A does not exist there, because that branch tip, fa16ad02, has no path A.

5.C. In ~/claude-sandbox/wt-gc-instructions, path A is byte-identical to blob 6a516591 and path B is byte-identical to blob 11a3d4e8.

5.D. Neither folder showed a character-device mask.

5.E. I also checked every other GC-glossary.txt under ~/claude-sandbox and ~/programming. The worktrees wt-DA, wt-FB and wt-SC-qa2 and the checkouts translate, translate-lo-AA, translate-th-GC and translate-th-SC hold only blob 6a516591 or blob 11a3d4e8. ~/claude-sandbox/gc-audit/govcheck-baseline/GC-glossary.txt equals blob cf2d9a2a. Five test copies under ~/claude-sandbox/gc-audit/ (govcheck-test/sandbox, govcheck-test/repo, govcheck-test/pristine, deltest1, deltest2) match no committed file as a whole, but every row they hold appears in some committed version, so they carry no row text of their own.

## 6. Recommendation

6.A. Make lo/GC/04_assets/translation_profile/GC-glossary.txt (copy A) the single home of the glossary. It holds the latest text of every head. Every script and instruction that names a path on origin/main names path A: lo/FB/04_assets/scripts/fb_check.py:28, lo/FB/04_assets/scripts/fb_packet.py:26, lo/FB/CLAUDE.md:21 and lo/assets/translation_profile/lao-glossary.txt:3, and on GC-instructions the gc-batch-auditor, gc-glossary-merge, gc-qa3-reader and gc-resolve-check agents.

6.B. Rows to bring forward into copy A: 0. No head in copy B, in any other committed version or in any uncommitted copy holds a text newer than copy A's.

6.C. Retire copy B. The only reference to path B on origin/main is the Edit permission at .claude/settings.json:37, which should name path A instead; that line is a proposal for the translator. The translator removes the file with this command:

    git rm lo/assets/translation_profile/GC-glossary.txt
