# Gold facts — real curriculum PDFs (for `tests/eval_answers.jsonl`)

Source: `tests/fixtures/chunks.jsonl` built by `scripts/build_fixtures.py` from `data/raw/`
(AIT.pdf → AIT, DSBA.pdf → DSBA, IT_inter2565.pdf → BIT, IT2565.pdf → IT).
**Every `value` and `quote` is copied from the chunk text** (after PUA repair) — nothing is
inferred or computed. `page` is the 1-based PDF page. Spelling oddities (`ระยะเวลการศึกษา`,
`สรางเสนห์`, `เชิงเส่น`) are in the source PDFs and are kept as-is.

Conventions: `NOT IN DOC` = the fact is absent from all four PDFs (checked on the full extracted
text, not only the fixtures). `IN DOC, NOT IN FIXTURE` = present in the PDF but not in a selected
chunk, so it must not be used in the eval. ☑/☐ are the document's own checkboxes.

## AIT — สาขาวิชาเทคโนโลยีปัญญาประดิษฐ์ (AIT.pdf)

| program | fact | value | page | chunk_id | quote (≤ 15 words) |
|---|---|---|---|---|---|
| AIT | program name (TH) | หลักสูตรวิทยาศาสตรบัณฑิตสาขาวิชาเทคโนโลยีปัญญาประดิษฐ์ | 2 | AIT-p2-c2 | ชื่อภาษาไทย หลักสูตรวิทยาศาสตรบัณฑิตสาขาวิชาเทคโนโลยีปัญญาประดิษฐ์ |
| AIT | program name (EN) | Bachelor of Science Program in Artificial Intelligence Technology | 2 | AIT-p2-c2 | ชื่อภาษาอังกฤษ Bachelor of Science Program in Artificial Intelligence Technology |
| AIT | degree full (TH) | วิทยาศาสตรบัณฑิต(เทคโนโลยีปัญญาประดิษฐ์) | 2 | AIT-p2-c3 | ชื่อเต็ม(ภาษาไทย) : วิทยาศาสตรบัณฑิต(เทคโนโลยีปัญญาประดิษฐ์) |
| AIT | degree full (EN) | Bachelor of Science (Artificial Intelligence Technology) | 2 | AIT-p2-c3 | (ภาษาอังกฤษ) : Bachelor of Science (Artificial Intelligence Technology) |
| AIT | degree abbr (TH / EN) | วท.บ. (เทคโนโลยีปัญญาประดิษฐ์) / B.Sc. (Artificial Intelligence Technology) | 2 | AIT-p2-c3 | ชื่อย่อ(ภาษาไทย) : วท.บ. (เทคโนโลยีปัญญาประดิษฐ์) |
| AIT | curriculum year | หลักสูตรใหม่ พ.ศ. 2566 | 2 | AIT-p2-c1 | หลักสูตรใหม่พ.ศ. 2566 |
| AIT | total credits | 120 หน่วยกิต | 2 | AIT-p2-c5 (also AIT-p12-c1) | 4. จำนวนหน่วยกิตที่เรียนตลอดหลักสูตร 120 หน่วยกิต |
| AIT | duration | 4 ปี (☑ หลักสูตรปริญญาตรี4 ปี) | 2 | AIT-p2-c6 | ☑ หลักสูตรปริญญาตรี4 ปี ☐ หลักสูตรปริญญาตรี5 ปี |
| AIT | opening | เดือนกรกฎาคม พ.ศ. 2566 (ภาคการศึกษาที่ 1/2566), หลักสูตรใหม่ | 4 | AIT-p4-c1 | กำหนดเปิดสอนเดือนกรกฎาคมพ.ศ. 2566 (ภาคการศึกษาที่1/2566) |
| AIT | language of instruction | ภาษาไทยและภาษาอังกฤษ | 3 | AIT-p3-c1 | ☑ หลักสูตรจัดการศึกษาเป็นภาษาไทยและภาษาอังกฤษ |
| AIT | admission requirements | ม.ปลายหรือเทียบเท่า/เทียบโอน; สอบคัดเลือกตามเกณฑ์ สกอ. หรือรับตรง | 10 | AIT-p10-c1 | สำเร็จการศึกษาระดับมัธยมศึกษาตอนปลายหรือเทียบเท่า … หรือผ่านการคัดเลือก(รับตรง) |
| AIT | year 1 sem 1 courses | 06046400 แคลคูลัส1; 06046402 พีชคณิตเชิงเส้น; 06066000 คณิตศาสตร์ไม่ต่อเนื่อง; 06066001 ความน่าจะเป็นและสถิติ; 06066303 การแก้ปัญหาและการโปรแกรมคอมพิวเตอร์; 90641008 พื้นฐานทักษะการสื่อสารภาษาอังกฤษ | 17 | AIT-p17-c1 | ปีที่1 ภาคการศึกษาที่1 … 06046400 แคลคูลัส1 CALCULUS 1 |
| AIT | year 1 sem 1 total | 15 หน่วยกิต | 17 | AIT-p17-c1 | รวม 15 |
| AIT | year 1 sem 2 courses (partial in chunk) | 06046401 แคลคูลัส2; 06046403 การโปรแกรมคอมพิวเตอร์ | 17 | AIT-p17-c1 | ปีที่1 ภาคการศึกษาที่2 … 06046401 แคลคูลัส2 CALCULUS 2 |
| AIT | structure: ศึกษาทั่วไป / เฉพาะ / เลือกเสรี | 24 / 90 / 6 หน่วยกิต | 12 | AIT-p12-c2 | ก. หมวดวิชาศึกษาทั่วไป 24 หน่วยกิต ข. หมวดวิชาเฉพาะ 90 หน่วยกิต |
| AIT | careers (first three) | (1) นักวิทยาศาสตร์ด้านการเรียนรู้เชิงลึก (2) นักวิทยาศาสตร์หรือวิศวกรข้อมูล (3) ผู้พัฒนาระบบธุรกิจอัจฉริยะ; also (4) วิศวกรการเรียนรู้ของเครื่อง | 4 | AIT-p4-c2 | (1) นักวิทยาศาสตร์ด้านการเรียนรู้เชิงลึก (2) นักวิทยาศาสตร์หรือวิศวกรข้อมูล |
| AIT | course description 1 | 06046400 แคลคูลัส1 (CALCULUS 1) — วิชาบังคับก่อน: ไม่มี | 236 | AIT-p236-c1 | 06046400 แคลคูลัส1 CALCULUS 1 วิชาบังคับก่อน: ไม่มี |
| AIT | course description 2 | 06046401 แคลคูลัส2 (CALCULUS 2) — วิชาบังคับก่อน: 06046400 แคลคูลัส1 | 236 | AIT-p236-c2 | วิชาบังคับก่อน: 06046400 แคลคูลัส1 PREREQUISITE : 06046400 CALCULUS 1 |
| AIT | majors / tracks | ไม่มี | 2 | AIT-p2-c4 | 3. วิชาเอกหรือความเชี่ยวชาญเฉพาะของหลักสูตร(ถ้ามี) - ไม่มี- |
| AIT | cost per head (budget, **not tuition**) | เฉลี่ย 68,660 บาท/คน/ปี | 11 | AIT-p11-c2 | ประมาณค่าใช้จ่ายต่อหัวในการผลิตบัณฑิตตามหลักสูตรนี้เฉลี่ย68,660 บาท/คน/ปี |
| AIT | tuition fee / ค่าเทอม | NOT IN DOC | — | — | (no ค่าธรรมเนียม / ค่าเทอม / ค่าเล่าเรียน anywhere in AIT.pdf) |

