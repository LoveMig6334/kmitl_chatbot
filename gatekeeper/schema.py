"""Interface contract between the gatekeeper and the RAG pipeline.

The RAG teammate imports ``GateDecision`` from here — keep it stable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "in_scope",
    "off_topic_general",
    "off_topic_other_university",
    "out_of_scope_kmitl",
    "injection_or_abuse",
]
Language = Literal["th", "en", "zh", "other"]
QuestionKind = Literal["fact_lookup", "descriptive", "comparison"]
DecidedBy = Literal["rule", "llm", "fallback"]

CATEGORIES: tuple[str, ...] = (
    "in_scope",
    "off_topic_general",
    "off_topic_other_university",
    "out_of_scope_kmitl",
    "injection_or_abuse",
)
LANGUAGES: tuple[str, ...] = ("th", "en", "zh", "other")
QUESTION_KINDS: tuple[str, ...] = ("fact_lookup", "descriptive", "comparison")


class GateDecision(BaseModel):
    category: Category
    language: Language
    faculty: str | None = None
    program: str | None = None
    course_codes: list[str] = Field(default_factory=list)
    question_kind: QuestionKind | None = None
    direct_reply: str | None = None  # filled ONLY when category != in_scope
    confidence: float = 0.0
    decided_by: DecidedBy
    model_used: str | None = None
    latency_ms: int = 0

    @property
    def forward_to_rag(self) -> bool:
        return self.category == "in_scope"
