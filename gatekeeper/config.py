"""Configuration for the gatekeeper (scope definition, models, timeouts).

Scope: ONE faculty — คณะเทคโนโลยีสารสนเทศ สจล. — and its four B.Sc. programs.
The scope unit downstream is the *program* (AIT / DSBA / BIT / IT).

Environment overrides:
- ``GATEKEEPER_MODEL``        ThaiLLM model used for classification
- ``GATEKEEPER_TIMEOUT_S``    per-call timeout in seconds (float)
- ``GATEKEEPER_MAX_TOKENS``   max tokens for the classification reply
- ``GATEKEEPER_CACHE_DIR``    optional on-disk LLM response cache (eval only)
- ``THAILLM_API_KEY`` / ``THAILLM_BASE_URL``  shared with the rest of the project
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:  # reuse the project's model registry when the package is installed
    from thai_llm_kmitl.models import DEFAULT_MODEL as _PROJECT_DEFAULT_MODEL
    from thai_llm_kmitl.models import MODELS as _PROJECT_MODELS
except ImportError:  # pragma: no cover - fallback when src/ is not importable
    _PROJECT_DEFAULT_MODEL = "openthaigpt-thaillm-8b-instruct-v7.2"
    _PROJECT_MODELS = [
        "openthaigpt-thaillm-8b-instruct-v7.2",
        "pathumma-thaillm-qwen3-8b-think-3.0.0",
        "typhoon-s-thaillm-8b-instruct",
        "thalle-0.2-thaillm-8b-fa",
    ]

DEFAULT_MODEL: str = _PROJECT_DEFAULT_MODEL
MODELS: list[str] = list(_PROJECT_MODELS)
DEFAULT_BASE_URL = "http://thaillm.or.th/api/v1"
USER_AGENT = "thai-llm-kmitl/0.1"

# --------------------------------------------------------------------------- #
# The single in-scope faculty
# --------------------------------------------------------------------------- #
FACULTY_KEY = "IT"
FACULTY_NAME_TH = "คณะเทคโนโลยีสารสนเทศ"
FACULTY_NAME_EN = "Faculty of Information Technology"
FACULTY_NAME_ZH = "信息技术学院"
FACULTY_WEBSITE = "https://www.it.kmitl.ac.th"
# lower-cased substrings / words that mean "the IT faculty" (any language)
FACULTY_ALIASES: tuple[str, ...] = (
    "เทคโนโลยีสารสนเทศ",
    "คณะไอที",
    "คณะ it",
    "faculty of information technology",
    "school of information technology",
    "information technology",
    "信息技术学院",
    "资讯科技学院",
    "信息技术",
)

# BIT aliases that mean "the international program": when one of these is present
# a bare/weak "IT" always refers to BIT, never to the IT program.
INTER_ALIASES: tuple[str, ...] = ("it inter", "ไอทีอินเตอร์", "อินเตอร์", "นานาชาติ", "international", "国际", "inter")

# Words that, near a bare "IT"/"ไอที"/"AI", signal a program-level reference.
PROGRAM_CONTEXT_WORDS: tuple[str, ...] = (
    "สาขา", "หลักสูตร", "ปกติ", "2565", "2566", "program", "programme", "major",
    "curriculum", "degree", "专业", "课程",
)


@dataclass(frozen=True)
class Program:
    """One in-scope B.Sc. program and the aliases used to recognise it."""

    id: str
    name_th: str
    name_en: str
    version_th: str
    aliases: tuple[str, ...]  # lower-cased; ASCII ones matched as whole words
    exact_aliases: tuple[str, ...] = ()  # case-sensitive whole words (e.g. "BIT")
    weak_aliases: tuple[str, ...] = ()  # only count when PROGRAM_CONTEXT_WORDS are nearby


PROGRAMS: tuple[Program, ...] = (
    Program(
        id="AIT",
        name_th="สาขาวิชาเทคโนโลยีปัญญาประดิษฐ์",
        name_en="Artificial Intelligence Technology",
        version_th="หลักสูตรใหม่ พ.ศ. 2566",
        aliases=(
            "ait", "เอไอที", "ปัญญาประดิษฐ์", "สาขา ai", "หลักสูตร ai",
            "artificial intelligence technology", "artificial intelligence", "人工智能技术", "人工智能",
        ),
        weak_aliases=("ai",),
    ),
    Program(
        id="DSBA",
        name_th="สาขาวิชาวิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ",
        name_en="Data Science and Business Analytics",
        version_th="หลักสูตรปรับปรุง พ.ศ. 2565",
        aliases=(
            "dsba", "ดาต้า", "data science", "data sci", "วิทยาการข้อมูล",
            "data science and business analytics", "business analytics", "数据科学",
        ),
        exact_aliases=("DS",),
        weak_aliases=("ds",),
    ),
    Program(
        id="BIT",
        name_th="สาขาวิชาเทคโนโลยีสารสนเทศทางธุรกิจ (หลักสูตรนานาชาติ)",
        name_en="Business Information Technology (International Program)",
        version_th="หลักสูตรปรับปรุง พ.ศ. 2565",
        aliases=(
            "it inter", "ไอทีอินเตอร์", "อินเตอร์", "นานาชาติ", "international",
            "business information technology", "เทคโนโลยีสารสนเทศทางธุรกิจ", "商业信息技术", "国际",
        ),
        exact_aliases=("BIT",),
    ),
    Program(
        id="IT",
        name_th="สาขาวิชาเทคโนโลยีสารสนเทศ",
        name_en="Information Technology",
        version_th="หลักสูตรปรับปรุง พ.ศ. 2565",
        aliases=(
            "สาขาไอที", "สาขา it", "สาขาวิชาเทคโนโลยีสารสนเทศ", "สาขาเทคโนโลยีสารสนเทศ",
            "it ปกติ", "ไอทีปกติ", "ไอที ปกติ", "ภาคปกติ", "หลักสูตร it", "หลักสูตรไอที",
            "it program", "information technology program", "信息技术专业",
        ),
        weak_aliases=("it", "ไอที"),
    ),
)
PROGRAM_IDS: tuple[str, ...] = tuple(p.id for p in PROGRAMS)


def program_by_id(pid: str | None) -> Program | None:
    if pid is None:
        return None
    k = pid.strip().upper()
    for p in PROGRAMS:
        if p.id == k:
            return p
    return None


# Other KMITL faculties/colleges: questions about them are ``out_of_scope_kmitl``.
# (Regex fragments, case-insensitive.)  "วิศวกรรมซอฟต์แวร์" is deliberately NOT
# matched — it is a course name inside the IT curriculum.
OTHER_KMITL_FACULTY_PATTERNS: tuple[str, ...] = (
    r"คณะวิศว|วิศวะ|วิศวกรรมศาสตร์|วิศวกรรม(ไฟฟ้า|เครื่องกล|โยธา|คอมพิวเตอร์|เคมี|อุตสาหการ|โทรคมนาคม|เกษตร|อิเล็กทรอนิกส์|ระบบควบคุม|การวัด|ชีวการแพทย์|ยานยนต์|หุ่นยนต์)"
    r"|faculty of engineering|school of engineering|engineering faculty|工程学院",
    r"สถาปัตย|architecture|建筑学院",
    r"คณะวิทยาศาสตร์|คณะวิทย์|faculty of science|school of science|理学院",
    r"บริหารธุรกิจ|คณะบริหาร|\bkbs\b|business school|business administration|商学院",
    r"ครุศาสตร์อุตสาหกรรม|industrial education",
    r"อุตสาหกรรมอาหาร|food industry",
    r"เทคโนโลยีการเกษตร|agricultural technology|agro-industry",
    r"ศิลปศาสตร์|liberal arts",
    r"คณะแพทย|แพทยศาสตร์|faculty of medicine|medical school|医学院",
    r"ทันตแพทย|dentistry",
    r"นวัตกรรมการผลิต|วิทยาลัยนาโน|nanotechnology|อุตสาหกรรมการบิน|aviation|วิทยาเขตชุมพร|วิทยาลัยวิศวกรรมสังคีต|music engineering",
)


@dataclass(frozen=True)
class Settings:
    model: str = DEFAULT_MODEL
    timeout_s: float = 8.0
    max_tokens: int = 512
    temperature: float = 0.0
    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = None
    max_attempts: int = 2  # first try + one retry
    cache_dir: str | None = None  # on-disk response cache (eval harness only)


def load_settings(**overrides: object) -> Settings:
    """Build settings from the environment (``.env`` is loaded if present)."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # pragma: no cover
        pass

    values: dict[str, object] = {
        "model": os.environ.get("GATEKEEPER_MODEL", DEFAULT_MODEL),
        "timeout_s": float(os.environ.get("GATEKEEPER_TIMEOUT_S", "8")),
        "max_tokens": int(os.environ.get("GATEKEEPER_MAX_TOKENS", "512")),
        "temperature": float(os.environ.get("GATEKEEPER_TEMPERATURE", "0")),
        "base_url": os.environ.get("THAILLM_BASE_URL", DEFAULT_BASE_URL),
        "api_key": os.environ.get("THAILLM_API_KEY"),
        "cache_dir": os.environ.get("GATEKEEPER_CACHE_DIR") or None,
    }
    values.update({k: v for k, v in overrides.items() if v is not None})
    return Settings(**values)  # type: ignore[arg-type]
