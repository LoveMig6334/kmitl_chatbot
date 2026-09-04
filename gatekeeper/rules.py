"""Deterministic pre-filter (layer 1, zero API calls).

Every function here is pure and unit-tested.  The rule layer only returns a
category when it is confident; otherwise it returns ``None`` and the LLM layer
decides.  Regardless of whether a category fires, metadata extraction
(faculty, program, course codes, question kind) is always available.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import (
    FACULTY_ALIASES,
    GENERIC_FIELD_ALIASES,
    INTER_ALIASES,
    OTHER_KMITL_FACULTIES,
    OTHER_KMITL_FACULTY_PATTERNS,
    PROGRAM_CONTEXT_WORDS,
    PROGRAMS,
    KmitlFaculty,
)
from .schema import Category, QuestionKind
from .smalltalk import detect_smalltalk, smalltalk_kind

__all__ = ["smalltalk_kind"]

# --------------------------------------------------------------------------- #
# Injection / abuse
# --------------------------------------------------------------------------- #
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        # English
        r"\bignore\b.{0,40}\b(previous|prior|above|earlier|all|your|the)\b.{0,20}\b(instructions?|prompts?|rules?|guidelines?)\b",
        r"\b(disregard|forget|override|bypass)\b.{0,40}\b(instructions?|prompts?|rules?|guidelines?|programming|training)\b",
        r"\bsystem\s*prompt\b",
        r"\b(reveal|show|print|display|output|repeat|leak|dump|tell me|what is|what's|give me)\b.{0,40}\b(your|the)\b.{0,20}\b(instructions?|prompt|configuration|config|rules|guidelines|directives|hidden)\b",
        r"\b(how|what)\b.{0,20}\b(were|are|have)\b.{0,10}\byou\b.{0,20}\b(configured|programmed|instructed|set ?up)\b",
        r"\byou are now\b",
        r"\b(act|pretend|roleplay|role-play)\b.{0,10}\b(as|to be|you are)\b.{0,30}\b(unrestricted|uncensored|evil|without (any )?(rules|restrictions|limits)|dan\b|jailbroken)",
        r"\bjailbreak",
        r"\bdeveloper mode\b",
        r"\bdo anything now\b",
        r"\b(new|updated) instructions?\s*:",
        r"\b(sudo|admin) mode\b",
        r"\bstop being an? (ai|assistant|chatbot)\b",
        r"\b(kill|hurt|harm|bomb|weapon)\b.{0,20}\b(how to|make|build|create|synthesi[sz]e)\b",
        r"\bhow to (make|build|create|synthesi[sz]e)\b.{0,20}\b(bomb|explosive|weapon|meth|drugs?)\b",
        # Thai
        r"(ลืม|ไม่ต้องสนใจ|เพิกเฉย|ยกเลิก|ละเว้น|ข้าม|ทิ้ง|โยน)\s*(คำสั่ง|กฎ|ข้อกำหนด|ข้อความ|บทบาท|คำแนะนำ)\s*(เดิม|ก่อนหน้า|ทั้งหมด|ที่ผ่านมา|ข้างต้น|ทุกอย่าง|ระบบ)?",
        r"(ลืม|ไม่ต้องสนใจ|เพิกเฉย)\s*(ทุกอย่าง|ทั้งหมด|สิ่ง)\s*(ที่|ก่อนหน้า|เดิม)",
        r"(ระบบพรอมต์|พรอมต์ระบบ|พร้อมท์ระบบ|ระบบพร้อมท์|system\s*prompt|คำสั่งระบบ|คำสั่งลับ|คำสั่งที่ซ่อน|คำสั่งเริ่มต้น|คำสั่งตั้งต้น|prompt\s*ของคุณ|พรอมต์ของคุณ)",
        r"(บอก|เผย|เปิดเผย|แสดง|พิมพ์|บอกฉัน|บอกเรา|บอกหน่อย)\s*(ฉัน|เรา|มา|หน่อย|ที)?\s*(ว่า)?\s*(คุณ|เธอ|บอท|ระบบ)\s*(ถูก)?\s*(ตั้งค่า|โปรแกรม|กำหนด|สั่ง|ตั้ง)",
        r"(คุณ|เธอ|บอท)\s*(ถูก)?\s*(ตั้งค่า|โปรแกรม|กำหนดค่า|เซ็ตอัพ|เซตอัป)\s*(ไว้|มา)?\s*(อย่างไร|ยังไง|แบบไหน|ว่าอะไร)",
        r"(สมมติว่า|สมมุติว่า|ทำตัวเป็น|แสดงเป็น|สวมบทบาท|รับบท|จำลองว่า)\s*(คุณ|เธอ)?\s*(เป็น|คือ)?\s*.{0,30}(ไม่มีข้อจำกัด|ไร้ข้อจำกัด|ไม่มีกฎ|ไร้กฎ|ทำได้ทุกอย่าง|ไม่ต้องสนใจกฎ|ตอบได้ทุกอย่าง|โหมดนักพัฒนา|ปลดล็อก)",
        r"(โหมดนักพัฒนา|โหมด\s*developer|โหมดผู้ดูแล|โหมดแอดมิน|ปลดล็อก(ข้อจำกัด|ตัวเอง|ระบบ)|เจลเบรก|แหกกฎ)",
        r"(ตอนนี้|จากนี้ไป|ต่อจากนี้|นับจากนี้)\s*(คุณ|เธอ)\s*(คือ|เป็น|จะเป็น)\s*(ผู้ช่วย|บอท|ai|เอไอ)?\s*.{0,20}(ใหม่|ไม่มีข้อจำกัด|ทำได้ทุกอย่าง)",
        r"(วิธี(ทำ|สร้าง|ประกอบ)|สอน(ทำ|สร้าง))\s*(ระเบิด|อาวุธ|ยาเสพติด|ยาบ้า|ปืนเถื่อน)",
        r"(ไอ้|อี)\s*(โง่|ควาย|สัตว์|เหี้ย|สัส|เวร)",
        r"(ตอบมา(เดี๋ยวนี้|ซะ|สิ)|ไม่งั้น(ฉันจะ|จะ))\s*.{0,20}(ฆ่า|ทำลาย|แฉ|ลบ)",
        # Chinese
        r"忽略.{0,10}(之前|以上|上面|所有|先前|前面).{0,10}(指令|指示|提示|规则|说明)",
        r"(忘掉|忘记|无视|不要理会|放弃).{0,10}(之前|以上|所有|先前).{0,10}(指令|指示|提示|规则|设定)",
        r"(系统提示|系统提示词|系统指令|系统设定|初始指令|隐藏指令|你的提示词|你的指令)",
        r"(告诉我|显示|输出|透露|泄露|展示|说出).{0,10}(你|您).{0,6}(是怎么|如何|怎样).{0,6}(被)?(设置|配置|设定|编程|训练)",
        r"(你|您)(现在)?(是|扮演|假装|假扮).{0,20}(没有限制|无限制|不受限|开发者模式|越狱|任何事)",
        r"(越狱|开发者模式|解除限制|绕过限制)",
    )
)

# --------------------------------------------------------------------------- #
# Universities
# --------------------------------------------------------------------------- #
_KMITL_PATTERN = re.compile(
    r"(สจล\.?|ลาดกระบัง|เจ้าคุณทหาร|พระจอมเกล้าเจ้าคุณทหาร|\bkmitl\b|king\s*mongkut'?s?\s*institute\s*of\s*technology\s*ladkrabang"
    r"|拉卡邦|先皇技术学院|蒙库国王理工学院)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class University:
    key: str
    name_th: str
    name_en: str
    admissions_url: str | None  # None = unknown / not a TCAS university (foreign)
    pattern: re.Pattern[str]


def _u(key: str, th: str, en: str, url: str | None, pattern: str) -> University:
    return University(key, th, en, url, re.compile(pattern, re.IGNORECASE))


OTHER_UNIVERSITIES: tuple[University, ...] = (
    _u("CU", "จุฬาลงกรณ์มหาวิทยาลัย", "Chulalongkorn University", "https://www.admissions.chula.ac.th",
       r"จุฬา|chula|chulalongkorn|朱拉隆功|\bcu\b(?=.*(university|มหาวิทยาลัย))"),
    _u("MU", "มหาวิทยาลัยมหิดล", "Mahidol University", "https://tcas.mahidol.ac.th",
       r"มหิดล|\bmahidol\b|玛希隆|玛希敦"),
    _u("TU", "มหาวิทยาลัยธรรมศาสตร์", "Thammasat University", "https://www.tuadmissions.in.th",
       r"ธรรมศาสตร์|\bthammasat\b|\bมธ\.?(?![ก-๙])|法政大学"),
    _u("KU", "มหาวิทยาลัยเกษตรศาสตร์", "Kasetsart University", "https://admission.ku.ac.th",
       r"เกษตรศาสตร์|\bkasetsart\b|(?<![ก-๙])มก\.?(?![ก-๙])|ม\.?\s?เกษตร|(?<![ก-๙])เกษตร(?![ก-๙])|农业大学"),
    _u("CMU", "มหาวิทยาลัยเชียงใหม่", "Chiang Mai University", "https://www1.reg.cmu.ac.th/ugradapply",
       r"มหาวิทยาลัยเชียงใหม่|ม\.?\s?เชียงใหม่|(?<![ก-๙])มช\.?(?![ก-๙])|chiang\s*mai\s*university|\bcmu\b|清迈大学"),
    _u("KKU", "มหาวิทยาลัยขอนแก่น", "Khon Kaen University", "https://admissions.kku.ac.th",
       r"มหาวิทยาลัยขอนแก่น|ม\.?\s?ขอนแก่น|(?<![ก-๙])มข\.?(?![ก-๙])|khon\s*kaen|\bkku\b|孔敬大学"),
    _u("PSU", "มหาวิทยาลัยสงขลานครินทร์", "Prince of Songkla University", "https://entrance.psu.ac.th",
       r"สงขลานครินทร์|ม\.?\s?อ\.?(?=\s*(หาดใหญ่|ปัตตานี|ภูเก็ต))|prince\s*of\s*songkla|\bpsu\b|宋卡王子大学"),
    _u("SU", "มหาวิทยาลัยศิลปากร", "Silpakorn University", "https://admission.su.ac.th",
       r"ศิลปากร|\bsilpakorn\b|艺术大学"),
    _u("SWU", "มหาวิทยาลัยศรีนครินทรวิโรฒ", "Srinakharinwirot University", "https://admission.swu.ac.th",
       r"ศรีนครินทรวิโรฒ|(?<![ก-๙])มศว\.?|srinakharinwirot|\bswu\b"),
    _u("KMUTT", "มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าธนบุรี", "KMUTT", "https://admission.kmutt.ac.th",
       r"พระจอมเกล้าธนบุรี|(?<![ก-๙])มจธ\.?|\bkmutt\b|บางมด"),
    _u("KMUTNB", "มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ", "KMUTNB", "https://admission.kmutnb.ac.th",
       r"พระจอมเกล้าพระนครเหนือ|(?<![ก-๙])มจพ\.?|\bkmutnb\b"),
    _u("SUT", "มหาวิทยาลัยเทคโนโลยีสุรนารี", "Suranaree University of Technology", "http://sutgateway.sut.ac.th",
       r"สุรนารี|suranaree|(?<![ก-๙])มทส\.?"),
    _u("NU", "มหาวิทยาลัยนเรศวร", "Naresuan University", "https://www.admission.nu.ac.th",
       r"นเรศวร|naresuan"),
    _u("BUU", "มหาวิทยาลัยบูรพา", "Burapha University", "https://regservice.buu.ac.th",
       r"มหาวิทยาลัยบูรพา|ม\.?\s?บูรพา|burapha"),
    _u("MFU", "มหาวิทยาลัยแม่ฟ้าหลวง", "Mae Fah Luang University", "https://admission.mfu.ac.th",
       r"แม่ฟ้าหลวง|mae\s*fah\s*luang|\bmfu\b"),
    _u("RSU", "มหาวิทยาลัยรังสิต", "Rangsit University", "https://www.rsu.ac.th/admission",
       r"มหาวิทยาลัยรังสิต|ม\.?\s?รังสิต|rangsit\s*university|\brsu\b"),
    _u("BU", "มหาวิทยาลัยกรุงเทพ", "Bangkok University", "https://www.bu.ac.th/th/admission",
       r"มหาวิทยาลัยกรุงเทพ|ม\.?\s?กรุงเทพ|bangkok\s*university"),
    _u("UTCC", "มหาวิทยาลัยหอการค้าไทย", "UTCC", "https://www.utcc.ac.th/admission",
       r"หอการค้า|\butcc\b"),
    _u("AU", "มหาวิทยาลัยอัสสัมชัญ", "Assumption University", "https://admissions.au.edu",
       r"อัสสัมชัญ|\babac\b|assumption\s*university"),
    _u("NIDA", "สถาบันบัณฑิตพัฒนบริหารศาสตร์", "NIDA", "https://nida.ac.th",
       r"\bnida\b|นิด้า|บัณฑิตพัฒนบริหารศาสตร์"),
    _u("RMUT", "มหาวิทยาลัยเทคโนโลยีราชมงคล", "RMUT", "https://www.rmutt.ac.th",
       r"ราชมงคล|rajamangala|\brmut[a-z]*\b"),
    _u("RU", "มหาวิทยาลัยราชภัฏ", "Rajabhat University", "https://www.mytcas.com",
       r"ราชภัฏ|rajabhat"),
    _u("RAM", "มหาวิทยาลัยรามคำแหง", "Ramkhamhaeng University", "https://www.ru.ac.th",
       r"รามคำแหง|ramkhamhaeng"),
    _u("STOU", "มหาวิทยาลัยสุโขทัยธรรมาธิราช", "STOU", "https://www.stou.ac.th",
       r"สุโขทัยธรรมาธิราช|\bstou\b|(?<![ก-๙])มสธ\.?"),
    _u("SIIT", "SIIT", "Sirindhorn International Institute of Technology", "https://www.siit.tu.ac.th",
       r"\bsiit\b|สิรินธร"),
    _u("ABROAD", "", "", None,  # empty names -> generic "that university" wording, no TCAS
       r"\b(mit|stanford|harvard|oxford|cambridge|yale|princeton|berkeley|ucla|caltech|nus|ntu|tsinghua|peking)\b(?=.*\b(university|program|admission|faculty|course|degree|school|major|apply|tuition)\b)"
       r"|(清华|北京大学|北大|复旦|浙江大学|上海交通|新加坡国立|南洋理工|哈佛|斯坦福|麻省理工|牛津|剑桥)"),
)

# --------------------------------------------------------------------------- #
# KMITL-but-not-curriculum topics
# --------------------------------------------------------------------------- #
_OUT_OF_SCOPE_KMITL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (topic, re.compile(p, re.IGNORECASE))
    for topic, p in (
        ("dorm", r"หอพัก|หอใน|หอนอก|ที่พัก(นักศึกษา)?|\bdorm(itory|itories|s)?\b|\bhousing\b|宿舍|住宿"),
        ("transport", (
            r"รถเมล์|รถตู้|รถไฟฟ้า|shuttle|การเดินทางไป|เดินทางมา|เดินทางไป|ที่จอดรถ|\bparking\b|交通|停车"
            r"|\bhow (do|can|should) (i|we) get to\b|\bdirections? to\b|\b(bus|train|taxi|grab) (to|from)\b|\bairport\b|怎么去|怎么走"
        )),
        ("food", r"โรงอาหาร|ร้านอาหารใน|\bcanteen\b|\bcafeteria\b|食堂"),
        ("events", r"งานรับน้อง|รับน้อง|กิจกรรมชมรม|ชมรม|คอนเสิร์ต|\bconcert\b|open\s*house|\bevents?\b|活动|社团"),
        ("facilities", r"ห้องสมุด(เปิด|ปิด)|\blibrary (hours|opening)\b|wifi|wi-fi|สนามกีฬา|ฟิตเนส|\bgym\b|โรงยิม|图书馆(开放|几点)"),
        ("staff", r"เบอร์โทร|เบอร์ติดต่อ|โทรศัพท์|phone number|contact number|电话"),
        ("scholarship", r"ทุนการศึกษา|ทุนเรียน|\bscholarships?\b|奖学金"),
        ("registrar", (
            r"เกรดออก|ผลการเรียนออก|ประกาศผล|ผลสอบออก|ตารางสอบ|เพิ่มถอน|ถอนวิชา|ดรอปวิชา|ทรานสคริปต์|\btranscripts?\b|ใบรับรอง|ใบเกรด|เช็คเกรด|ดูเกรด"
            r"|\bgrades? (come|are|be) (out|released|posted)\b|\bwhen (do|will|are) (the )?grades\b|\bexam (schedule|timetable|dates?)\b|\badd[/ -]drop\b|成绩(什么时候|公布)|考试时间表|成绩单"
        )),
    )
)

_CURRICULUM_KEYWORDS = re.compile(
    r"หลักสูตร|หน่วยกิต|รายวิชา|วิชา(บังคับ|เลือก|เอก|โท|พื้นฐาน|เฉพาะ|ศึกษาทั่วไป)|แผนการเรียน|โครงสร้างหลักสูตร|สาขา(วิชา)?|ปริญญา|บัณฑิต"
    r"|เกณฑ์การรับ|คุณสมบัติผู้(สมัคร|เข้าศึกษา)|การรับเข้า|รับสมัคร|รอบ(รับ|ที่)|โควตา|portfolio|admission|tcas"
    r"|เปิดสอน|ปีการศึกษา|ภาคการศึกษา|ชั้นปี|จบภายใน|สำเร็จการศึกษา|เรียนกี่ปี|กี่ปี|ค่าธรรมเนียมการศึกษา|ค่าเทอม|ค่าเล่าเรียน"
    r"|เจนเอ็ด|\bgen[ -]?ed\b|วิชาศึกษาทั่วไป|general education|วัตถุประสงค์(ของ)?หลักสูตร|ปรัชญา(ของ)?หลักสูตร|ผลลัพธ์การเรียนรู้|อาชีพ(ที่|หลัง)|สหกิจ|ฝึกงาน|โปรเจค|โครงงาน|ปริญญานิพนธ์"
    r"|\bcurriculum\b|\bcredits?\b|\bcourses?\b|\bsubjects?\b|\bprogram(me)?s?\b|\bmajors?\b|\bdegree\b|\bbachelor\b|\bmaster\b|\bsyllabus\b|\bprerequisites?\b"
    r"|\bsemesters?\b|\bacademic year\b|\bgraduat(e|ion)\b|\btuition\b|\bstudy plan\b|\bintake\b|\benrol+(ment)?\b|\brequirements?\b|\belective\b|\bcore courses?\b|\binternship\b|\bcapstone\b|\bthesis\b"
    r"|专业|学分|课程|学制|招生|入学|学位|学费|培养|开课|必修|选修|毕业|实习|论文|学院",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------- #
# Obvious everyday off-topic
# --------------------------------------------------------------------------- #
_GENERAL_TOPICS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (topic, re.compile(p, re.IGNORECASE))
    for topic, p in (
        ("weather", r"อากาศ|ฝนตก|ฝนจะตก|พยากรณ์|อุณหภูมิ|ร้อนไหม|หนาวไหม|พายุ|\bweather\b|\bforecast\b|\braining\b|\btemperature\b|天气|下雨|气温"),
        ("cooking", r"สูตร(ทำ|อาหาร)?\s*(ต้มยำ|ผัด|แกง|ขนม|อาหาร|กุ้ง|ไก่|หมู|ปลา|เค้ก|คุกกี้|ข้าว)|วิธีทำ(อาหาร|ต้มยำ|ผัด|แกง|ขนม|เค้ก)|\brecipes?\b|how to (cook|bake|make) (a |an |some )?(soup|curry|cake|tom yum|pad thai|noodles|rice|pasta|pizza|bread|cookies)|食谱|怎么做.{0,6}(菜|汤|饭|蛋糕)"),
        ("lottery", r"หวย|เลขเด็ด|สลากกินแบ่ง|\blottery\b|彩票"),
        ("finance", r"ราคาทอง|ราคาน้ำมัน|หุ้น|บิทคอยน์|bitcoin|\bstock price\b|\bgold price\b|\bexchange rate\b|อัตราแลกเปลี่ยน|金价|股票|汇率"),
        ("sports", r"ผลบอล|ฟุตบอล(คืนนี้|เมื่อคืน|วันนี้)|พรีเมียร์ลีก|\bfootball (score|result|match)\b|\bpremier league\b|\bnba\b|球赛|足球比赛"),
        ("entertainment", r"หนัง(ใหม่|ดีๆ|น่าดู)|ซีรีส์|ซีรี่ย์|ละคร|เพลง(ใหม่|ฮิต)|netflix|\bmovie\b|\bmovies\b|\bseries\b|\bsong\b|电影|电视剧|歌曲"),
        ("chitchat", r"เล่าเรื่องตลก|\btell me a joke\b|讲个笑话"),
        ("coding", r"(เขียน|แก้)\s*(โค้ด|code|โปรแกรม)\s*(python|java|javascript|c\+\+|sql|html)|\bwrite (me )?(a |some )?(python|java|javascript|c\+\+|sql|bash) (code|script|function|program)\b|\bfix (my|this) (code|bug|error)\b|\bsegfault\b|\bstack ?overflow\b|写.{0,4}(python|java|代码|程序)"),
        ("health", r"ปวดหัว|ปวดท้อง|เป็นไข้|กินยาอะไร|ลดน้ำหนัก|ลดความอ้วน|ออกกำลังกาย|\bheadache\b|\bmedicine for\b|\blose weight\b|\bdiet\b|\bworkout\b|头疼|感冒|减肥"),
        ("travel", r"ที่เที่ยว|เที่ยว(ไหน|ที่ไหน)|จองโรงแรม|ตั๋วเครื่องบิน|\bflight to\b|\bhotel in\b|\btravel to\b|旅游|机票"),
        ("politics", r"นายก(รัฐมนตรี)?(คนปัจจุบัน|คือใคร)|เลือกตั้ง|\bprime minister\b|\belection\b|总理|选举"),
    )
)

# --------------------------------------------------------------------------- #
# Course codes / metadata
# --------------------------------------------------------------------------- #
# KMITL course codes are 8 digits (e.g. 06016317, 01006710).  Also accept the
# common "XX 0000 0000"-style and letter-prefixed codes used in other faculties.
COURSE_CODE_PATTERN = re.compile(
    r"(?<![\d-])(\d{8})(?![\d-])"
    r"|(?<![A-Za-z\d])([A-Z]{2,4}\s?-?(?!(?:25|20)\d\d(?!\d))\d{3,4})(?![\d])"
)

# Very short follow-up fragments that only make sense inside a curriculum conversation
# ("แล้วรอบ 2 ล่ะ", "กี่บาทนะ", "and BIT?").  The gate has no history, so they are in_scope
# by the "attempt an answer rather than wrongly refuse" principle.
_FOLLOWUP_FRAGMENT = re.compile(
    r"^(?:แล้ว|then|and|what about|how about|\bso\b)?\s*"
    r"(?:(?:ปี|เทอม|รอบ|ชั้นปี|ภาค)\s*\d|ait|dsba|bit|it|ไอที|อินเตอร์|inter|ทั้งหมด|รวม|"
    r"กี่(?:บาท|ปี|คน|หน่วยกิต|เทอม|รอบ|วิชา|ตัว|ชั่วโมง)|เท่าไหร่|เท่าไร|ปีไหน|รอบไหน|เมื่อไหร่|เมื่อไร|ตอนไหน|วันไหน)"
    r"[\sก-๙a-z0-9]{0,12}?\s*(?:ล่ะ|หละ|ละ|นะ|อ่ะ|หรอ|เหรอ|ครับ|คะ|ค่ะ|\?)*\s*$",
    re.IGNORECASE,
)

_COMPARISON_PATTERN = re.compile(
    r"เปรียบเทียบ|เทียบ(กับ|กัน)|ต่างกัน|แตกต่าง|ความแตกต่าง|ดีกว่า|เหมือนกัน(ไหม|หรือ)|อันไหน(ดี|เหมาะ)|ควรเลือก|เลือก(อะไร|อันไหน|คณะไหน|สาขาไหน)ดี"
    r"|\bvs\.?\b|\bversus\b|\bcompar(e|ed|ison|ing)\b|\bdifferen(ce|t)\b|\bbetter\b|\bwhich (one|is)\b|\bsimilar(ities)?\b|\bor\b(?=.*\?)"
    r"|区别|比较|不同|哪个更|对比|差异",
    re.IGNORECASE,
)
_FACT_PATTERN = re.compile(
    r"กี่(?!ยว)|เท่าไหร่|เท่าไร|เมื่อใด|เมื่อไหร่|เมื่อไร|ตอนไหน|ปีไหน|วันไหน|ใช่ไหม|หรือไม่|หรือเปล่า|ไหม\s*$|มีไหม|ที่ไหน|ใคร|จำนวน|เปิดสอนเมื่อ|รหัสวิชา"
    r"|\bhow (many|much|long)\b|\bwhen\b|\bwhat year\b|\bwhich year\b|\bis there\b|\bdoes\b|\bdo (i|we|they|students)\b|\bwho\b|\bwhere\b|\bnumber of\b|\bhow old\b|\bdeadline\b"
    r"|多少|几年|几个|什么时候|何时|哪一年|哪年|是否|有没有|吗|谁|哪里|几门",
    re.IGNORECASE,
)
_DESCRIPTIVE_PATTERN = re.compile(
    r"อธิบาย|เป็นอย่างไร|ยังไงบ้าง|อย่างไรบ้าง|คืออะไร|มีอะไรบ้าง|เรียนอะไรบ้าง|รายละเอียด|เกี่ยวกับอะไร|สอนอะไร|แนะนำ|ภาพรวม|โครงสร้าง|จบไปทำงานอะไร|อาชีพ"
    r"|\bexplain\b|\bdescribe\b|\bwhat (is|are)\b|\boverview\b|\btell me about\b|\bdetails?\b|\bwhat does\b.{0,30}\b(cover|teach|include)\b|\bwhat can i\b|\bcareer\b|\bstructure\b|\bobjectives?\b|\bphilosophy\b"
    r"|介绍|是什么|有哪些|说明|详细|解释|概况|学什么|就业|结构|目标",
    re.IGNORECASE,
)


_OTHER_KMITL_FACULTY_RE = re.compile("|".join(f"(?:{p})" for p in OTHER_KMITL_FACULTY_PATTERNS), re.IGNORECASE)
_OTHER_KMITL_FACULTY_RES: tuple[tuple[KmitlFaculty, re.Pattern[str]], ...] = tuple(
    (f, re.compile(f.pattern, re.IGNORECASE)) for f in OTHER_KMITL_FACULTIES
)
_CONTEXT_WINDOW = 25  # chars around a weak alias in which a context word must appear


@dataclass
class Metadata:
    programs: list[str] = field(default_factory=list)  # canonical ids, in order of first mention
    faculty_mentioned: bool = False
    course_codes: list[str] = field(default_factory=list)
    question_kind: QuestionKind | None = None

    @property
    def program(self) -> str | None:
        return self.programs[0] if len(self.programs) == 1 else None


@dataclass
class RuleResult:
    category: Category | None
    confidence: float
    reason: str
    metadata: Metadata
    university: University | None = None  # for off_topic_other_university
    faculty: KmitlFaculty | None = None  # for out_of_scope_kmitl (topic == "faculty")
    topic: str | None = None  # hint for the redirect template


# --------------------------------------------------------------------------- #
# Public pure functions
# --------------------------------------------------------------------------- #
def is_injection(text: str) -> bool:
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def mentions_kmitl(text: str) -> bool:
    return bool(_KMITL_PATTERN.search(text))


def mentions_faculty(text: str) -> bool:
    """True when the IT faculty itself is named (any language)."""
    lowered = text.lower()
    return any(_alias_search(lowered, a) is not None for a in FACULTY_ALIASES)


def mentions_other_kmitl_faculty(text: str) -> bool:
    return bool(_OTHER_KMITL_FACULTY_RE.search(text))


def find_other_kmitl_faculty(text: str) -> KmitlFaculty | None:
    """The first other-KMITL faculty named in ``text`` (drives the redirect wording)."""
    for fac, rx in _OTHER_KMITL_FACULTY_RES:
        if rx.search(text):
            return fac
    return None


def find_other_universities(text: str) -> list[University]:
    return [u for u in OTHER_UNIVERSITIES if u.pattern.search(text)]


_GENERIC_FIELD_RE = re.compile(
    "|".join(
        rf"(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])" if a.isascii() else re.escape(a)
        for a in sorted(GENERIC_FIELD_ALIASES, key=len, reverse=True)
    ),
    re.IGNORECASE,
)


def has_specific_scope_signal(text: str) -> bool:
    """True when our faculty/programs are named *specifically* (ids, Thai names,
    "คณะไอที", ...) — not merely via a generic field name such as "data science"."""
    stripped = _GENERIC_FIELD_RE.sub(" ", text)
    return bool(resolve_programs(stripped)) or mentions_faculty(stripped) or bool(extract_course_codes(text))


def is_followup_fragment(text: str) -> bool:
    return len(text) <= 25 and bool(_FOLLOWUP_FRAGMENT.match(text.strip()))


def has_curriculum_keywords(text: str) -> bool:
    return bool(_CURRICULUM_KEYWORDS.search(text))


def find_out_of_scope_topic(text: str) -> str | None:
    for topic, pat in _OUT_OF_SCOPE_KMITL_PATTERNS:
        if pat.search(text):
            return topic
    return None


def find_general_topic(text: str) -> str | None:
    for topic, pat in _GENERAL_TOPICS:
        if pat.search(text):
            return topic
    return None


def extract_course_codes(text: str) -> list[str]:
    codes: list[str] = []
    for m in COURSE_CODE_PATTERN.finditer(text):
        code = (m.group(1) or m.group(2) or "").replace(" ", "").replace("-", "").upper()
        if code and code not in codes:
            codes.append(code)
    return codes


def _alias_search(lowered: str, alias: str, *, case_sensitive_src: str | None = None) -> re.Match[str] | None:
    """Find ``alias`` in ``lowered``; ASCII aliases must match as whole words."""
    if alias.isascii():
        flags = 0 if case_sensitive_src is not None else re.IGNORECASE
        src = case_sensitive_src if case_sensitive_src is not None else lowered
        return re.search(rf"(?<![A-Za-z]){re.escape(alias)}(?![A-Za-z])", src, flags)
    pos = lowered.find(alias)
    if pos < 0:
        return None
    return re.compile(re.escape(alias)).search(lowered, pos)


def _has_context(lowered: str, start: int, end: int) -> bool:
    window = lowered[max(0, start - _CONTEXT_WINDOW): end + _CONTEXT_WINDOW]
    return any(w in window for w in PROGRAM_CONTEXT_WORDS)


def resolve_programs(text: str, scope_filter: list[str] | None = None) -> list[str]:
    """Return the in-scope program ids the text refers to, in order of mention.

    Disambiguation (see config): bare "IT"/"ไอที"/"AI" only count with a
    program-context word nearby; anything "inter"/นานาชาติ is BIT, never IT.
    """
    lowered = text.lower()
    hits: dict[str, tuple[int, int, bool]] = {}  # id -> (start, end, strong)
    for prog in PROGRAMS:
        best: tuple[int, int, bool] | None = None
        for alias in prog.aliases:
            m = _alias_search(lowered, alias)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), m.end(), True)
        for alias in prog.exact_aliases:
            m = _alias_search(lowered, alias, case_sensitive_src=text)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), m.end(), True)
        if best is None:
            for alias in prog.weak_aliases:
                for m in re.finditer(
                    rf"(?<![A-Za-z]){re.escape(alias)}(?![A-Za-z])" if alias.isascii() else re.escape(alias), lowered
                ):
                    if _has_context(lowered, m.start(), m.end()):
                        best = (m.start(), m.end(), False)
                        break
                if best:
                    break
        if best:
            hits[prog.id] = best

    # "IT inter"/นานาชาติ always means BIT (never the IT program); an IT alias that
    # overlaps the BIT alias span ("สาขาวิชาเทคโนโลยีสารสนเทศทางธุรกิจ") is BIT too.
    if "IT" in hits and ("BIT" in hits or any(_alias_search(lowered, a) for a in INTER_ALIASES)):
        it_s, it_e, it_strong = hits["IT"]
        overlaps = False
        if "BIT" in hits:
            b_s, b_e, _ = hits["BIT"]
            overlaps = it_s < b_e and b_s < it_e
        inter = any(_alias_search(lowered, a) for a in INTER_ALIASES)
        if not it_strong or overlaps or inter:
            del hits["IT"]
            if "BIT" not in hits and inter:
                hits["BIT"] = (it_s, it_e, True)

    ids = [pid for pid, _ in sorted(hits.items(), key=lambda kv: kv[1][0])]
    if scope_filter:
        allowed = [s.upper() for s in scope_filter if s]
        narrowed = [pid for pid in ids if pid in allowed]
        if narrowed:
            ids = narrowed
        elif not ids and len(allowed) == 1 and allowed[0] in {p.id for p in PROGRAMS}:
            ids = [allowed[0]]
    return ids


def classify_question_kind(text: str, programs: list[str] | None = None) -> QuestionKind:
    if (programs and len(programs) > 1) or _COMPARISON_PATTERN.search(text):
        return "comparison"
    if _DESCRIPTIVE_PATTERN.search(text) and not _FACT_PATTERN.search(text):
        return "descriptive"
    if _FACT_PATTERN.search(text):
        return "fact_lookup"
    return "descriptive"


def extract_metadata(text: str, scope_filter: list[str] | None = None) -> Metadata:
    programs = resolve_programs(text, scope_filter)
    return Metadata(
        programs=programs,
        faculty_mentioned=mentions_faculty(text),
        course_codes=extract_course_codes(text),
        question_kind=classify_question_kind(text, programs),
    )


def apply_rules(text: str, scope_filter: list[str] | None = None) -> RuleResult:
    """Run the deterministic layer.  ``category`` is ``None`` when unsure.

    Principle: rules decide only when near-certain; otherwise abstain to the LLM.
    """
    meta = extract_metadata(text, scope_filter)
    stripped = text.strip()

    # 1. Injection always wins, even when wrapped in a greeting or a legitimate-looking question.
    if is_injection(stripped):
        return RuleResult("injection_or_abuse", 0.98, "injection pattern", meta)

    # 2. Pure smalltalk (greeting / thanks / ok / bye / who are you / vague help opener):
    #    the whole message must be content-free, otherwise abstain (mixed → in_scope via the LLM).
    kind = detect_smalltalk(stripped)
    if kind is not None:
        return RuleResult("greeting_smalltalk", 0.95, f"smalltalk: {kind}", Metadata(), topic=kind)

    kmitl = mentions_kmitl(stripped)
    others = find_other_universities(stripped)
    other_kmitl_faculty = mentions_other_kmitl_faculty(stripped)
    in_scope_signal = meta.faculty_mentioned or bool(meta.programs) or bool(meta.course_codes)
    curriculum = has_curriculum_keywords(stripped)
    gen_topic = find_general_topic(stripped)
    oos_topic = find_out_of_scope_topic(stripped)

    # 3. Another university named, and nothing points at our faculty/programs -> redirect.
    #    (Comparisons with our programs, or KMITL mentions, abstain to the LLM.)
    if others and not kmitl and not in_scope_signal:
        return RuleResult(
            "off_topic_other_university", 0.95, f"other university: {others[0].key}", meta, university=others[0]
        )
    #    Generic field names ("data science", "AI", "IT") next to another university are that
    #    university's programs, not ours.
    if others and not kmitl and not has_specific_scope_signal(stripped):
        return RuleResult(
            "off_topic_other_university", 0.9, f"other university + generic field: {others[0].key}", meta,
            university=others[0],
        )

    # 4. Another KMITL faculty named, ours not -> out of scope (KMITL).
    if other_kmitl_faculty and not others and not in_scope_signal:
        return RuleResult(
            "out_of_scope_kmitl", 0.9, "other KMITL faculty", meta, topic="faculty",
            faculty=find_other_kmitl_faculty(stripped),
        )

    # 5. KMITL logistics that the curriculum documents do not cover.
    if oos_topic and not others and not curriculum and (kmitl or in_scope_signal or not gen_topic):
        return RuleResult("out_of_scope_kmitl", 0.9, f"kmitl logistics: {oos_topic}", meta, topic=oos_topic)

    # 6. Obvious everyday topics with no curriculum signal at all.
    if gen_topic and not kmitl and not in_scope_signal and not curriculum:
        return RuleResult("off_topic_general", 0.9, f"general topic: {gen_topic}", meta, topic=gen_topic)

    # 7. Clear curriculum question about our faculty / a program / a course code.
    if in_scope_signal and not others and not other_kmitl_faculty and (curriculum or meta.course_codes):
        return RuleResult("in_scope", 0.92, "program/faculty + curriculum keywords", meta)

    # 8. Bare follow-up fragment with no other signal ("กี่บาทนะ", "แล้วรอบ 2 ล่ะ").
    if is_followup_fragment(stripped) and not (others or other_kmitl_faculty or gen_topic or oos_topic):
        return RuleResult("in_scope", 0.7, "follow-up fragment", meta)

    return RuleResult(None, 0.0, "no rule fired", meta, university=others[0] if others else None,
                      topic=gen_topic or oos_topic)
