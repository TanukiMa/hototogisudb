from mozc4med_dict.utils.kana import normalize_reading


def test_normalize_reading_katakana_to_hiragana():
    assert normalize_reading("トウニョウビョウ") == "とうにょうびょう"


def test_normalize_reading_already_hiragana():
    assert normalize_reading("とうにょうびょう") == "とうにょうびょう"


def test_normalize_reading_strips_whitespace():
    assert normalize_reading("　アスピリン　") == "あすぴりん"


def test_normalize_reading_empty():
    import pytest
    with pytest.raises(ValueError):
        normalize_reading("")


def test_normalize_reading_mixed():
    assert normalize_reading("インスリンチュウシャ") == "いんすりんちゅうしゃ"


def test_normalize_reading_non_kana_raises():
    import pytest
    with pytest.raises(ValueError):
        normalize_reading("糖尿病")


def test_normalize_reading_halfwidth_katakana():
    # 半角カナ → ひらがな
    assert normalize_reading("ｼﾝﾘｮｳｺｳｲ") == "しんりょうこうい"


def test_normalize_reading_halfwidth_dakuten():
    # 半角カナ濁点結合
    assert normalize_reading("ｼﾞｬｸﾋﾝ") == "じゃくひん"


def test_normalize_reading_halfwidth_handakuten():
    # 半角カナ半濁点結合
    assert normalize_reading("ﾊﾟｰｷﾝｿﾝﾋﾞｮｳ") == "ぱーきんそんびょう"


def test_normalize_reading_halfwidth_digits():
    # 半角数字はそのまま通す
    assert normalize_reading("ｲﾝｽﾘﾝ10ｴ") == "いんすりん10え"


def test_normalize_reading_fullwidth_digits_raises():
    import pytest

    with pytest.raises(ValueError):
        normalize_reading("ｲﾝｽﾘﾝ１０ｴ")
