"""Public entry point: ``gate(message, scope_filter) -> GateDecision``.

Routing, cheapest first:
1. deterministic rules (0 API calls) — only when near-certain
2. one ThaiLLM classification call (retry once on timeout / bad JSON)
3. fallback to ``in_scope`` with empty metadata
"""

from __future__ import annotations

import asyncio
import logging
import time

from . import llm as _llm
from .config import Settings, load_settings
from .language import detect_language
from .parsing import LLMVerdict, parse_verdict
from .replies import build_reply
from .rules import OTHER_UNIVERSITIES, Metadata, apply_rules, find_other_universities
from .schema import Category, GateDecision, Language

log = logging.getLogger(__name__)


def _university_info(text: str, verdict_name: str | None) -> tuple[str | None, str | None]:
    thai = detect_language(text) == "th"
    found = find_other_universities(text)
    if found:
        return (found[0].name_th if thai else found[0].name_en), found[0].admissions_url
    if verdict_name:
        lowered = verdict_name.lower()
        for u in OTHER_UNIVERSITIES:
            if u.pattern.search(lowered):
                return (u.name_th if thai else u.name_en), u.admissions_url
        return verdict_name, None
    return None, None


def _build_decision(
    *,
    category: Category,
    language: Language,
    meta: Metadata,
    confidence: float,
    decided_by: str,
    model_used: str | None,
    started: float,
    university_name: str | None = None,
    admissions_url: str | None = None,
    topic: str | None = None,
    llm_programs: list[str] | None = None,
    llm_kind: str | None = None,
) -> GateDecision:
    in_scope = category == "in_scope"
    programs = meta.programs or list(llm_programs or [])
    if len(programs) > 1:
        kind: str | None = "comparison"
    else:
        kind = llm_kind or meta.question_kind
    return GateDecision(
        category=category,
        language=language,
        programs=programs if in_scope else [],  # type: ignore[arg-type]
        course_codes=meta.course_codes if in_scope else [],
        question_kind=kind if in_scope else None,  # type: ignore[arg-type]
        direct_reply=build_reply(
            category, language, university_name=university_name, admissions_url=admissions_url, topic=topic
        ),
        confidence=round(confidence, 3),
        decided_by=decided_by,  # type: ignore[arg-type]
        model_used=model_used,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


async def _classify_with_retry(message: str, settings: Settings) -> tuple[LLMVerdict | None, str | None, list[str]]:
    """Call the LLM up to ``settings.max_attempts`` times; return (verdict, model, raw_outputs)."""
    raws: list[str] = []
    model: str | None = None
    for attempt in range(1, settings.max_attempts + 1):
        try:
            resp = await _llm.call_classifier(message, settings)
        except TimeoutError as exc:
            log.warning("gatekeeper llm timeout (attempt %d): %s", attempt, exc)
            raws.append(f"<timeout: {exc!r}>")
            continue
        except Exception as exc:  # noqa: BLE001 - any network/API failure must fall through to the fallback
            log.warning("gatekeeper llm error (attempt %d): %s", attempt, exc)
            raws.append(f"<error: {exc!r}>")
            continue
        model = resp.model
        raws.append(resp.text)
        verdict = parse_verdict(resp.text)
        if verdict is not None:
            return verdict, model, raws
        log.warning("gatekeeper llm returned unparsable JSON (attempt %d)", attempt)
    return None, model, raws


async def gate(
    message: str,
    scope_filter: list[str] | None = None,
    *,
    settings: Settings | None = None,
    use_llm: bool = True,
    use_rules: bool = True,
    debug: dict | None = None,
) -> GateDecision:
    """Classify ``message`` and decide whether RAG should handle it.

    ``scope_filter`` = program ids ticked in the UI; narrows program resolution
    and never causes a refusal.
    ``use_llm=False`` runs the rule layer only (``--dry-run`` evals);
    ``use_rules=False`` skips rule *decisions* so every message hits the LLM
    (``--no-rules`` evals — the system's floor).  Metadata extraction always runs.
    ``debug`` (optional dict) receives ``rule_reason`` and ``raw_outputs`` for eval tooling.
    """
    started = time.perf_counter()
    text = message or ""
    language = detect_language(text)
    rule = apply_rules(text, scope_filter)
    meta = rule.metadata
    if debug is not None:
        debug["rule_reason"] = rule.reason
        debug["raw_outputs"] = []

    if use_rules and rule.category is not None:
        uni_name, uni_url = (None, None)
        if rule.university is not None:
            uni_name = rule.university.name_th if language == "th" else rule.university.name_en
            uni_url = rule.university.admissions_url
        return _build_decision(
            category=rule.category, language=language, meta=meta, confidence=rule.confidence,
            decided_by="rule", model_used=None, started=started, university_name=uni_name,
            admissions_url=uni_url, topic=rule.topic,
        )

    settings = settings or load_settings()
    verdict: LLMVerdict | None = None
    model_used: str | None = None
    if use_llm:
        verdict, model_used, raws = await _classify_with_retry(text, settings)
        if debug is not None:
            debug["raw_outputs"] = raws

    if verdict is None:
        # Fallback: better to attempt an answer than to wrongly refuse.
        return _build_decision(
            category="in_scope", language=language, meta=Metadata(course_codes=meta.course_codes),
            confidence=0.0, decided_by="fallback", model_used=model_used, started=started,
        )

    category: Category = verdict.category  # type: ignore[assignment]
    # The deterministic detector is more reliable than the model for language.
    if language == "other" and verdict.language in ("th", "en", "zh"):
        language = verdict.language  # type: ignore[assignment]
    uni_name, uni_url = (None, None)
    if category == "off_topic_other_university":
        uni_name, uni_url = _university_info(text, verdict.university)
    topic = rule.topic or verdict.topic
    return _build_decision(
        category=category, language=language, meta=meta,
        confidence=verdict.confidence if verdict.confidence is not None else 0.7,
        decided_by="llm", model_used=model_used, started=started, university_name=uni_name,
        admissions_url=uni_url, topic=topic, llm_programs=verdict.programs, llm_kind=verdict.question_kind,
    )


def gate_sync(message: str, scope_filter: list[str] | None = None, **kwargs) -> GateDecision:
    """Blocking convenience wrapper around :func:`gate`."""
    return asyncio.run(gate(message, scope_filter, **kwargs))