## DSBA — สาขาวิชาวิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ (DSBA.pdf)

| program | fact | value | page | chunk_id | quote (≤ 15 words) |
|---|---|---|---|---|---|
| DSBA | program name (TH) | หลักสูตรวิทยาศาสตรบัณฑิตสาขาวิชาวิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ | 2 | DSBA-p2-c2 | หลักสูตรวิทยาศาสตรบัณฑิตสาขาวิชาวิทยาการข้อมูลและการวิเคราะห์ เชิงธุรกิจ |
| DSBA | program name (EN) | Bachelor of Science Program in Data Science and Business Analytics | 2 | DSBA-p2-c2 | ชื่อภาษาอังกฤษBachelor of Science Program in Data Science and Business Analytics |
| DSBA | degree full (TH) | วิทยาศาสตรบัณฑิต(วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ) | 2 | DSBA-p2-c3 | ชื่อเต็ม(ภาษาไทย) : วิทยาศาสตรบัณฑิต(วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ) |
| DSBA | degree full (EN) | Bachelor of Science (Data Science and Business Analytics) | 2 | DSBA-p2-c3 | : Bachelor of Science (Data Science and Business Analytics) |
| DSBA | degree abbr (TH / EN) | วท.บ. (วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ) / B.Sc. (Data Science and Business Analytics) | 2 | DSBA-p2-c3 | : วท.บ. (วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ) |
| DSBA | curriculum year | หลักสูตรปรับปรุง พ.ศ. 2565 | 2 | DSBA-p2-c1 | หลักสูตรปรับปรุงพ.ศ. 2565 |
| DSBA | total credits | 132 หน่วยกิต | 2 | DSBA-p2-c5 (also DSBA-p14-c1) | 4. จำนวนหน่วยกิตที่เรียนตลอดหลักสูตร 132 หน่วยกิต |
| DSBA | duration | 4 ปี | 3 | DSBA-p3-c1 | 5.1 รูปแบบ ☑ หลักสูตรปริญญาตรี4 ปี |
| DSBA | opening | เดือนสิงหาคม พ.ศ. 2565, หลักสูตรปรับปรุง | 3 | DSBA-p3-c3 | ☑ หลักสูตรปรับปรุง กำหนดเปิดสอนเดือนสิงหาคมพ.ศ. 2565 |
| DSBA | language of instruction | ภาษาไทยและภาษาอังกฤษ | 3 | DSBA-p3-c2 | ☑ หลักสูตรจัดการศึกษาเป็นภาษาไทยและภาษาอังกฤษ |
| DSBA | admission requirements | ม.ปลายหรือเทียบเท่า; ผ่านการคัดเลือกตามเกณฑ์ของสำนักงานคณะกรรมการอุดมศึกษา และ/หรือระเบียบของสถาบันฯ | 12 | DSBA-p12-c1 | สำเร็จการศึกษาระดับมัธยมศึกษาตอนปลายหรือเทียบเท่าโดยผ่านการคัดเลือกตามเกณฑ์ของ สำนักงานคณะกรรมการอุดมศึกษา |
| DSBA | year 1 sem 1 courses | 06026200 แคลคูลัส1; 06026202 พีชคณิตเชิงเส้น; 06066101 พื้นฐานทางธุรกิจสำหรับเทคโนโลยีสารสนเทศ; 06066303 การแก้ปัญหาและการโปรแกรมคอมพิวเตอร์; 90641001 โรงเรียนสร้างเสน่ห์; 90641003 กีฬาและนันทนาการ; 90644007 ภาษาอังกฤษพื้นฐาน1 | 22 | DSBA-p22-c1 | ปีที่1 ภาคการศึกษาที่1 … 06026200 แคลคูลัส1 CALCULUS 1 |
| DSBA | year 1 sem 1 total | 18 หน่วยกิต | 22 | DSBA-p22-c1 | รวม 18 |
| DSBA | structure: ศึกษาทั่วไป / เฉพาะ / เลือกเสรี | 30 / 96 / 6 หน่วยกิต | 14 | DSBA-p14-c2, DSBA-p14-c3 | ก. หมวดวิชาศึกษาทั่วไป 30 หน่วยกิต … ข. หมวดวิชาเฉพาะ 96 หน่วยกิต |
| DSBA | specialised groups (12 หน่วยกิต, choose one) | กลุ่มวิทยาการข้อมูล / กลุ่มการวิเคราะห์เชิงสถิติ / กลุ่มวิศวกรรมข้อมูล | 14 | DSBA-p14-c2, DSBA-p14-c3 | นักศึกษาเลือกลงทะเบียนเรียนวิชาในกลุ่มวิชาชีพเฉพาะด้านกลุ่มใดกลุ่มหนึ่งจำนวนรวม12 หน่วยกิต |
| DSBA | careers (first three) | 1) นักวิทยาการข้อมูล(Data Scientist) 2) นักวิเคราะห์ข้อมูล(Data Analyst) 3) วิศวกรข้อมูล(Data Engineer); also 4) วิศวกรการเรียนรู้ของเครื่อง(Machine Learning Engineer) | 3–4 | DSBA-p3-c4, DSBA-p4-c1 | 1) นักวิทยาการข้อมูล(Data Scientist) 2) นักวิเคราะห์ข้อมูล(Data Analyst) |
| DSBA | course description 1 | 06026200 แคลคูลัส1 (CALCULUS 1) — วิชาบังคับก่อน: ไม่มี | 253 | DSBA-p253-c1 | 06026200 แคลคูลัส1 CALCULUS 1 วิชาบังคับก่อน: ไม่มี |
| DSBA | course description 2 | 06026201 แคลคูลัส2 (CALCULUS 2) — วิชาบังคับก่อน: 06026200 แคลคูลัส1 | 253 | DSBA-p253-c2 | วิชาบังคับก่อน: 06026200 แคลคูลัส1 |
| DSBA | course description 3 | 06066001 ความน่าจะเป็นและสถิติ (PROBABILITY AND STATISTICS) — วิชาบังคับก่อน: ไม่มี | 254 | DSBA-p254-c2 | 06066001 ความน่าจะเป็นและสถิติ PROBABILITY AND STATISTICS วิชาบังคับก่อน: ไม่มี |
| DSBA | majors / tracks | no majors; "จัดอยู่ในสาขาคอมพิวเตอร์(สาขาวิชาเทคโนโลยีสารสนเทศ)" | 2 | DSBA-p2-c4 | หลักสูตรนี้จัดอยู่ในสาขาคอมพิวเตอร์(สาขาวิชาเทคโนโลยีสารสนเทศ) |
| DSBA | cost per head (budget, **not tuition**) | เฉลี่ย 55,200 บาท/คน/ปี | 13 | DSBA-p13-c2 | ประมาณค่าใช้จ่ายต่อหัวในการผลิตบัณฑิตตามหลักสูตรนี้เฉลี่ย55,200 บาท/คน/ ปี |
| DSBA | tuition fee / ค่าเทอม | NOT IN DOC | — | — | — |

