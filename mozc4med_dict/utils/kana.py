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
        code = ord(ch)
        # カタカナ → ひらがな（U+30A1–U+30F6 → U+3041–U+3096）
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        elif 0x3041 <= code <= 0x3096:
            # ひらがなはそのまま
            result.append(ch)
        elif ch in ("ー", "・", "　"):
            # 長音符・中点・全角スペースは許可（全角スペースは除去済みだが念のため）
            result.append(ch)
        else:
            raise ValueError(f"非カナ文字が含まれています: {ch!r}")
    return "".join(result)
