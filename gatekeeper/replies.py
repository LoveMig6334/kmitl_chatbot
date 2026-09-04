"""Fixed-style refusal / redirect templates, selected by category × language,
plus the warm ``greeting_smalltalk`` welcome.

Pure functions only.  ``other`` languages fall back to English.  Injection
replies are deliberately short and never mention internals.
"""

from __future__ import annotations

import re

from .config import (
    FACULTY_NAME_EN,
    FACULTY_NAME_TH,
    FACULTY_NAME_ZH,
    FACULTY_WEBSITE,
    PROGRAMS,
)
from .schema import Category, Language
from .smalltalk import KINDS as SMALLTALK_KINDS

KMITL_SITE = "https://www.kmitl.ac.th"
KMITL_REG = "https://www.reg.kmitl.ac.th"
KMITL_ADMISSION = "https://www1.reg.kmitl.ac.th/admission"
TCAS = "https://www.mytcas.com"

_PROGRAM_IDS = "/".join(p.id for p in PROGRAMS)
_FACULTY_LIST_TH = f"{FACULTY_NAME_TH} ({_PROGRAM_IDS})"
_FACULTY_LIST_EN = f"{FACULTY_NAME_EN} ({_PROGRAM_IDS})"
_FACULTY_LIST_ZH = f"{FACULTY_NAME_ZH}（{_PROGRAM_IDS}）"

_GENERAL_CHANNELS: dict[str, dict[str, str]] = {
    "weather": {
        "th": "แอปพยากรณ์อากาศหรือเว็บไซต์กรมอุตุนิยมวิทยา (tmd.go.th)",
        "en": "a weather app or the Thai Meteorological Department site (tmd.go.th)",
        "zh": "天气应用或泰国气象局网站 (tmd.go.th)",
    },
    "cooking": {
        "th": "เว็บไซต์หรือแอปสูตรอาหาร เช่น Wongnai Cooking",
        "en": "a cooking site or recipe app such as Wongnai Cooking",
        "zh": "菜谱网站或应用，例如 Wongnai Cooking",
    },
    "coding": {
        "th": "เอกสารประกอบภาษานั้น ๆ หรือชุมชนนักพัฒนา เช่น Stack Overflow",
        "en": "the language's documentation or a developer community such as Stack Overflow",
        "zh": "该语言的官方文档或开发者社区，例如 Stack Overflow",
    },
    "lottery": {"th": "เว็บไซต์สำนักงานสลากกินแบ่งรัฐบาล (glo.or.th)", "en": "the Government Lottery Office site (glo.or.th)", "zh": "泰国政府彩票局网站 (glo.or.th)"},
    "finance": {"th": "เว็บไซต์ข่าวการเงินหรือแอปธนาคาร", "en": "a finance news site or your banking app", "zh": "财经新闻网站或银行应用"},
    "sports": {"th": "เว็บไซต์ข่าวกีฬาหรือแอปผลบอล", "en": "a sports news site or live-score app", "zh": "体育新闻网站或比分应用"},
    "entertainment": {"th": "เว็บไซต์รีวิวหนัง/เพลง หรือแพลตฟอร์มสตรีมมิง", "en": "a movie/music review site or streaming platform", "zh": "影视/音乐评论网站或流媒体平台"},
    "health": {"th": "แพทย์ เภสัชกร หรือสายด่วน 1669 กรณีฉุกเฉิน", "en": "a doctor, a pharmacist, or the 1669 emergency line", "zh": "医生、药剂师或紧急热线 1669"},
    "travel": {"th": "แอปท่องเที่ยวหรือเว็บไซต์ ททท. (tourismthailand.org)", "en": "a travel app or the TAT site (tourismthailand.org)", "zh": "旅游应用或泰国旅游局网站 (tourismthailand.org)"},
    "politics": {"th": "สำนักข่าวที่น่าเชื่อถือ", "en": "a reputable news outlet", "zh": "可靠的新闻媒体"},
    "chitchat": {"th": "", "en": "", "zh": ""},
    "default": {
        "th": "เครื่องมือค้นหาทั่วไปหรือผู้ช่วย AI ทั่วไป",
        "en": "a general search engine or general-purpose assistant",
        "zh": "通用搜索引擎或通用 AI 助手",
    },
}