## BIT — สาขาวิชาเทคโนโลยีสารสนเทศทางธุรกิจ (หลักสูตรนานาชาติ) (IT_inter2565.pdf)

| program | fact | value | page | chunk_id | quote (≤ 15 words) |
|---|---|---|---|---|---|
| BIT | program name (TH) | หลักสูตรวิทยาศาสตรบัณฑิตสาขาวิชาเทคโนโลยีสารสนเทศทางธุรกิจ (หลักสูตรนานาชาติ) | 2 | BIT-p2-c2 | หลักสูตรวิทยาศาสตรบัณฑิตสาขาวิชาเทคโนโลยีสารสนเทศทางธุรกิจ (หลักสูตรนานาชาติ) |
| BIT | program name (EN) | Bachelor of Science in Business Information Technology (International Program) | 2 | BIT-p2-c2 | Bachelor of Science in Business Information Technology (International Program) |
| BIT | degree full (TH) | วิทยาศาสตรบัณฑิต(เทคโนโลยีสารสนเทศทางธุรกิจ) | 2 | BIT-p2-c3 | ชื่อเต็ม(ภาษาไทย) : วิทยาศาสตรบัณฑิต(เทคโนโลยีสารสนเทศทางธุรกิจ) |
| BIT | degree full (EN) | Bachelor of Science (Business Information Technology) | 2 | BIT-p2-c3 | : Bachelor of Science (Business Information Technology) |
| BIT | degree abbr (TH / EN) | วท.บ. (เทคโนโลยีสารสนเทศทางธุรกิจ) / B.Sc. (Business Information Technology) | 2 | BIT-p2-c3 | : วท.บ. (เทคโนโลยีสารสนเทศทางธุรกิจ) |
| BIT | curriculum year | หลักสูตรปรับปรุง พ.ศ. 2565 | 2 | BIT-p2-c1 | หลักสูตรปรับปรุงพ.ศ. 2565 |
| BIT | total credits | 126 หน่วยกิต | 2 | BIT-p2-c5 (also BIT-p14-c1) | 4. จำนวนหน่วยกิตที่เรียนตลอดหลักสูตร 126 หน่วยกิต |
| BIT | duration | 4 ปี | 2 | BIT-p2-c6 | 5.1 รูปแบบ ☑ หลักสูตรปริญญาตรี4 ปี |
| BIT | opening | เดือนสิงหาคม พ.ศ. 2565, หลักสูตรปรับปรุง | 3 | BIT-p3-c1 | ☑ หลักสูตรปรับปรุง กำหนดเปิดสอนเดือนสิงหาคมพ.ศ. 2565 |
| BIT | language of instruction | ภาษาอังกฤษ | 2 | BIT-p2-c7 | ☑ หลักสูตรจัดการศึกษาเป็นภาษาอังกฤษ |
| BIT | admission requirements | ม.ปลายหรือเทียบเท่า; ผ่านการคัดเลือกตามเกณฑ์ของสำนักงานคณะกรรมการอุดมศึกษา และ/หรือระเบียบของสถาบันฯ | 12 | BIT-p12-c1 | สำเร็จการศึกษาระดับมัธยมศึกษาตอนปลายหรือเทียบเท่าโดยผ่านการคัดเลือกตามเกณฑ์ของ สำนักงานคณะกรรมการอุดมศึกษา |
| BIT | year 1 sem 1 courses | 06036100 พื้นฐานทางด้านเทคโนโลยีสารสนเทศ; 06036101 คณิตศาสตร์สำหรับธุรกิจ; 06036118 การแก้ปัญหาทางด้านเทคโนโลยีสารสนเทศ; 96641001 โรงเรียนสรางเสนห์ [sic]; 96641003 กีฬาและนันทนาการ; 96644007 ภาษาอังกฤษพื้นฐาน1; 96644042 การสื่อสารและการนำเสนออยางมืออาชีพ [sic] | 22 | BIT-p22-c1 | ปีที่1 ภาคการศึกษาที่1 … 06036100 พื้นฐานทางด้านเทคโนโลยีสารสนเทศ INFORMATION TECHNOLOGY FUNDAMENTALS |
| BIT | year 1 sem 1 total | IN DOC, NOT IN FIXTURE (table cell after "รวม" was lost) | 22 | BIT-p22-c1 | รวม |
| BIT | structure: ศึกษาทั่วไป / เฉพาะ / เลือกเสรี | 30 / 90 / 6 หน่วยกิต | 14–15 | BIT-p14-c2, BIT-p15-c1 | ก. หมวดวิชาศึกษาทั่วไป 30 หน่วยกิต … ข. หมวดวิชาเฉพาะ 90 หน่วยกิต |
| BIT | elective groups (กลุ่มวิชาเลือก, 6 หน่วยกิต) | กลุ่มวิชาที่1 การวิเคราะห์เชิงธุรกิจ; ที่2 ระบบระดับองค์กร; ที่3 การตลาดเชิงดิจิทัล; ที่4 การออกแบบและพัฒนาส่วนติดต่อกับผู้ใช้งาน(UX/UI) | 15 | BIT-p15-c1 | กลุ่มวิชาที่1 : การวิเคราะห์เชิงธุรกิจ (Business Analysis) กลุ่มวิชาที่2 : ระบบระดับองค์กร |
| BIT | careers (groups) | กลุ่มอาชีพที่1 การวิเคราะห์เชิงธุรกิจ(Business Analysis) e.g. (1) นักวิเคราะห์ระบบเทคโนโลยีสารสนเทศ; ที่2 ระบบระดับองค์กร e.g. ที่ปรึกษาด้านERP; ที่3 การตลาดเชิงดิจิทัล(Digital Marketing); ที่4 UX/UI e.g. นักออกแบบUX/UI | 3 | BIT-p3-c2, BIT-p3-c3 | กลุ่มอาชีพที่1 : การวิเคราะห์เชิงธุรกิจ(Business Analysis) (1) นักวิเคราะห์ระบบเทคโนโลยีสารสนเทศ |
| BIT | course description 1 | 06036100 พื้นฐานทางด้านเทคโนโลยีสารสนเทศ (INFORMATION TECHNOLOGY FUNDAMENTALS) 3(2-2-5) — วิชาบังคับก่อน: ไม่มี | 187 | BIT-p187-c1 | 06036100 พื้นฐานทางด้านเทคโนโลยีสารสนเทศ 3(2-2-5) INFORMATION TECHNOLOGY FUNDAMENTALS วิชาบังคับก่อน: ไม่มี |
| BIT | course description 2 | 06036101 คณิตศาสตร์สำหรับธุรกิจ (MATHEMATICS FOR BUSINESS) 3(3-0-6) — วิชาบังคับก่อน: ไม่มี | 187 | BIT-p187-c2 | 06036101 คณิตศาสตร์สำหรับธุรกิจ 3(3-0-6) MATHEMATICS FOR BUSINESS |
| BIT | course description 3 | 06036102 การวิเคราะห์เชิงสถิติสำหรับธุรกิจ (STATISTICAL ANALYSIS FOR BUSINESS) 3(3-0-6) | 188 | BIT-p188-c1 | 06036102 การวิเคราะห์เชิงสถิติสำหรับธุรกิจ 3(3-0-6) STATISTICAL ANALYSIS FOR BUSINESS |
| BIT | majors / tracks | ไม่มี | 2 | BIT-p2-c4 | 3. วิชาเอกหรือความเชี่ยวชาญเฉพาะของหลักสูตร(ถ้ามี) ไม่มี |
| BIT | cost per head (budget, **not tuition**) | เฉลี่ย 229,192 บาท/คน/ปี | 13 | BIT-p13-c2 | ประมาณค่าใช้จ่ายต่อหัวในการผลิตบัณฑิตตามหลักสูตรนี้เฉลี่ย229,192 บาท/คน/ ปี |
| BIT | tuition fee / ค่าเทอม | NOT IN DOC | — | — | — |
| BIT | English score requirement (IELTS/TOEFL) | NOT IN DOC | — | — | (0 hits for IELTS / TOEFL in IT_inter2565.pdf) |

