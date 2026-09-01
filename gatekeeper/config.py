"""Configuration for the gatekeeper (models, timeouts, in-scope faculties).

Everything is overridable through environment variables so the module can be
tuned without code changes:

- ``GATEKEEPER_MODEL``        ThaiLLM model used for classification
- ``GATEKEEPER_TIMEOUT_S``    per-call timeout in seconds (float)
- ``GATEKEEPER_MAX_TOKENS``   max tokens for the classification reply
- ``THAILLM_API_KEY`` / ``THAILLM_BASE_URL``  shared with the rest of the project
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

try:  # reuse the project's model registry when the package is installed
    from thai_llm_kmitl.models import DEFAULT_MODEL as _PROJECT_DEFAULT_MODEL
    from thai_llm_kmitl.models import MODELS as _PROJECT_MODELS
except Exception:  # pragma: no cover - fallback when src/ is not importable
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


@dataclass(frozen=True)
class Faculty:
    """One in-scope faculty with the aliases used to recognise it."""

    key: str  # canonical id used in GateDecision.faculty
    name_th: str
    name_en: str
    name_zh: str
    aliases: tuple[str, ...]  # lower-cased substrings (Thai/English/Chinese)
    programs: dict[str, tuple[str, ...]] = field(default_factory=dict)  # code -> aliases
    website: str = "https://www.kmitl.ac.th"


# NOTE: the spec left the four faculties as placeholders; the IT faculty is
# certain (it appears in the eval set), the other three are reasonable defaults
# and are trivially editable here.
FACULTIES: tuple[Faculty, ...] = (
    Faculty(
        key="IT",
        name_th="คณะเทคโนโลยีสารสนเทศ",
        name_en="School of Information Technology",
        name_zh="信息技术学院",
        aliases=(
            "เทคโนโลยีสารสนเทศ",
            "คณะไอที",
            "คณะ it",
            "school of information technology",
            "faculty of information technology",
            "information technology",
            "信息技术学院",
            "资讯科技学院",
            "信息技术",
        ),
        programs={
            "AIT": (
                "ait",
                "เทคโนโลยีปัญญาประดิษฐ์",
                "ปัญญาประดิษฐ์",
                "artificial intelligence technology",
                "人工智能技术",
                "人工智能",
            ),
            "DSBA": (
                "dsba",
                "วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ",
                "วิทยาการข้อมูล",
                "data science and business analytics",
                "data science",
                "数据科学",
            ),
            "BIT": (
                "bit",
                "business information technology",
                "เทคโนโลยีสารสนเทศทางธุรกิจ",
                "商业信息技术",
            ),
            "IT": (
                "สาขาวิชาเทคโนโลยีสารสนเทศ",
                "สาขาเทคโนโลยีสารสนเทศ",
                "สาขา it",
                "สาขาไอที",
                "it program",
                "information technology program",
                "信息技术专业",
            ),
        },
        website="https://www.it.kmitl.ac.th",
    ),
    Faculty(
        key="ENG",
        name_th="คณะวิศวกรรมศาสตร์",
        name_en="School of Engineering",
        name_zh="工程学院",
        aliases=(
            "วิศวกรรมศาสตร์",
            "คณะวิศวะ",
            "วิศวะ",
            "วิศวกรรม",
            "school of engineering",
            "faculty of engineering",
            "engineering",
            "工程学院",
            "工程",
        ),
        programs={
            "CE": ("วิศวกรรมคอมพิวเตอร์", "computer engineering", "计算机工程"),
            "EE": ("วิศวกรรมไฟฟ้า", "electrical engineering", "电气工程"),
            "ME": ("วิศวกรรมเครื่องกล", "mechanical engineering", "机械工程"),
            "CIE": ("วิศวกรรมโยธา", "civil engineering", "土木工程"),
            "ROBOTICS": ("วิศวกรรมหุ่นยนต์", "robotics", "机器人"),
        },
        website="https://engineer.kmitl.ac.th",
    ),
    Faculty(
        key="SCI",
        name_th="คณะวิทยาศาสตร์",
        name_en="School of Science",
        name_zh="理学院",
        aliases=(
            "คณะวิทยาศาสตร์",
            "คณะวิทย์",
            "school of science",
            "faculty of science",
            "理学院",
        ),
        programs={
            "CS": ("วิทยาการคอมพิวเตอร์", "computer science", "计算机科学"),
            "MATH": ("คณิตศาสตร์ประยุกต์", "applied mathematics", "应用数学"),
            "CHEM": ("เคมี", "chemistry", "化学"),
            "PHYS": ("ฟิสิกส์", "physics", "物理"),
        },
        website="https://www.science.kmitl.ac.th",
    ),
    Faculty(
        key="BUS",
        name_th="คณะบริหารธุรกิจ",
        name_en="KMITL Business School",
        name_zh="商学院",
        aliases=(
            "บริหารธุรกิจ",
            "คณะบริหาร",
            "business school",
            "business administration",
            "kbs",
            "商学院",
            "工商管理",
        ),
        programs={
            "BBA": ("bba", "บริหารธุรกิจบัณฑิต", "bachelor of business administration"),
            "ENTREPRENEUR": ("ผู้ประกอบการ", "entrepreneurship", "创业"),
        },
        website="https://kbs.kmitl.ac.th",
    ),
)

FACULTY_KEYS: tuple[str, ...] = tuple(f.key for f in FACULTIES)


def faculty_by_key(key: str | None) -> Faculty | None:
    if key is None:
        return None
    k = key.strip().upper()
    for f in FACULTIES:
        if f.key == k:
            return f
    return None


@dataclass(frozen=True)
class Settings:
    model: str = DEFAULT_MODEL
    timeout_s: float = 8.0
    max_tokens: int = 512
    temperature: float = 0.0
    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = None
    max_attempts: int = 2  # first try + one retry


def load_settings(**overrides: object) -> Settings:
    """Build settings from the environment (``.env`` is loaded if present)."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:  # pragma: no cover
        pass

    values: dict[str, object] = {
        "model": os.environ.get("GATEKEEPER_MODEL", DEFAULT_MODEL),
        "timeout_s": float(os.environ.get("GATEKEEPER_TIMEOUT_S", "8")),
        "max_tokens": int(os.environ.get("GATEKEEPER_MAX_TOKENS", "512")),
        "temperature": float(os.environ.get("GATEKEEPER_TEMPERATURE", "0")),
        "base_url": os.environ.get("THAILLM_BASE_URL", DEFAULT_BASE_URL),
        "api_key": os.environ.get("THAILLM_API_KEY"),
    }
    values.update({k: v for k, v in overrides.items() if v is not None})
    return Settings(**values)  # type: ignore[arg-type]
