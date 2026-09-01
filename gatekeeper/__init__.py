"""Gatekeeper: query classification + routing in front of the RAG pipeline.

Usage::

    from gatekeeper import gate, GateDecision
    decision = await gate("หลักสูตร AIT เรียนกี่หน่วยกิต", scope_filter=["IT"])
    if decision.category == "in_scope":
        ...  # hand off to RAG with decision.language / faculty / program / course_codes
    else:
        reply = decision.direct_reply
"""

from .config import DEFAULT_MODEL, FACULTIES, FACULTY_KEYS, MODELS, Settings, load_settings
from .gate import gate, gate_sync
from .schema import GateDecision

__all__ = [
    "DEFAULT_MODEL",
    "FACULTIES",
    "FACULTY_KEYS",
    "MODELS",
    "GateDecision",
    "Settings",
    "gate",
    "gate_sync",
    "load_settings",
]
