"""Gatekeeper: query classification + routing in front of the RAG pipeline.

Usage::

    from gatekeeper import gate, GateDecision, FACULTY
    decision = await gate("หลักสูตร AIT เรียนกี่หน่วยกิต", scope_filter=["AIT"])
    if decision.category == "in_scope":
        ...  # hand off to RAG with decision.language / decision.programs / decision.course_codes
    else:
        reply = decision.direct_reply
"""

from .config import DEFAULT_MODEL, MODELS, PROGRAM_IDS, PROGRAMS, Settings, load_settings
from .gate import gate, gate_sync
from .schema import CONTRACT_VERSION, FACULTY, GateDecision

__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_MODEL",
    "FACULTY",
    "MODELS",
    "PROGRAMS",
    "PROGRAM_IDS",
    "GateDecision",
    "Settings",
    "gate",
    "gate_sync",
    "load_settings",
]
