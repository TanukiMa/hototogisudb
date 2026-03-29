def normalize_reading(text: str) -> str:
    """カタカナ・全角スペースを正規化してひらがなに変換する。

    Args:
        text: 入力文字列（カタカナとひらがなの混合可）

    Returns:
        ひらがなに統一された文字列（全角スペースは除去）
    """
    text = text.strip()
    # 全角スペース除去
    text = text.replace("\u3000", "").strip()
    result = []
    for ch in text:
        # カタカナ → ひらがな（U+30A1–U+30F6 → U+3041–U+3096）
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(ch)
    return "".join(result)
