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


def test_foreign_university_reply_has_no_tcas_and_no_english_name_in_thai_or_chinese():
    from gatekeeper.replies import other_university_reply

    for lang in ("th", "en", "zh"):
        r = other_university_reply(lang, university_name=None, admissions_url=None, foreign=True)
        assert "mytcas" not in r and "the university" not in r, r
    assert "该大学" in other_university_reply("zh", university_name=None, admissions_url=None, foreign=True)
    assert "มหาวิทยาลัยดังกล่าว" in other_university_reply("th", university_name=None, admissions_url=None, foreign=True)
    # an unknown university with no URL still gets the TCAS portal (Thai default)
    assert "mytcas" in other_university_reply("en", university_name=None, admissions_url=None)
    # a Thai university keeps its admissions URL and the TCAS portal
    assert "mytcas" in other_university_reply("en", university_name="Mahidol University", admissions_url="https://tcas.mahidol.ac.th")


def test_thai_general_reply_has_a_space_before_the_particle():
    r = build_reply("off_topic_general", "th", topic="weather")
    assert ")นะคะ" not in r and " นะคะ" in r


def test_kmitl_out_of_scope_reply_labels_urls_correctly():
    th = build_reply("out_of_scope_kmitl", "th", topic="scholarship")
    assert "เว็บไซต์ของคณะ (https://www.reg" not in th
    assert th.count("https://www.it.kmitl.ac.th") == 1
    en = build_reply("out_of_scope_kmitl", "en", topic="dorm")
    assert "Dormitory Office" in en and "reg.kmitl.ac.th" not in en and "it.kmitl.ac.th" in en
    assert "reg.kmitl.ac.th" in build_reply("out_of_scope_kmitl", "en")  # default channel is the registrar


def test_other_faculty_reply_names_the_faculty_and_its_website():
    th = build_reply("out_of_scope_kmitl", "th", topic="faculty",
                     faculty_name="คณะบริหารธุรกิจ", faculty_url="https://www.kbs.kmitl.ac.th")
    assert "คณะบริหารธุรกิจ" in th and "https://www.kbs.kmitl.ac.th" in th
    assert "คณะนั้น" not in th
    assert "AIT" in th and "it.kmitl.ac.th" in th  # still says what the bot can do
    en = build_reply("out_of_scope_kmitl", "en", topic="faculty",
                     faculty_name="KMITL Business School", faculty_url="https://www.kbs.kmitl.ac.th")
    assert "KMITL Business School" in en and "https://www.kbs.kmitl.ac.th" in en
    zh = build_reply("out_of_scope_kmitl", "zh", topic="faculty",
                     faculty_name="工程学院", faculty_url=None)
    assert "工程学院" in zh and "https://www.kmitl.ac.th" in zh  # no known site -> central KMITL site
    # unknown faculty -> generic wording unchanged
    assert "คณะนั้น" in build_reply("out_of_scope_kmitl", "th", topic="faculty")


def test_unsafe_request_reply_is_a_safety_refusal_that_still_offers_help():
    th = build_reply("injection_or_abuse", "th", topic="unsafe")
    assert "คณะเทคโนโลยีสารสนเทศ" in th  # still offers curriculum help
    assert th != build_reply("injection_or_abuse", "th")  # distinct from the generic injection reply
    en = build_reply("injection_or_abuse", "en", topic="unsafe")
    assert "Information Technology" in en
    zh = build_reply("injection_or_abuse", "zh", topic="unsafe")
    assert len(zh) > 10