_KMITL_CHANNELS: dict[str, dict[str, str]] = {
    "dorm": {
        "th": "สำนักงานหอพักนักศึกษา สจล.",
        "en": "the KMITL Student Dormitory Office",
        "zh": "先皇技术学院学生宿舍办公室",
    },
    "scholarship": {
        "th": "สำนักงานกิจการนักศึกษา สจล.",
        "en": "the KMITL Student Affairs Office",
        "zh": "先皇技术学院学生事务办公室",
    },
    "faculty": {
        "th": f"เว็บไซต์ของคณะนั้นโดยตรง หรือสำนักทะเบียนและประมวลผล สจล. ({KMITL_REG})",
        "en": f"that faculty's own website or the KMITL Office of the Registrar ({KMITL_REG})",
        "zh": f"该学院官网或先皇技术学院注册处（{KMITL_REG}）",
    },
    "default": {
        "th": f"สำนักทะเบียนและประมวลผล สจล. ({KMITL_REG})",
        "en": f"the KMITL Office of the Registrar ({KMITL_REG})",
        "zh": f"先皇技术学院注册处（{KMITL_REG}）",
    },
}


def _lang(language: Language) -> str:
    return language if language in ("th", "en", "zh") else "en"


# --------------------------------------------------------------------------- #
# greeting_smalltalk — warm, useful, never a refusal
# --------------------------------------------------------------------------- #
# Example questions the bot can actually answer (curriculum documents).  Thai ones
# are phrased the way a high-school student would type them.
_EXAMPLES: dict[str, tuple[str, ...]] = {
    "th": (
        "AIT เรียนกี่ปี จบแล้วทำงานอะไรได้บ้าง",
        "DSBA ต้องเรียนคณิตเยอะไหม",
        "IT ปกติ กับ IT อินเตอร์ (BIT) ต่างกันยังไง",
        "ปี 1 เทอม 1 ต้องเรียนวิชาอะไรบ้าง",
        "หลักสูตร IT มีกี่หน่วยกิต",
        "สมัครเข้า AIT ต้องมีคุณสมบัติอะไรบ้าง",
        "BIT เรียนเป็นภาษาอังกฤษทั้งหมดไหม",
        "เรียน DSBA ต้องเขียนโปรแกรมเป็นไหม",
        "จบ IT แล้วไปทำงานสายไหนได้บ้าง",
    ),
    "en": (
        "How many years is the AIT program?",
        "What jobs can DSBA graduates do?",
        "What is the difference between IT and BIT?",
        "Which courses are in the first semester of IT?",
        "How many credits is the BIT program?",
        "What are the admission requirements for AIT?",
        "Is BIT taught entirely in English?",
    ),
    "zh": (
        "AIT专业要读几年？",
        "DSBA毕业后能做什么工作？",
        "IT和BIT有什么区别？",
        "IT专业第一学期学什么课？",
        "BIT专业总共多少学分？",
        "申请AIT需要什么条件？",
    ),
}
_PROGRAMS_TH = ", ".join(p.id for p in PROGRAMS)


def _examples(lang: str, n: int, seed: int | None) -> list[str]:
    pool = _EXAMPLES[lang]
    start = (seed or 0) % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(n)]


def _quoted(items: list[str], lang: str) -> str:
    q = [f"“{x}”" for x in items]
    if lang == "th":
        return " ".join(q[:-1]) + (" หรือ " if len(q) > 1 else "") + q[-1]
    if lang == "zh":
        return "".join(q[:-1]) + ("或" if len(q) > 1 else "") + q[-1]
    return ", ".join(q[:-1]) + (" or " if len(q) > 1 else "") + q[-1]