## IT — สาขาวิชาเทคโนโลยีสารสนเทศ (IT2565.pdf)

| program | fact | value | page | chunk_id | quote (≤ 15 words) |
|---|---|---|---|---|---|
| IT | program name (TH) | หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาเทคโนโลยีสารสนเทศ | 2 | IT-p2-c2 | ชื่อภาษาไทย หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาเทคโนโลยีสารสนเทศ |
| IT | program name (EN) | Bachelor of Science Program in Information Technology | 2 | IT-p2-c2 | ชื่อภาษาอังกฤษ Bachelor of Science Program in Information Technology |
| IT | degree full (TH) | วิทยาศาสตรบัณฑิต (เทคโนโลยีสารสนเทศ) | 2 | IT-p2-c3 | ชื่อเต็ม (ภาษาไทย) : วิทยาศาสตรบัณฑิต (เทคโนโลยีสารสนเทศ) |
| IT | degree full (EN) | Bachelor of Science (Information Technology) | 2 | IT-p2-c3 | : Bachelor of Science (Information Technology) |
| IT | degree abbr (TH / EN) | วท.บ. (เทคโนโลยีสารสนเทศ) / B.Sc. (Information Technology) | 2 | IT-p2-c3 | : วท.บ. (เทคโนโลยีสารสนเทศ) … : B.Sc. (Information Technology) |
| IT | curriculum year | หลักสูตรปรับปรุง พ.ศ. 2565 | 2 | IT-p2-c1 | หลักสูตรปรับปรุง พ.ศ. 2565 |
| IT | total credits | 129 หน่วยกิต | 2 | IT-p2-c5 (also IT-p15-c1) | 4. จำนวนหน่วยกิตที่เรียนตลอดหลักสูตร 129 หน่วยกิต |
| IT | duration | 4 ปี | 3 | IT-p3-c1 | 5.1 รูปแบบ หลักสูตรปริญญาตรี 4 ปี |
| IT | opening | เดือนสิงหาคม พ.ศ. 2565, หลักสูตรปรับปรุง | 3 | IT-p3-c3 | หลักสูตรปรับปรุง กำหนดเปิดสอนเดือนสิงหาคม พ.ศ. 2565 |
| IT | language of instruction | ภาษาไทยและภาษาอังกฤษ | 3 | IT-p3-c2 | หลักสูตรจัดการศึกษาเป็นภาษาไทยและภาษาอังกฤษ |
| IT | specialisation tracks (3) | (1) ด้านการพัฒนาซอฟต์แวร์ (Software Development) (2) ด้านโครงสร้างพื้นฐานเทคโนโลยีสารสนเทศ (Information Technology Infrastructure) (3) ด้านสื่อประสมสำหรับการพัฒนาสื่อเชิงโต้ตอบ เว็บ และเกม | 2 | IT-p2-c4 (also IT-p15-c1) | (1) ด้านการพัฒนาซอฟต์แวร์ (Software Development) (2) ด้านโครงสร้างพื้นฐานเทคโนโลยีสารสนเทศ |
| IT | when the track is chosen | เมื่อขึ้นปีที่ 2 ภาคการศึกษาที่ 2 | 15 | IT-p15-c2 | นักศึกษาจะต้องเลือกกลุ่มวิชาสาขาที่จะเรียน เมื่อขึ้นปีที่ 2 ภาคการศึกษาที่ 2 |
| IT | admission requirements | ม.ปลายหรือเทียบเท่า; ผ่านการคัดเลือกตามเกณฑ์ของสำนักงานคณะกรรมการอุดมศึกษา และ/หรือระเบียบของสถาบันฯ | 13 | IT-p13-c1 | สำเร็จการศึกษาระดับมัธยมศึกษาตอนปลายหรือเทียบเท่าโดยผ่านการคัดเลือกตามเกณฑ์ของ สำนักงานคณะกรรมการอุดมศึกษา |
| IT | year 1 sem 1 courses | 06016401 คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ; 06016402 พื้นฐานทางด้านเทคโนโลยีสารสนเทศ; 06016411 ระบบคอมพิวเตอร์เบื้องต้น; 06066303 การแก้ปัญหาและการโปรแกรมคอมพิวเตอร์; 90641001 โรงเรียนสร้างเสน่ห์; 90641003 กีฬาและนันทนาการ; 90644007 ภาษาอังกฤษพื้นฐาน 1 | 27 | IT-p27-c1 | ปีที่ 1 ภาคการศึกษาที่ 1 … 06016401 คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ |
| IT | year 1 sem 1 total | 18 หน่วยกิต | 27 | IT-p27-c1 | รวม 18 |
| IT | year 1 sem 2 courses | 06016408 การสร้างโปรแกรมเชิงวัตถุ; 06066001 ความน่าจะเป็นและสถิติ; 06066101 พื้นฐานทางธุรกิจสำหรับเทคโนโลยีสารสนเทศ; 06066301 โครงสร้างข้อมูลและอัลกอริทึม; 90641002 ความฉลาดทางดิจิทัล; 90644008 ภาษาอังกฤษพื้นฐาน 2 | 28 | IT-p28-c1 | ปีที่ 1 ภาคการศึกษาที่ 2 … 06016408 การสร้างโปรแกรมเชิงวัตถุ OBJECT-ORIENTED PROGRAMMING |
| IT | year 1 sem 2 total | 18 หน่วยกิต | 28 | IT-p28-c1 | รวม 18 |
| IT | structure: ศึกษาทั่วไป / เฉพาะ credits | IN DOC (p15: 30 / 93), NOT IN FIXTURE | 15 | — | — |
| IT | careers (first three) | นักโปรแกรมคอมพิวเตอร์ (Programmer); นักพัฒนาเว็บไซต์ (Web Developer); ผู้ทดสอบโปรแกรม (Software Tester); also ผู้ดูแลระบบเครือข่าย (Network System Administrator), นักพัฒนาเกม (Game Developer) | 4 | IT-p4-c1, IT-p4-c2 | นักโปรแกรมคอมพิวเตอร์ (Programmer) - นักพัฒนาเว็บไซต์ (Web Developer) |
| IT | course description 1 | 06016401 คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ (MATHEMATICS FOR INFORMATION TECHNOLOGY) 3(3-0-6) — วิชาบังคับก่อน: ไม่มี | 245 | IT-p245-c1 | 06016401 คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ 3(3-0-6) MATHEMATICS FOR INFORMATION TECHNOLOGY |
| IT | course description 2 | 06016408 การสร้างโปรแกรมเชิงวัตถุ (OBJECT-ORIENTED PROGRAMMING) 3(2-2-5) — วิชาบังคับก่อน: ไม่มี | 248 | IT-p248-c1 | 06016408 การสร้างโปรแกรมเชิงวัตถุ 3(2-2-5) OBJECT-ORIENTED PROGRAMMING วิชาบังคับก่อน : ไม่มี |
| IT | course description 3 | 06016411 ระบบคอมพิวเตอร์เบื้องต้น (INTRODUCTION TO COMPUTER SYSTEMS) 3(2-2-5) — วิชาบังคับก่อน: ไม่มี | 250 | IT-p250-c1 | 06016411 ระบบคอมพิวเตอร์เบื้องต้น 3(2-2-5) INTRODUCTION TO COMPUTER SYSTEMS |
| IT | cost per head (budget, **not tuition**) | เฉลี่ย 76,397 บาท/คน/ปี | 14 | IT-p14-c4 | ประมาณค่าใช้จ่ายต่อหัวในการผลิตบัณฑิตตามหลักสูตรนี้ เฉลี่ย 76,397 บาท/คน/ ปี |
| IT | tuition fee / ค่าเทอม | NOT IN DOC | — | — | — |

