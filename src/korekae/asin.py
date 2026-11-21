"""AmazonのURLからASINを取り出す。"""

import re
from urllib.parse import urlparse

_AMAZON_HOST = re.compile(r"(^|\.)amazon\.(co\.jp|com|jp)$")
_ASIN_IN_PATH = re.compile(
    r"/(?:dp|gp/product|exec/obidos/ASIN)/([A-Za-z0-9]{10})(?:[/?]|$)"
)


def extract_asin(url: str) -> str | None:
    """商品ページURLからASINを返す。取り出せなければNone。

    amzn.to などの短縮URLは展開が必要なため、ここではNoneを返す。
    """
    parsed = urlparse(url)
    if not _AMAZON_HOST.search(parsed.hostname or ""):
        return None
    match = _ASIN_IN_PATH.search(parsed.path)
    return match.group(1).upper() if match else None
