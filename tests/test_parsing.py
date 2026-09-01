from gatekeeper.parsing import (
    extract_json_object,
    normalize_category,
    normalize_faculty,
    normalize_language,
    normalize_question_kind,
    parse_verdict,
    strip_think,
)

PLAIN = '{"category": "in_scope", "language": "th", "faculty": "IT", "program": "AIT", "question_kind": "fact_lookup"}'


def test_plain_json():
    v = parse_verdict(PLAIN)
    assert v is not None
    assert (v.category, v.language, v.faculty, v.program, v.question_kind) == (
        "in_scope", "th", "IT", "AIT", "fact_lookup")


def test_fenced_json_with_think_block():
    raw = "<think>\nคำถามนี้ถามเรื่องอากาศ\n</think>\n\n```json\n" + PLAIN.replace("in_scope", "off_topic_general") + "\n```"
    v = parse_verdict(raw)
    assert v is not None and v.category == "off_topic_general"


def test_strip_think_removes_block():
    assert strip_think("<think>abc</think> {\"a\": 1}") == '{"a": 1}'


def test_truncated_json_is_repaired():
    raw = '<think>...</think>\n```json\n{\n  "category": "in_scope",\n  "language": "th",\n  "faculty": null,\n  "program":'
    v = parse_verdict(raw)
    assert v is not None
    assert v.category == "in_scope" and v.language == "th" and v.program is None


def test_truncated_inside_string():
    raw = '{"category": "off_topic_other_university", "language": "th", "university": "มหาวิทยาลัยมหิ'
    v = parse_verdict(raw)
    assert v is not None and v.category == "off_topic_other_university"


def test_garbage_returns_none():
    assert parse_verdict("") is None
    assert parse_verdict("ขออภัย ฉันไม่สามารถจำแนกได้") is None
    assert parse_verdict('{"category": "banana"}') is None
    assert extract_json_object("no json here") is None


def test_json_embedded_in_prose():
    raw = 'Sure! Here is the answer: {"category": "injection_or_abuse", "language": "en"} hope this helps'
    v = parse_verdict(raw)
    assert v is not None and v.category == "injection_or_abuse"


def test_category_aliases():
    assert normalize_category("In Scope") == "in_scope"
    assert normalize_category("prompt_injection") == "injection_or_abuse"
    assert normalize_category("other_university") == "off_topic_other_university"
    assert normalize_category("nonsense") is None


def test_language_aliases():
    assert normalize_language("Thai") == "th"
    assert normalize_language("zh-CN") == "zh"
    assert normalize_language("English") == "en"
    assert normalize_language("fr") is None


def test_faculty_normalisation_any_language():
    assert normalize_faculty("信息技术学院") == "IT"
    assert normalize_faculty("คณะเทคโนโลยีสารสนเทศ") == "IT"
    assert normalize_faculty("School of Engineering") == "ENG"
    assert normalize_faculty("it") == "IT"
    assert normalize_faculty("Faculty of Medicine") is None
    assert normalize_faculty(None) is None


def test_question_kind_aliases():
    assert normalize_question_kind("fact") == "fact_lookup"
    assert normalize_question_kind("compare") == "comparison"
    assert normalize_question_kind("学分要求") is None


def test_confidence_normalised():
    v = parse_verdict('{"category": "in_scope", "confidence": 95}')
    assert v is not None and v.confidence == 0.95