## Absent from all four documents (`expect_not_found` candidates)

Checked with a full-text search of every page of each PDF (after PUA repair); hit counts are 0 in
all four unless noted.

| topic | search terms | status |
|---|---|---|
| tuition / semester fee | ค่าธรรมเนียม, ค่าเทอม, ค่าเล่าเรียน, ค่าลงทะเบียน | NOT IN DOC (the only money figures are the per-head production budget above) |
| dormitory / housing | หอพัก | NOT IN DOC |
| master's degree offered by the program | ปริญญาโท | NOT IN DOC |
| entrance score thresholds | IELTS, TOEFL, GPAX, เกรดเฉลี่ย, TCAS, Portfolio | NOT IN DOC (admission text only cites สกอ./สถาบันฯ criteria) |
| "is it hard" / difficulty | เรียนยาก | NOT IN DOC |
| scholarships | ทุนการศึกษา | mentioned in passing (AIT/BIT strategy tables, no amounts) — **not** a clean not-found; do not use |

## Notes for the eval author

- Study-plan tables are flattened column-wise: in AIT/DSBA/BIT the credit cell `3 (3-0-6)` follows
  its course; in IT2565 it precedes it. Eval cases should test course codes/names and the semester
  total, not per-course credits.
- Opening month and curriculum type differ: AIT is `หลักสูตรใหม่` opening
  กรกฎาคม 2566; the other three are `หลักสูตรปรับปรุง` opening สิงหาคม 2565.
- Credits: AIT 120, BIT 126, IT 129, DSBA 132 (all 4-year). These are the raw numbers to use in
  comparison cases; never expect a computed difference.
