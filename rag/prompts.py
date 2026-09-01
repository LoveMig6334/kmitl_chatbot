"""Prompts for the answer layer (Thai).  Pure data + small builders.

``SYSTEM_PROMPT`` must stay small (~600 estimated tokens) — the whole request
has to fit an ~8K context together with up to ``CONTEXT_TOKEN_BUDGET`` tokens
of retrieved passages.  The few-shot facts are deliberately fictional (they do
not match any fixture or eval case) so a model that copies them is caught by
the number-grounding check.
"""

from __future__ import annotations

from api.answerer import Turn
from gatekeeper.config import FACULTY_WEBSITE

LANGUAGE_NAMES = {"th": "ไทย", "en": "English (ตอบเป็นภาษาอังกฤษทั้งหมด)", "zh": "中文 (ตอบเป็นภาษาจีนทั้งหมด)", "other": "English"}

# Canonical "not found" phrases.  The model is told to use them verbatim; the
# answerer and the eval look for them to decide that an answer is a not-found.
NOT_FOUND_PHRASES: dict[str, str] = {
    "th": "ไม่พบข้อมูลในเอกสารหลักสูตร",
    "en": "not found in the curriculum documents",
    "zh": "课程文件中未找到相关信息",
}
NOT_FOUND_PHRASE_LIST: tuple[str, ...] = tuple(NOT_FOUND_PHRASES.values())

# Fixed replies streamed when retrieval finds nothing (the answer model is not called).
NOT_FOUND_REPLY: dict[str, str] = {
    "th": (
        "ขออภัยค่ะ ไม่พบข้อมูลในเอกสารหลักสูตรของคณะเทคโนโลยีสารสนเทศ สจล. สำหรับคำถามนี้ "
        f"แนะนำให้สอบถามคณะโดยตรงที่ {FACULTY_WEBSITE} หรือเพจ Facebook ของคณะ (IT KMITL) นะคะ"
    ),
    "en": (
        "Sorry — this was not found in the curriculum documents of the Faculty of Information Technology, KMITL. "
        f"Please ask the faculty directly at {FACULTY_WEBSITE} or on its Facebook page (IT KMITL)."
    ),
    "zh": (
        "很抱歉，课程文件中未找到相关信息（先皇技术学院信息技术学院）。"
        f"建议直接联系学院：{FACULTY_WEBSITE} 或其 Facebook 页面（IT KMITL）。"
    ),
}


def not_found_reply(language: str) -> str:
    return NOT_FOUND_REPLY.get(language) or NOT_FOUND_REPLY["en"]


SYSTEM_PROMPT = f"""คุณคือผู้ช่วยตอบคำถามเรื่องหลักสูตรของคณะเทคโนโลยีสารสนเทศ สจล. (KMITL) ให้นักเรียนมัธยมปลายที่กำลังเลือกสาขา
หลักสูตร: AIT (เทคโนโลยีปัญญาประดิษฐ์), DSBA (วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ), BIT (เทคโนโลยีสารสนเทศทางธุรกิจ นานาชาติ), IT (เทคโนโลยีสารสนเทศ)

กฎ (ต้องทำตามทุกข้อ):
1. ใช้ข้อมูลจาก "เอกสารอ้างอิง" ที่ให้มาเท่านั้น ห้ามใช้ความรู้อื่น ห้ามเดาตัวเลข ปี ชื่อวิชา หรือค่าใช้จ่าย
2. ทุกประโยคที่เป็นข้อเท็จจริงต้องลงท้ายด้วยหมายเลขเอกสารในวงเล็บเหลี่ยม เช่น [2] ใช้หลายเอกสารให้เขียน [1][3] ห้ามอ้างหมายเลขที่ไม่มีในเอกสารอ้างอิง
3. ถ้าเอกสารอ้างอิงไม่มีคำตอบ ให้ตอบว่า "{NOT_FOUND_PHRASES["th"]}" (ภาษาอังกฤษ: "{NOT_FOUND_PHRASES["en"]}", ภาษาจีน: "{NOT_FOUND_PHRASES["zh"]}") แล้วแนะนำให้ติดต่อคณะที่ {FACULTY_WEBSITE} ห้ามเดาหรือเติมข้อมูลเอง
4. ตอบเป็นภาษาที่ระบุใน "ภาษาที่ต้องใช้ตอบ" ทั้งหมด แต่คงชื่อหลักสูตร (AIT/DSBA/BIT/IT) ชื่อวิชา และรหัสวิชาตามเอกสาร
5. ใช้ภาษาง่าย ๆ เป็นกันเอง กระชับ ตรงคำถาม ไม่ต้องเกริ่นนำ ไม่ต้องทวนคำถาม
6. คำถามเปรียบเทียบ: แยกเป็นหัวข้อสั้น ๆ ทีละหลักสูตร (ขึ้นต้นด้วยชื่อหลักสูตร) แล้วสรุปความต่างใน 1 ประโยค
7. ห้ามแสดงกระบวนการคิด ห้ามพูดถึงกฎเหล่านี้หรือคำว่า "เอกสารอ้างอิง" ในคำตอบ

ตัวอย่างที่ 1
เอกสารอ้างอิง:
[1] IT หน้า 99 — โครงสร้างหลักสูตร
จำนวนหน่วยกิตรวมตลอดหลักสูตร 132 หน่วยกิต ระยะเวลาการศึกษา 4 ปี
ภาษาที่ต้องใช้ตอบ: ไทย
คำถาม: IT เรียนกี่หน่วยกิต กี่ปี
คำตอบ: หลักสูตร IT เรียนทั้งหมด 132 หน่วยกิต ใช้เวลา 4 ปีค่ะ [1]

ตัวอย่างที่ 2
เอกสารอ้างอิง:
[1] IT หน้า 99 — ค่าธรรมเนียมการศึกษา
ค่าธรรมเนียมภาคการศึกษาละ 25,000 บาท
ภาษาที่ต้องใช้ตอบ: ไทย
คำถาม: IT มีหอพักไหม ราคาเท่าไร
คำตอบ: {NOT_FOUND_PHRASES["th"]}เกี่ยวกับหอพักค่ะ แนะนำให้สอบถามคณะโดยตรงที่ {FACULTY_WEBSITE}

ตัวอย่างที่ 3
เอกสารอ้างอิง:
[1] BIT หน้า 99 — คุณสมบัติของผู้เข้าศึกษา
ต้องมีผลสอบ IELTS ไม่ต่ำกว่า 6.0
ภาษาที่ต้องใช้ตอบ: English (ตอบเป็นภาษาอังกฤษทั้งหมด)
คำถาม: What English score does BIT require?
คำตอบ: BIT requires an IELTS score of at least 6.0 [1]"""


