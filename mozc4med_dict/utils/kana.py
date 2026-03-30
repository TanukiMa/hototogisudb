import jaconv


def normalize_reading(text: str) -> str:
    """カタカナ・半角カナ・全角スペースを正規化してひらがなに変換する。

    半角数字（0–9）は全角数字（０–９）に変換して通過させる。

    Args:
        text: 入力文字列（全角カタカナ・半角カナ・ひらがなの混合可）

    Returns:
        ひらがな・全角数字に統一された文字列（全角スペースは除去）
    """
    text = text.strip().replace("\u3000", "").strip()
    # 半角→全角（カナ・英数字・記号すべて）
    text = jaconv.h2z(text, kana=True, digit=True, ascii=False)
    # カタカナ→ひらがな
    text = jaconv.kata2hira(text)

    for ch in text:
        code = ord(ch)
        if 0x3041 <= code <= 0x3096:
            pass  # ひらがな OK
        elif 0xFF10 <= code <= 0xFF19:
            pass  # 全角数字 OK
        elif ch in ("ー", "・"):
            pass  # 長音符・中点 OK
        else:
            raise ValueError(f"非カナ文字が含まれています: {ch!r}")
    return text
