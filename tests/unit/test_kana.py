from mozc4med_dict.utils.kana import normalize_reading


def test_normalize_reading_katakana_to_hiragana():
    assert normalize_reading("トウニョウビョウ") == "とうにょうびょう"


def test_normalize_reading_already_hiragana():
    assert normalize_reading("とうにょうびょう") == "とうにょうびょう"


def test_normalize_reading_strips_whitespace():
    assert normalize_reading("　アスピリン　") == "あすぴりん"


def test_normalize_reading_empty():
    assert normalize_reading("") == ""


def test_normalize_reading_mixed():
    assert normalize_reading("インスリンチュウシャ") == "いんすりんちゅうしゃ"


def test_normalize_reading_non_kana_raises():
    import pytest
    with pytest.raises(ValueError):
        normalize_reading("糖尿病")
