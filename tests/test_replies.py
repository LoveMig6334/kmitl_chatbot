import pytest

from gatekeeper.replies import build_reply, injection_reply


@pytest.mark.parametrize("category", ["off_topic_general", "off_topic_other_university", "out_of_scope_kmitl", "injection_or_abuse"])
def test_reply_language_selection(category):
    th = build_reply(category, "th")
    en = build_reply(category, "en")
    zh = build_reply(category, "zh")
    other = build_reply(category, "other")
    assert th and any("฀" <= c <= "๿" for c in th)
    assert en and all(ord(c) < 0x2000 for c in en)
    assert zh and any("一" <= c <= "鿿" for c in zh)
    assert other == en  # unknown languages fall back to English


def test_in_scope_has_no_direct_reply():
    assert build_reply("in_scope", "th") is None


def test_replies_name_the_single_faculty_and_programs():
    for cat in ("off_topic_general", "off_topic_other_university", "out_of_scope_kmitl"):
        th = build_reply(cat, "th")
        assert "คณะเทคโนโลยีสารสนเทศ" in th and "AIT" in th and "DSBA" in th
        assert "Information Technology" in build_reply(cat, "en")
    assert "คณะนั้น" in build_reply("out_of_scope_kmitl", "th", topic="faculty")


def test_general_reply_suggests_channel():
    assert "อากาศ" in build_reply("off_topic_general", "th", topic="weather")
    assert "weather" in build_reply("off_topic_general", "en", topic="weather").lower()
    assert "Wongnai" in build_reply("off_topic_general", "th", topic="cooking")


def test_other_university_reply_points_to_admissions():
    r = build_reply("off_topic_other_university", "th", university_name="มหาวิทยาลัยมหิดล", admissions_url="https://tcas.mahidol.ac.th")
    assert "มหาวิทยาลัยมหิดล" in r and "tcas.mahidol.ac.th" in r and "mytcas.com" in r
    r_en = build_reply("off_topic_other_university", "en")
    assert "mytcas.com" in r_en


def test_kmitl_out_of_scope_points_to_official_channels():
    r = build_reply("out_of_scope_kmitl", "th", topic="dorm")
    assert "หอพัก" in r and "kmitl.ac.th" in r
    assert "reg.kmitl.ac.th" in build_reply("out_of_scope_kmitl", "en")


def test_injection_reply_is_short_and_reveals_nothing():
    for lang in ("th", "en", "zh"):
        r = injection_reply(lang)
        assert len(r) < 160
        assert "system prompt" not in r.lower()
        assert "<user_message>" not in r
        assert "ผู้คัดกรอง" not in r


def test_unknown_category_raises():
    with pytest.raises(ValueError):
        build_reply("weird", "th")  # type: ignore[arg-type]
