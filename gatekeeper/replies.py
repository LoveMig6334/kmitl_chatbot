"""Fixed-style refusal / redirect templates, selected by category × language.

Pure functions only.  ``other`` languages fall back to English.  Injection
replies are deliberately short and never mention internals.
"""

from __future__ import annotations

from .config import (
    FACULTY_NAME_EN,
    FACULTY_NAME_TH,
    FACULTY_NAME_ZH,
    FACULTY_WEBSITE,
    PROGRAMS,
)
from .schema import Category, Language

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
        "th": "สำนักงานหอพักนักศึกษา สจล. หรือเว็บไซต์สถาบัน",
        "en": "the KMITL Student Dormitory Office or the institute website",
        "zh": "先皇技术学院学生宿舍办公室或学院官网",
    },
    "scholarship": {
        "th": "สำนักงานกิจการนักศึกษา สจล. หรือเว็บไซต์ของคณะ",
        "en": "the KMITL Student Affairs Office or the faculty website",
        "zh": "学生事务办公室或学院官网",
    },
    "faculty": {
        "th": "เว็บไซต์ของคณะนั้นโดยตรง หรือสำนักทะเบียนและประมวลผล สจล.",
        "en": "that faculty's own website or the KMITL Office of the Registrar",
        "zh": "该学院官网或先皇技术学院注册处",
    },
    "default": {
        "th": "สำนักทะเบียนและประมวลผล สจล.",
        "en": "the KMITL Office of the Registrar",
        "zh": "先皇技术学院注册处",
    },
}


def _lang(language: Language) -> str:
    return language if language in ("th", "en", "zh") else "en"


def general_reply(language: Language, topic: str | None = None) -> str:
    lang = _lang(language)
    channel = _GENERAL_CHANNELS.get(topic or "default", _GENERAL_CHANNELS["default"])[lang]
    if lang == "th":
        base = f"ขออภัยค่ะ ฉันตอบได้เฉพาะคำถามเกี่ยวกับหลักสูตรของ{_FACULTY_LIST_TH} สจล. เท่านั้น"
        return base + (f" สำหรับเรื่องนี้แนะนำให้ลองใช้{channel}นะคะ" if channel else " หากมีคำถามเกี่ยวกับหลักสูตร ถามได้เลยค่ะ")
    if lang == "zh":
        base = f"抱歉，我只能回答有关先皇技术学院（KMITL）{_FACULTY_LIST_ZH}课程的问题。"
        return base + (f"关于这个话题，建议您使用{channel}。" if channel else "如有课程相关问题，欢迎提问。")
    base = f"Sorry, I can only answer questions about the curricula of KMITL's {_FACULTY_LIST_EN}."
    return base + (f" For this, please try {channel}." if channel else " Feel free to ask about any of those programs.")


def other_university_reply(language: Language, university_name: str | None = None, admissions_url: str | None = None) -> str:
    lang = _lang(language)
    url = admissions_url or TCAS
    if lang == "th":
        who = university_name or "มหาวิทยาลัยดังกล่าว"
        return (
            f"ขออภัยค่ะ ฉันให้ข้อมูลได้เฉพาะหลักสูตรของ{_FACULTY_LIST_TH} สจล. เท่านั้น "
            f"สำหรับข้อมูลของ{who} แนะนำให้ดูที่เว็บไซต์รับสมัครอย่างเป็นทางการ {url} หรือระบบ TCAS ({TCAS}) นะคะ"
        )
    if lang == "zh":
        who = university_name or "该大学"
        return (
            f"抱歉，我只能提供先皇技术学院（KMITL）{_FACULTY_LIST_ZH}的课程信息。"
            f"关于{who}的信息，请访问其官方招生网站 {url} 或泰国 TCAS 系统（{TCAS}）。"
        )
    who = university_name or "that university"
    return (
        f"Sorry, I only cover the curricula of KMITL's {_FACULTY_LIST_EN}. "
        f"For {who}, please check its official admissions site at {url} or the TCAS portal ({TCAS})."
    )


def kmitl_out_of_scope_reply(language: Language, topic: str | None = None) -> str:
    lang = _lang(language)
    channel = _KMITL_CHANNELS.get(topic or "default", _KMITL_CHANNELS["default"])[lang]
    if lang == "th":
        return (
            f"ขออภัยค่ะ เรื่องนี้ไม่อยู่ในเอกสารหลักสูตรที่ฉันมีข้อมูล ฉันตอบได้เฉพาะเรื่องหลักสูตร/รายวิชา/เกณฑ์การรับเข้าของ "
            f"{_FACULTY_LIST_TH} สจล. เท่านั้น แนะนำให้ติดต่อ{channel} ({KMITL_REG}) หรือเว็บไซต์คณะ {FACULTY_WEBSITE} นะคะ"
        )
    if lang == "zh":
        return (
            f"抱歉，这个问题不在我掌握的课程文件范围内。我只能回答{_FACULTY_LIST_ZH}的课程、科目和入学要求。"
            f"建议您联系{channel}（{KMITL_REG}）或访问学院官网 {FACULTY_WEBSITE}。"
        )
    return (
        f"Sorry, that isn't covered by the curriculum documents I have. I can only answer about the programs, courses and admission "
        f"requirements of KMITL's {_FACULTY_LIST_EN}. Please contact {channel} ({KMITL_REG}) or see {FACULTY_WEBSITE}."
    )


def injection_reply(language: Language) -> str:
    lang = _lang(language)
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
) -> str | None:
    """Return the direct reply for a non-``in_scope`` category (``None`` for in_scope)."""
    if category == "in_scope":
        return None
    if category == "off_topic_general":
        return general_reply(language, topic)
    if category == "off_topic_other_university":
        return other_university_reply(language, university_name, admissions_url)
    if category == "out_of_scope_kmitl":
        return kmitl_out_of_scope_reply(language, topic)
    if category == "injection_or_abuse":
        return injection_reply(language)
    raise ValueError(f"unknown category: {category}")
