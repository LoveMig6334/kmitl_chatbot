"""Interface contract between the gatekeeper and the RAG pipeline.

The RAG teammate imports ``GateDecision`` from here — keep it stable.

CONTRACT_VERSION 2 (2026-09-01): the scope is a single faculty (``FACULTY``),
so the ``faculty`` and ``program`` fields were replaced by ``programs`` — the
list of in-scope program ids the question names (empty = none named, RAG
should search all programs; two or more = a comparison).

2026-09-02 (additive, still v2): ``category`` gained ``greeting_smalltalk`` —
greetings / thanks / acknowledgements / farewells / bot-identity questions and
vague help openers that carry no answerable content.  Like every non-in_scope
category it comes with a ``direct_reply`` (a warm welcome, never a refusal), so
consumers that only branch on ``in_scope`` need no change.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CONTRACT_VERSION = 2
FACULTY = "IT"  # the only faculty in scope: คณะเทคโนโลยีสารสนเทศ สจล.

Category = Literal[
    "in_scope",
    "off_topic_general",
    "off_topic_other_university",
    "out_of_scope_kmitl",
    "injection_or_abuse",
    "greeting_smalltalk",
]
Language = Literal["th", "en", "zh", "other"]
QuestionKind = Literal["fact_lookup", "descriptive", "comparison"]
DecidedBy = Literal["rule", "llm", "fallback"]
ProgramId = Literal["AIT", "DSBA", "BIT", "IT"]

CATEGORIES: tuple[str, ...] = (
    "in_scope",
    "off_topic_general",
    "off_topic_other_university",
    "out_of_scope_kmitl",
    "injection_or_abuse",
    "greeting_smalltalk",
)
LANGUAGES: tuple[str, ...] = ("th", "en", "zh", "other")
QUESTION_KINDS: tuple[str, ...] = ("fact_lookup", "descriptive", "comparison")


class GateDecision(BaseModel):
    category: Category
    language: Language
    programs: list[ProgramId] = Field(default_factory=list)  # [] = none named
    course_codes: list[str] = Field(default_factory=list)
    question_kind: QuestionKind | None = None
    direct_reply: str | None = None  # filled ONLY when category != in_scope
    confidence: float = 0.0
    decided_by: DecidedBy
    model_used: str | None = None
    latency_ms: int = 0

    @property
    def faculty(self) -> str:
        return FACULTY

    @property
    def program(self) -> str | None:
        """Convenience: the single named program, or None if zero or several."""
        return self.programs[0] if len(self.programs) == 1 else None

    @property
    def forward_to_rag(self) -> bool:
        return self.category == "in_scope"
