# 半角カナ → 全角カタカナ変換テーブル
# 結合濁点・半濁点（U+FF9E, U+FF9F）を考慮した対応表
_HALFWIDTH_DAKUTEN: dict[str, str] = {
    "ｶ": "ガ", "ｷ": "ギ", "ｸ": "グ", "ｹ": "ゲ", "ｺ": "ゴ",
    "ｻ": "ザ", "ｼ": "ジ", "ｽ": "ズ", "ｾ": "ゼ", "ｿ": "ゾ",
    "ﾀ": "ダ", "ﾁ": "ヂ", "ﾂ": "ヅ", "ﾃ": "デ", "ﾄ": "ド",
    "ﾊ": "バ", "ﾋ": "ビ", "ﾌ": "ブ", "ﾍ": "ベ", "ﾎ": "ボ",
    "ｳ": "ヴ",
}
_HALFWIDTH_HANDAKUTEN: dict[str, str] = {
    "ﾊ": "パ", "ﾋ": "ピ", "ﾌ": "プ", "ﾍ": "ペ", "ﾎ": "ポ",
}
_HALFWIDTH_TO_FULLWIDTH: dict[str, str] = {
    "ｦ": "ヲ", "ｧ": "ァ", "ｨ": "ィ", "ｩ": "ゥ", "ｪ": "ェ", "ｫ": "ォ",
    "ｬ": "ャ", "ｭ": "ュ", "ｮ": "ョ", "ｯ": "ッ", "ｰ": "ー",
    "ｱ": "ア", "ｲ": "イ", "ｳ": "ウ", "ｴ": "エ", "ｵ": "オ",
    "ｶ": "カ", "ｷ": "キ", "ｸ": "ク", "ｹ": "ケ", "ｺ": "コ",
    "ｻ": "サ", "ｼ": "シ", "ｽ": "ス", "ｾ": "セ", "ｿ": "ソ",
    "ﾀ": "タ", "ﾁ": "チ", "ﾂ": "ツ", "ﾃ": "テ", "ﾄ": "ト",
    "ﾅ": "ナ", "ﾆ": "ニ", "ﾇ": "ヌ", "ﾈ": "ネ", "ﾉ": "ノ",
    "ﾊ": "ハ", "ﾋ": "ヒ", "ﾌ": "フ", "ﾍ": "ヘ", "ﾎ": "ホ",
    "ﾏ": "マ", "ﾐ": "ミ", "ﾑ": "ム", "ﾒ": "メ", "ﾓ": "モ",
    "ﾔ": "ヤ", "ﾕ": "ユ", "ﾖ": "ヨ",
    "ﾗ": "ラ", "ﾘ": "リ", "ﾙ": "ル", "ﾚ": "レ", "ﾛ": "ロ",
    "ﾜ": "ワ", "ﾝ": "ン", "ﾞ": "", "ﾟ": "",  # 単独濁点・半濁点は除去
}


def _halfwidth_to_fullwidth_katakana(text: str) -> str:
    """半角カナを全角カタカナに変換する（濁点・半濁点の結合処理含む）。"""
    result = []
    i = 0
    while i < len(text):
        ch = text[i]
        # 次の文字が結合濁点（ﾞ）か確認
        next_ch = text[i + 1] if i + 1 < len(text) else ""
        if next_ch == "ﾞ" and ch in _HALFWIDTH_DAKUTEN:
            result.append(_HALFWIDTH_DAKUTEN[ch])
            i += 2
        elif next_ch == "ﾟ" and ch in _HALFWIDTH_HANDAKUTEN:
            result.append(_HALFWIDTH_HANDAKUTEN[ch])
            i += 2
        elif ch in _HALFWIDTH_TO_FULLWIDTH:
            result.append(_HALFWIDTH_TO_FULLWIDTH[ch])
            i += 1
        else:
            result.append(ch)
            i += 1
    return "".join(result)


def normalize_reading(text: str) -> str:
    """カタカナ・半角カナ・全角スペースを正規化してひらがなに変換する。

    半角数字（0–9）は全角数字（０–９）に変換して通過させる。

    Args:
        text: 入力文字列（全角カタカナ・半角カナ・ひらがなの混合可）

    Returns:
        ひらがな・全角数字に統一された文字列（全角スペースは除去）
    """
    text = text.strip()
    # 全角スペース除去
    text = text.replace("\u3000", "").strip()
    # 半角数字 → 全角数字（U+0030–U+0039 → U+FF10–U+FF19）
    text = "".join(chr(ord(ch) + 0xFEE0) if "0" <= ch <= "9" else ch for ch in text)
    # 半角カナ → 全角カタカナ
    text = _halfwidth_to_fullwidth_katakana(text)
    result = []
    for ch in text:
        code = ord(ch)
        # カタカナ → ひらがな（U+30A1–U+30F6 → U+3041–U+3096）
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        elif 0x3041 <= code <= 0x3096:
            # ひらがなはそのまま
            result.append(ch)
        elif 0xFF10 <= code <= 0xFF19:
            # 全角数字はそのまま通過
            result.append(ch)
        elif ch in ("ー", "・", "　"):
            # 長音符・中点・全角スペースは許可（全角スペースは除去済みだが念のため）
            result.append(ch)
        else:
            raise ValueError(f"非カナ文字が含まれています: {ch!r}")
    return "".join(result)