def smalltalk_reply(language: Language, kind: str | None = "greeting", seed: int | None = None) -> str:
    """Warm reply for greetings / thanks / ok / bye / who-are-you / vague help openers.

    ``seed`` (e.g. a hash of the message) rotates the example questions so the
    same message always gets the same reply while different greetings vary.
    """
    lang = _lang(language)
    kind = kind if kind in SMALLTALK_KINDS else "greeting"
    ex3 = _quoted(_examples(lang, 3, seed), lang)
    ex2 = _quoted(_examples(lang, 2, seed), lang)
    if lang == "th":
        faculty = f"{FACULTY_NAME_TH} สจล."
        return {
            "greeting": f"สวัสดีค่ะ 👋 ฉันเป็นผู้ช่วยตอบคำถามเกี่ยวกับหลักสูตรทั้ง 4 สาขาของ{faculty} ({_PROGRAMS_TH}) ค่ะ ลองถามได้เลย เช่น {ex3}",
            "help": f"ได้เลยค่ะ ถามมาได้เลย ฉันตอบคำถามเกี่ยวกับหลักสูตร 4 สาขาของ{faculty} ({_PROGRAMS_TH}) ได้ค่ะ เช่น {ex3}",
            "identity": f"ฉันเป็นแชตบอตผู้ช่วยของ{faculty} ค่ะ ตอบคำถามเกี่ยวกับหลักสูตร 4 สาขา ({_PROGRAMS_TH}) ได้ เช่น รายวิชา หน่วยกิต การรับเข้า และอาชีพหลังจบ ลองถามได้เลย เช่น {ex2}",
            "thanks": f"ยินดีค่ะ 😊 ถ้ามีคำถามเกี่ยวกับหลักสูตรของ{faculty} เพิ่มเติม ถามได้เลยนะคะ",
            "ack": "ค่ะ 👍 ถ้ามีอะไรอยากถามเพิ่มเกี่ยวกับหลักสูตร ถามได้เลยนะคะ",
            "farewell": f"ขอบคุณที่แวะมาคุยนะคะ 👋 ถ้าอยากรู้อะไรเกี่ยวกับหลักสูตรของ{faculty} อีก กลับมาถามได้เสมอค่ะ",
        }[kind]
    if lang == "zh":
        faculty = f"先皇技术学院（KMITL）{FACULTY_NAME_ZH}"
        return {
            "greeting": f"你好！👋 我可以回答{faculty}四个专业（{_PROGRAMS_TH}）的课程问题。试试问我：{ex3}。",
            "help": f"当然可以！请直接提问，我负责{faculty}四个专业（{_PROGRAMS_TH}）的课程问题，例如{ex3}。",
            "identity": f"我是{faculty}的课程助手。我可以回答四个专业（{_PROGRAMS_TH}）的课程、学分、入学和就业问题。例如：{ex2}。",
            "thanks": f"不客气！😊 如果还有关于{FACULTY_NAME_ZH}课程的问题，随时问我。",
            "ack": "好的 👍 还有其他课程问题，随时可以问我。",
            "farewell": f"再见！👋 想了解{FACULTY_NAME_ZH}的课程时，随时回来问我。",
        }[kind]
    faculty = f"KMITL's {FACULTY_NAME_EN}"
    return {
        "greeting": f"Hi! 👋 I answer questions about the four programs of {faculty} ({_PROGRAMS_TH}). Try something like {ex3}.",
        "help": f"Of course! Ask away, I cover the four programs of {faculty} ({_PROGRAMS_TH}), for example {ex3}.",
        "identity": f"I'm the assistant chatbot of {faculty}. I can answer questions about its four B.Sc. programs ({_PROGRAMS_TH}): courses, credits, admission and careers. Try asking {ex2}.",
        "thanks": f"You're welcome! 😊 If you have any more questions about the {FACULTY_NAME_EN} programs, just ask.",
        "ack": "Great 👍 Feel free to ask anything else about the programs.",
        "farewell": f"Bye for now! 👋 Come back any time you want to ask about the {FACULTY_NAME_EN} programs.",
    }[kind]


_QUOTED_RE = re.compile(r"“[^”]*”|\"[^\"]*\"")
_URL_RE = re.compile(r"https?://\S+|\b[a-z0-9.-]+\.(?:ac\.th|go\.th|or\.th|com|org|edu|in\.th)\b", re.IGNORECASE)
_ABBREV_RE = re.compile(r"สจล\.|B\.Sc\.|Ph\.D\.|M\.Sc\.|e\.g\.|i\.e\.|etc\.|www\.|\.ac\.th|\.com|\.org|\.go\.th|\.or\.th", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"[.!?。！？]+|\n+|(?:นะคะ|นะครับ|ค่ะ|ครับ|จ้า|นะ)(?=\s|$)")


def sentence_count(text: str) -> int:
    """Rough sentence count used by the reply rubric (quoted examples and abbreviations don't split)."""
    masked = _ABBREV_RE.sub("X", _URL_RE.sub("X", _QUOTED_RE.sub("X", text)))
    parts = [p for p in _SENTENCE_SPLIT_RE.split(masked) if p and p.strip(" ,;:")]
    return len(parts)


def general_reply(language: Language, topic: str | None = None) -> str:
    lang = _lang(language)
    channel = _GENERAL_CHANNELS.get(topic or "default", _GENERAL_CHANNELS["default"])[lang]
    if lang == "th":
        base = f"ขออภัยค่ะ ฉันตอบได้เฉพาะคำถามเกี่ยวกับหลักสูตรของ{_FACULTY_LIST_TH} สจล. เท่านั้น"
        return base + (f" สำหรับเรื่องนี้แนะนำให้ลองใช้{channel} นะคะ" if channel else " หากมีคำถามเกี่ยวกับหลักสูตร ถามได้เลยค่ะ")
    if lang == "zh":
        base = f"抱歉，我只能回答有关先皇技术学院（KMITL）{_FACULTY_LIST_ZH}课程的问题。"
        return base + (f"关于这个话题，建议您使用{channel}。" if channel else "如有课程相关问题，欢迎提问。")
    base = f"Sorry, I can only answer questions about the curricula of KMITL's {_FACULTY_LIST_EN}."
    return base + (f" For this, please try {channel}." if channel else " Feel free to ask about any of those programs.")


