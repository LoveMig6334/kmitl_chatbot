"""Cheap detection of greetings / thanks / acknowledgements / farewells /
bot-identity questions / vague help openers (``greeting_smalltalk``).

Pure functions, zero API calls.  The strict detector (:func:`detect_smalltalk`)
only fires when the *whole* message — after dropping emoji, punctuation,
laughter and politeness particles — is one of the known smalltalk cores.
Anything left over is content, so the rule abstains and the LLM decides
(mixed messages like "สวัสดีครับ AIT เรียนกี่ปี" are ``in_scope``).

:func:`smalltalk_kind` is the loose variant: it looks for a smalltalk core
anywhere in the text and is used only to pick the reply template once the LLM
has already said the message is smalltalk.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

SmalltalkKind = Literal["greeting", "thanks", "ack", "farewell", "identity", "help"]
KINDS: tuple[str, ...] = ("greeting", "thanks", "ack", "farewell", "identity", "help")

MAX_LEN = 80  # longer messages are never pure smalltalk

# Politeness / filler particles that carry no content.  Stripped from the ends of
# each whitespace token (Thai glues them to the word) and dropped when standalone.
_THAI_PARTICLE = (
    r"(?:ครับผม|ครับ|คับ|ครัช|กั๊บ|ฮับ|งับ|ค่ะ|คะ|ค๊ะ|ค่า|คร้าบ|คร้า|จ้า|จ้ะ|จ๊ะ|จ๋า|จ้าา|นะ|น้า|นะเนี่ย|ฮะ|ฮ่ะ|เจ้าค่ะ|ขอรับ"
    r"|หน่อย|ที|ด้วย|เลย|มาก|มากมาย|มากๆ|จริงๆ|จริง|เยอะ|หลาย|จัง|สุดๆ|เถอะ|หน่อยสิ|สิ|ซิ|เนอะ|อ่ะ|อะ|อ่า|ผม|ฉัน|เรา|หนู|ดิฉัน|กระผม|ค้าบ|คร๊าบ|ค่ะะ)"
)
_THAI_PARTICLE_TAIL = re.compile(rf"(?:{_THAI_PARTICLE})+$")
_THAI_PARTICLE_HEAD = re.compile(r"^(?:ครับ|คับ|ค่ะ|คะ|จ้า|เอ่อ|เออ|อ่า|อืม|อือ|เอิ่ม|คือ|คือว่า|แบบว่า|แบบ)+")
_FILLER_TOKENS = {
    "please", "pls", "plz", "so", "much", "very", "a", "lot", "lots", "really", "indeed", "alot",
    "sir", "madam", "man", "bro", "dude", "mate", "friend",
    "kub", "krub", "krab", "ka", "kha", "na", "ja", "jaa", "naka", "nakrub", "khrap", "khap",
    "um", "uh", "hmm", "hm", "ah", "oh",
    "了", "啊", "呀", "哦", "嗯", "呢", "吧", "哈", "啦", "哟", "呐", "一下", "请", "请问",
}

# One-off noise
_LAUGH = re.compile(r"^(?:5{3,}|ฮ่า+|ฮะฮ่า+|ha(?:ha)+h?|he(?:he)+|lol+|lmao|rofl|哈{2,}|嘿嘿|呵呵|555\+)$")
_REPEAT_LATIN = re.compile(r"([a-z])\1{2,}")  # helloooo -> hello, heyyy -> hey
_REPEAT_THAI = re.compile(r"([ะาิีึืุูเแโใไๆ])\1+")  # ค่าาา -> ค่า
_MAI_YAMOK = re.compile(r"ๆ")

# --------------------------------------------------------------------------- #
# Cores (matched against the normalised, particle-free message)
# --------------------------------------------------------------------------- #
_ACK_WORDS = (
    r"โอเค|โอเช|โอเคร|okie|okies|ok|okay|okey|kk|k|ได้|ได้เลย|ได้ค่ะ|เข้าใจ|เข้าใจแล้ว|รับทราบ|ทราบแล้ว|รู้แล้ว|อ๋อ|อ่อ|อือ|อืม|เออ|ใช่|อ่าฮะ|โอเคเลย|ตกลง|ดี|ดีมาก|เยี่ยม|สุดยอด|เจ๋ง|ชัดเจน|เคลียร์|clear"
    r"|got it|i see|noted|understood|alright|aight|sure|cool|nice|great|good|fine|yes|yep|yeah|yup|ya|no|nope|nah|right|roger|perfect|awesome|gotcha|copy|ic|oki|okk"
    r"|明白|明白了|知道了|好的|好|好吧|嗯|哦|噢|了解|收到|懂了|行|可以|是的|对"
)
_GREETING_WORDS = (
    r"สวัสดี|สวัดดี|สวัสดิ|หวัดดี|วัดดี|ดีจ้า|ดี|ทักทาย|ฮัลโหล|ฮัลโล|เฮลโล|ฮาย|ไฮ|เฮ้|โย่|มีใครอยู่ไหม|มีใครอยู่มั้ย|มีใครอยู่|ใครอยู่บ้าง|อยู่ไหม|อยู่มั้ย"
    r"|สบายดีไหม|สบายดีมั้ย|สบายดีปะ|สบายดี|เป็นไงบ้าง|เป็นยังไงบ้าง|เป็นไง|กินข้าวยัง|กินข้าวหรือยัง|ทำอะไรอยู่|ว่างไหม|ว่างมั้ย|ตื่นยัง|หลับยัง|ยังอยู่ไหม|ยังอยู่มั้ย|อรุณสวัสดิ์|ราตรีสวัสดิ์|ทดสอบ|เทส|เทสต์|ทดลอง|test|testing|ping"
    r"|(?:hi|hii|hello|helo|hallo|hullo|hey|heya|hiya|yo|greetings|howdy)(?: there| again| all| everyone| guys| bot| friend| you| u| dear)?|good morning|good afternoon|good evening|good day|morning|afternoon|evening|sup|whats up|wassup|wazzup|whatsup|hola|bonjour|namaste|salut|ciao|hej|aloha"
    r"|how are you|how r u|how are u|how are you doing|how are you today|how do you do|hows it going|how is it going|how you doing|hows everything|whats new|anyone there|anybody there|is anyone there|are you there|you there|u there|r u there|are you online|are you awake|still there"
    r"|你好|您好|你们好|嗨|哈喽|哈罗|嘿|早上好|早安|晚上好|晚安|下午好|大家好|喂|哈啰|你好吗|您好吗|最近怎么样|最近好吗|过得怎么样|过得好吗|今天过得怎么样|吃饭了吗|吃了吗|在吗|有人吗|在不在|你在吗"
)
_THANKS_WORDS = (
    r"ขอบคุณ|ขอบใจ|ขอบพระคุณ|แต้งกิ้ว|แต๊งกิ้ว|แต้งค์|แต๊งค์|แต้ง|ขอบคุน|ขอบคุณค่ะ|ขอบคุณครับ"
    r"|(?:thanks|thank you|thank u|thankyou|thankss|thx|thnx|thanx|tks|ty|tysm|tyvm|cheers|many thanks)(?: again| for that| for the help| for your help| for the info| for the information| for helping| for everything| you| u| bot)?|much appreciated|appreciate it|appreciated"
    r"|谢谢|谢了|感谢|多谢|谢啦|谢谢你|谢谢您|非常感谢|太感谢了|感谢你|多谢了"
)
_FAREWELL_WORDS = (
    r"บาย|บ๊ายบาย|บายบาย|บ๊ะบาย|ลาก่อน|ไปก่อน|ไปละ|ไปล่ะ|ไปแล้ว|แค่นี้|แค่นี้ก่อน|พอแค่นี้|พอก่อน|เจอกันใหม่|เจอกัน|ไว้เจอกัน|ฝันดี|นอนละ|นอนก่อน|ไปนอนละ|ขอตัวก่อน|ขอตัว|ไว้คุยใหม่|ไว้มาใหม่|แค่นี้แหละ"
    r"|bye|byee|bye bye|byebye|goodbye|good bye|see you|see ya|see u|cya|later|catch you later|talk later|good night|goodnight|gn|gotta go|g2g|im off|i am off|im leaving|take care|thats all|that is all|thats it|done|im done|i am done|nothing else|no more questions"
    r"|再见|拜拜|拜|晚安|回头见|下次见|再会|我走了|先走了|就这样|没了|没有了|没问题了|不用了"
)
_IDENTITY_WORDS = (
    r"คุณคือใคร|คุณเป็นใคร|เธอคือใคร|เธอเป็นใคร|นี่ใคร|นี่คือใคร|คุยกับใคร|คุยกับใครอยู่|กำลังคุยกับใคร|กำลังคุยกับใครอยู่|คุยอยู่กับใคร|คุณชื่ออะไร|เธอชื่ออะไร|ชื่ออะไร|คุณชื่อ|มีชื่อไหม"
    r"|คุณทำอะไรได้|ทำอะไรได้|ทำอะไรได้บ้าง|คุณทำอะไรได้บ้าง|ช่วยอะไรได้บ้าง|คุณช่วยอะไรได้บ้าง|ช่วยอะไรได้|ตอบอะไรได้บ้าง|ตอบอะไรได้|ถามอะไรได้บ้าง|ถามอะไรได้|ถามอะไรได้บ้างคะ|ถามได้แค่ไหน"
    r"|คุณคือบอทใช่ไหม|คุณคือบอทหรือเปล่า|เป็นบอทหรือคน|เป็นคนหรือบอท|บอทหรือคน|คนหรือบอท|คุณเป็นบอทใช่ไหม|เป็นบอทใช่ไหม|เป็นบอทเหรอ|บอทเหรอ|บอทใช่ไหม|คุณเป็น ai ใช่ไหม|เป็น ai ใช่ไหม|เป็น ai เหรอ|คุณเป็น ai หรือเปล่า|คุณเป็นคนไหม|เป็นคนจริงไหม|เป็นคนจริงหรือเปล่า|ตอบอัตโนมัติใช่ไหม"
    r"|who are you|who r u|who are u|who is this|who am i talking to|who am i chatting with|who am i speaking to|what are you|what is this|what is this bot|whats this|what is your name|whats your name|what should i call you|do you have a name"
    r"|what can you do|what do you do|what can u do|how can you help|how can you help me|what can you help with|what can you help me with|what can i ask|what can i ask you|what do you know|what are you for|what is this for|what is this bot for|what are you able to do|what topics can you answer"
    r"|(?:are you|are u|r u|you|u)(?: a| an)? (?:bot|robot|human|ai|real|real person|chatbot|machine|person|computer)|are you a bot|are you human|are you a human|are you an ai|are you ai|are you real|are you a real person|are you a robot|are you chatgpt|is this a bot|am i talking to a bot|is this a real person|bot or human"
    r"|你是谁|你是谁啊|你叫什么|你叫什么名字|你是什么|这是什么|你能做什么|你会做什么|你会什么|你能帮我什么|你能帮什么忙|你可以做什么|你能回答什么|你能回答哪些问题|我能问什么|我可以问什么|你是机器人吗|你是人吗|你是ai吗|你是真人吗|你是人工智能吗|我在跟谁说话|我在和谁聊天"
)
_HELP_WORDS = (
    r"ช่วย|ช่วยหน่อย|ช่วยด้วย|ช่วยที|ช่วย(?:หน่อย|ด้วย|ที)?ได้(?:ไหม|มั้ย|ปะ|ป่ะ|บ้าง)|ขอความช่วยเหลือ|ถามได้ไหม|ถามได้มั้ย|ถามได้ปะ|ถามได้ป่ะ|ถามหน่อย|ขอถามหน่อย|ขอถาม|ขอถามอะไรหน่อย|ขอถามอะไร|มีคำถาม|มีเรื่องอยากถาม|มีเรื่องจะถาม|อยากถาม|อยากถามหน่อย|อยากถามอะไรหน่อย|มีคำถามค่ะ|มีคำถามครับ|มีเรื่องสงสัย|สงสัย"
    r"|อยากรู้เรื่องเรียนต่อ|อยากรู้เรื่องการเรียนต่อ|อยากรู้เรื่องเรียน|อยากรู้เรื่องการเรียน|อยากรู้|อยากปรึกษา|ขอคำปรึกษาหน่อย|ขอคำปรึกษา|ปรึกษาหน่อย|ปรึกษา|สอบถามหน่อย|ขอสอบถามหน่อย|ขอสอบถาม|สอบถาม|อยากสอบถาม|ขอข้อมูลหน่อย|ขอข้อมูล|อยากได้ข้อมูล|รบกวนหน่อย|รบกวนสอบถาม|รบกวนถาม|รบกวน|ขอคำแนะนำ|ขอคำแนะนำหน่อย|แนะนำหน่อย"
    r"|help|help me|i need help|need help|can i ask|can i ask something|can i ask a question|can i ask you something|may i ask|may i ask something|may i ask a question|i have a question|i have a few questions|i have some questions|i got a question|question|questions|a question|quick question|i want to ask|i want to ask something|id like to ask|i would like to ask|i d like to ask|need some help|can you help|can you help me|could you help me|can u help|can u help me|could you help|i need some info|i need information|i need some information|any help|help please"
    r"|我想问|我想问一下|我有个问题|我有问题|我有一个问题|可以问吗|可以问一下吗|能问个问题吗|能问吗|请问|帮帮我|帮我|求助|帮忙|需要帮助|我需要帮助|我想咨询|咨询一下|想咨询|想问一下|问一下|问个问题|请教一下|请教"
)


def _alternatives(words: str) -> list[str]:
    """Split a regex alternation on top-level ``|`` (respects parentheses)."""
    out, depth, cur = [], 0, []
    for ch in words:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "|" and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [a for a in out if a]


# Strict matcher: the whole normalised message must be a sequence of content-free
# cores / particles.  Alternatives are ordered longest-first inside an atomic
# group so the regex never backtracks (messages are ≤ MAX_LEN anyway).
_PARTICLE_WORDS = r"ครับ|คับ|ค่ะ|คะ|จ้า|นะ|ค่า|ครัช|งับ|ผม|ฉัน|เรา"
_ALL_ALTS = sorted(
    set(
        _alternatives(_ACK_WORDS) + _alternatives(_GREETING_WORDS) + _alternatives(_THANKS_WORDS)
        + _alternatives(_FAREWELL_WORDS) + _alternatives(_IDENTITY_WORDS) + _alternatives(_HELP_WORDS)
        + _alternatives(_PARTICLE_WORDS) + ["ใคร", "คือใคร", "เป็นใคร"]
    ),
    key=len,
    reverse=True,
)
_STRICT_RE = re.compile(r"^(?:(?>" + "|".join(_ALL_ALTS) + r")\s*)+$")

# Kind priority when several cores co-occur ("ขอบคุณ ช่วยได้เยอะเลย" is thanks, not help;
# "สวัสดีครับ ขอถามหน่อย" is a help opener).  The core may appear anywhere; ASCII
# cores need word boundaries.
_LOOSE: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (kind, re.compile(rf"(?<![a-z])(?:{words})(?![a-z])"))
    for kind, words in (
        ("thanks", _THANKS_WORDS),
        ("farewell", _FAREWELL_WORDS),
        ("identity", _IDENTITY_WORDS),
        ("help", _HELP_WORDS),
        ("greeting", _GREETING_WORDS),
    )
)


def _is_symbol(ch: str) -> bool:
    cat = unicodedata.category(ch)
    return cat.startswith(("S", "P", "C")) or ch in "\u200b‍️"


def normalize(text: str) -> str:
    """Lower-case, drop emoji/punctuation, collapse stretched letters, strip particles."""
    # NFKC folds full-width punctuation/letters but would decompose Thai SARA AM (ำ), so skip Thai.
    t = "".join(ch if "\u0e00" <= ch <= "\u0e7f" else unicodedata.normalize("NFKC", ch) for ch in text)
    t = t.lower().replace("'", "").replace("’", "")
    t = "".join(" " if _is_symbol(ch) else ch for ch in t)
    t = _MAI_YAMOK.sub(" ", t)
    t = re.sub(r"5{3,}", " ", t)  # "สวัสดี555" -> "สวัสดี"
    t = _REPEAT_LATIN.sub(r"\1", t)
    t = _REPEAT_THAI.sub(r"\1", t)
    tokens: list[str] = []
    for tok in t.split():
        if _LAUGH.match(tok):
            continue
        tok = _THAI_PARTICLE_HEAD.sub("", tok)
        tok = _THAI_PARTICLE_TAIL.sub("", tok)
        if not tok or tok in _FILLER_TOKENS:
            continue
        tokens.append(tok)
    return " ".join(tokens)


def _has_letters(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def detect_smalltalk(text: str) -> SmalltalkKind | None:
    """Strict: the whole message is smalltalk (no answerable content) → its kind, else ``None``."""
    stripped = text.strip()
    if len(stripped) > MAX_LEN:
        return None
    if not _has_letters(stripped):
        return "greeting"  # empty, emoji-only, stickers-as-text ("55555", "!!!")
    core = normalize(stripped)
    if not core:
        return "ack"  # only particles survived: "ครับๆ", "ค่ะ", "จ้า"
    if _STRICT_RE.match(core):
        return _loose_kind(core) or ("identity" if "ใคร" in core else "ack")
    return None


def _loose_kind(core: str) -> SmalltalkKind | None:
    """Bare "ใคร" is deliberately not a hint ("ใครสอนวิชานี้" is a real question)."""
    for kind, pat in _LOOSE:
        if pat.search(core):
            return kind  # type: ignore[return-value]
    return None


def smalltalk_kind(text: str) -> SmalltalkKind | None:
    """Loose hint for template selection: the highest-priority smalltalk core found anywhere."""
    return detect_smalltalk(text) or _loose_kind(normalize(text))
