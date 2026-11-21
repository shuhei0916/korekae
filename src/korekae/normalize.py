"""商品名の表記ゆれを吸収するための正規化。"""

import unicodedata


def normalize_name(name: str) -> str:
    """名寄せ用のキーを返す。

    NFKC正規化（全角英数→半角など）と小文字化のあと、文字・数字以外
    （空白、記号、括弧）を取り除く。読みの同一視などは誤統合を招くため行わない。
    """
    text = unicodedata.normalize("NFKC", name).casefold()
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in ("L", "N"))