def other_university_reply(
    language: Language, university_name: str | None = None, admissions_url: str | None = None, *, foreign: bool = False
) -> str:
    """``foreign=True`` = not a TCAS university: point to its own site only.  Unknown Thai → TCAS."""
    lang = _lang(language)
    if not foreign and admissions_url is None:
        admissions_url = TCAS
    if lang == "th":
        who = university_name or "มหาวิทยาลัยดังกล่าว"
        head = f"ขออภัยค่ะ ฉันให้ข้อมูลได้เฉพาะหลักสูตรของ{_FACULTY_LIST_TH} สจล. เท่านั้น "
        if admissions_url is None:
            return head + f"สำหรับข้อมูลของ{who} แนะนำให้ดูที่เว็บไซต์รับสมัครอย่างเป็นทางการของมหาวิทยาลัยนั้น นะคะ"
        if admissions_url == TCAS:
            return head + f"สำหรับข้อมูลของ{who} แนะนำให้ดูที่ระบบ TCAS ({TCAS}) นะคะ"
        return head + f"สำหรับข้อมูลของ{who} แนะนำให้ดูที่เว็บไซต์รับสมัครอย่างเป็นทางการ {admissions_url} หรือระบบ TCAS ({TCAS}) นะคะ"
    if lang == "zh":
        who = university_name or "该大学"
        head = f"抱歉，我只能提供先皇技术学院（KMITL）{_FACULTY_LIST_ZH}的课程信息。"
        if admissions_url is None:
            return head + f"关于{who}的信息，请访问该校的官方招生网站。"
        if admissions_url == TCAS:
            return head + f"关于{who}的信息，请访问泰国 TCAS 系统（{TCAS}）。"
        return head + f"关于{who}的信息，请访问其官方招生网站 {admissions_url} 或泰国 TCAS 系统（{TCAS}）。"
    who = university_name or "that university"
    head = f"Sorry, I only cover the curricula of KMITL's {_FACULTY_LIST_EN}. "
    if admissions_url is None:
        return head + f"For {who}, please check its official admissions website."
    if admissions_url == TCAS:
        return head + f"For {who}, please check the TCAS portal ({TCAS})."
    return head + f"For {who}, please check its official admissions site at {admissions_url} or the TCAS portal ({TCAS})."


def kmitl_out_of_scope_reply(
    language: Language,
    topic: str | None = None,
    faculty_name: str | None = None,
    faculty_url: str | None = None,
) -> str:
    """Redirect for KMITL topics the curriculum documents do not cover.

    When another KMITL faculty was identified (``topic == "faculty"`` and a
    ``faculty_name``), the reply names it and points at its website (or the
    central KMITL site when the faculty's own site is unknown).
    """
    lang = _lang(language)
    if topic == "faculty" and faculty_name:
        site = faculty_url or KMITL_SITE
        if lang == "th":
            return (
                f"ขออภัยค่ะ ข้อมูลของ{faculty_name} สจล. ไม่อยู่ในเอกสารหลักสูตรที่ฉันมี ฉันตอบได้เฉพาะเรื่องหลักสูตร/รายวิชา/"
                f"เกณฑ์การรับเข้าของ {_FACULTY_LIST_TH} สจล. เท่านั้น แนะนำให้ดูหลักสูตรของ{faculty_name}ได้ที่เว็บไซต์คณะ {site} "
                f"หรือสอบถามสำนักทะเบียนและประมวลผล สจล. ({KMITL_REG}) ส่วนข้อมูลคณะเทคโนโลยีสารสนเทศดูได้ที่ {FACULTY_WEBSITE} นะคะ"
            )
        if lang == "zh":
            return (
                f"抱歉，{faculty_name}的信息不在我掌握的课程文件范围内。我只能回答{_FACULTY_LIST_ZH}的课程、科目和入学要求。"
                f"建议您访问{faculty_name}官网 {site}，或联系先皇技术学院注册处（{KMITL_REG}）。信息技术学院官网：{FACULTY_WEBSITE}。"
            )
        return (
            f"Sorry, the {faculty_name} isn't covered by the curriculum documents I have. I can only answer about the programs, "
            f"courses and admission requirements of KMITL's {_FACULTY_LIST_EN}. Please see the {faculty_name}'s website at {site} "
            f"or contact the KMITL Office of the Registrar ({KMITL_REG}); the Faculty of IT's site is {FACULTY_WEBSITE}."
        )
    channel = _KMITL_CHANNELS.get(topic or "default", _KMITL_CHANNELS["default"])[lang]
    if lang == "th":
        return (
            f"ขออภัยค่ะ เรื่องนี้ไม่อยู่ในเอกสารหลักสูตรที่ฉันมีข้อมูล ฉันตอบได้เฉพาะเรื่องหลักสูตร/รายวิชา/เกณฑ์การรับเข้าของ "
            f"{_FACULTY_LIST_TH} สจล. เท่านั้น แนะนำให้ติดต่อ{channel} หรือดูที่เว็บไซต์คณะ {FACULTY_WEBSITE} นะคะ"
        )
    if lang == "zh":
        return (
            f"抱歉，这个问题不在我掌握的课程文件范围内。我只能回答{_FACULTY_LIST_ZH}的课程、科目和入学要求。"
            f"建议您联系{channel}，或访问学院官网 {FACULTY_WEBSITE}。"
        )
    return (
        f"Sorry, that isn't covered by the curriculum documents I have. I can only answer about the programs, courses and admission "
        f"requirements of KMITL's {_FACULTY_LIST_EN}. Please contact {channel} or see {FACULTY_WEBSITE}."
    )