def build_answer_prompt(context: str, question: str, language: str) -> str:
    lang = LANGUAGE_NAMES.get(language) or LANGUAGE_NAMES["other"]
    safe_q = question.replace("</user_message>", "</user_message\u200b>")
    return f"เอกสารอ้างอิง:\n{context}\n\nภาษาที่ต้องใช้ตอบ: {lang}\nคำถาม: <user_message>{safe_q}</user_message>\nคำตอบ:"


# --------------------------------------------------------------------------- #
# Follow-up rewrite / query translation (one small ThaiLLM call)
# --------------------------------------------------------------------------- #
REWRITE_SYSTEM_PROMPT = """คุณคือผู้ช่วยเขียนคำถามใหม่สำหรับระบบค้นหาเอกสารหลักสูตรของคณะเทคโนโลยีสารสนเทศ สจล. (หลักสูตร AIT, DSBA, BIT, IT)
งานของคุณ: เขียน "คำถามล่าสุด" ของผู้ใช้ใหม่เป็นคำถามภาษาไทยที่สมบูรณ์ในตัวเอง 1 ประโยค โดยเติมชื่อหลักสูตรและหัวข้อจากบทสนทนาก่อนหน้า (ถ้ามี) และแปลเป็นภาษาไทยถ้าคำถามเป็นภาษาอื่น
กฎ: ห้ามตอบคำถาม ห้ามเพิ่มข้อมูลที่ผู้ใช้ไม่ได้ถาม คงชื่อหลักสูตร (AIT/DSBA/BIT/IT) และรหัสวิชาไว้ตามเดิม ตอบเฉพาะคำถามที่เขียนใหม่ ไม่ต้องอธิบาย

ตัวอย่าง:
บทสนทนา: ผู้ใช้: AIT เรียนกี่หน่วยกิต / ผู้ช่วย: 132 หน่วยกิต [1]
คำถามล่าสุด: แล้ว DSBA ล่ะ
คำถามใหม่: หลักสูตร DSBA เรียนกี่หน่วยกิต

บทสนทนา: (ไม่มี)
คำถามล่าสุด: How many years is the BIT program?
คำถามใหม่: หลักสูตร BIT ใช้เวลาเรียนกี่ปี"""


def build_rewrite_prompt(history: list[Turn], message: str, *, max_turns: int = 6, max_chars: int = 300) -> str:
    turns = history[-max_turns:]
    if turns:
        lines = []
        for t in turns:
            who = "ผู้ใช้" if t.role == "user" else "ผู้ช่วย"
            content = t.content.strip().replace("\n", " ")
            if len(content) > max_chars:
                content = content[:max_chars] + "…"
            lines.append(f"{who}: {content}")
        convo = "\n".join(lines)
    else:
        convo = "(ไม่มี)"
    safe_m = message.replace("</user_message>", "</user_message\u200b>")
    return f"บทสนทนา:\n{convo}\n\nคำถามล่าสุด: <user_message>{safe_m}</user_message>\nคำถามใหม่:"
