import jaconv

try:
    import alphabet2kana  # added for ASCII‑letter conversion
except ImportError:  # pragma: no cover
    alphabet2kana = None  # type: ignore


def normalize_reading(text: str) -> str:
    """SSK から取得した kana カラムを Mozc 用に正規化する。

    変換フロー（仕様書 CLAUDE.md に記載）:
    1. 半角カナ → 全角カタナ → 平仮名
    2. ASCII 英字 → カタカナ → 平仮名
    3. 半角数字は **そのまま**（半角数字のまま通す）
    4. 許容文字はひらがな、半角数字、長音符「ー」、中点「・」

    Args:
        text: SSK CSV から読み込んだ生文字列

    Returns:
        正規化された文字列（ひらがな + 半角数字）
    """
    # 前後空白・全角スペース除去
    text = text.strip().replace("\u3000", "")
    if not text:
        raise ValueError("empty reading")

    # ① 半角カナ → 全角カタナ（数字はそのまま） → 平仮名
    text = jaconv.h2z(text, kana=True, digit=False, ascii=False)
    # ② ASCII 英字 → カタカナ → 平仮名（alphabet2kana が利用できない場合はスキップ）
    if alphabet2kana is not None:
        text = alphabet2kana.alphabet2kana(text)
    # ③ カタカナ → 平仮名
    text = jaconv.kata2hira(text)

    # 許容文字チェック（ひらがな、半角数字、全角数字、長音符・中点）
    for ch in text:
        code = ord(ch)
        if 0x3041 <= code <= 0x3096:  # ひらがな
            continue
        if 0x30 <= code <= 0x39:       # 半角数字 0‑9
            continue
        if 0xFF10 <= code <= 0xFF19:   # 全角数字（互換性のため残す）
            continue
        if ch in ("ー", "・"):
            continue
        raise ValueError(f"非カナ文字が含まれています: {ch!r}")
    return text