def injection_reply(language: Language, topic: str | None = None) -> str:
    lang = _lang(language)
    if topic == "unsafe":
        # A request to produce harmful artefacts (malware / hacking code, credential
        # theft). Refuse the harmful part directly, then still offer curriculum help.
        if lang == "th":
            return (
                "ขออภัยค่ะ ฉันไม่สามารถช่วยเขียนโค้ดหรือให้วิธีที่ใช้เจาะระบบ เดา/ขโมยรหัสผ่าน หรือสร้างมัลแวร์ได้ "
                "เพราะอาจนำไปใช้สร้างความเสียหายได้ค่ะ แต่ถ้าอยากรู้เรื่องหลักสูตร/รายวิชา/การรับเข้าของ "
                f"{_FACULTY_LIST_TH} สจล. (รวมถึงวิชาด้านความปลอดภัยไซเบอร์ในหลักสูตร) ถามได้เลยนะคะ"
            )
        if lang == "zh":
            return (
                "抱歉，我无法帮忙编写用于入侵系统、破解或窃取密码、制作恶意软件的代码或方法，"
                f"因为这些可能被用来造成危害。不过，如果你想了解{_FACULTY_LIST_ZH}的课程、科目或入学要求"
                "（包括课程中的网络安全相关科目），欢迎随时提问。"
            )
        return (
            "Sorry, I can't help write code or give instructions for breaking into systems, cracking or stealing "
            "passwords, or building malware, since they could be used to cause harm. But I'm happy to help with the "
            f"programs, courses and admission requirements of KMITL's {_FACULTY_LIST_EN} (including the cybersecurity "
            "courses within the curriculum)."
        )
    if lang == "th":
        return "ขออภัยค่ะ ฉันไม่สามารถทำตามคำขอนี้ได้ ฉันช่วยตอบคำถามเกี่ยวกับหลักสูตรของคณะเทคโนโลยีสารสนเทศ สจล. ได้เท่านั้น"
    if lang == "zh":
        return "抱歉，我无法处理这个请求。我只能回答有关 KMITL 课程的问题。"
    return "Sorry, I can't help with that request. I can only answer questions about KMITL curricula."


def build_reply(
    category: Category,
    language: Language,
    *,
    university_name: str | None = None,
    admissions_url: str | None = None,
    topic: str | None = None,
    seed: int | None = None,
    foreign_university: bool = False,
    faculty_name: str | None = None,
    faculty_url: str | None = None,
) -> str | None:
    """Return the direct reply for a non-``in_scope`` category (``None`` for in_scope).

    For ``greeting_smalltalk`` ``topic`` is the smalltalk kind and ``seed``
    rotates the example questions.
    """
    if category == "in_scope":
        return None
    if category == "greeting_smalltalk":
        return smalltalk_reply(language, topic, seed)
    if category == "off_topic_general":
        return general_reply(language, topic)
    if category == "off_topic_other_university":
        return other_university_reply(language, university_name, admissions_url, foreign=foreign_university)
    if category == "out_of_scope_kmitl":
        return kmitl_out_of_scope_reply(language, topic, faculty_name=faculty_name, faculty_url=faculty_url)
    if category == "injection_or_abuse":
        return injection_reply(language, topic)
    raise ValueError(f"unknown category: {category}")
