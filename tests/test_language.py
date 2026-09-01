from gatekeeper.language import detect_language


def test_thai():
    assert detect_language("หลักสูตร AIT เรียนกี่หน่วยกิต") == "th"


def test_english():
    assert detect_language("How many credits does the AIT program require?") == "en"


def test_chinese():
    assert detect_language("KMITL信息技术学院的人工智能技术专业(AIT)总共需要修满多少学分?") == "zh"


def test_thai_with_english_code_is_thai():
    assert detect_language("วิชา 06016317 Data Structures กี่หน่วยกิต") == "th"


def test_mixed_thai_english_prefers_thai():
    assert detect_language("AIT program ของ KMITL ต้องเรียนกี่ years") == "th"


def test_other_scripts():
    assert detect_language("これは日本語の質問です") == "other"
    assert detect_language("이것은 한국어 질문입니다") == "other"
    assert detect_language("Это вопрос на русском языке") == "other"


def test_empty_or_symbols():
    assert detect_language("") == "other"
    assert detect_language("12345 ???") == "other"
