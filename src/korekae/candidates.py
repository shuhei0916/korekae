"""記事候補（まだ読んでいないURL）の管理。

data/<年>/candidates.jsonl に1行1候補で置く。
- todo      : まだ読んでいない
- extracted : 読んで sources.jsonl / mentions.jsonl に書き出した
- skipped   : 読んだが対象外だった（reason に理由）
"""

from dataclasses import dataclass
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from .models import _Record

STATUSES = ("todo", "extracted", "skipped")
_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"fbclid", "gclid", "yclid", "mc_cid", "mc_eid", "ref", "ref_src"}


def canonical_url(url: str) -> str:
    """同じ記事を指すURLを同じ文字列にする（重複判定用）。"""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    path = quote(unquote(parts.path), safe="/:@!$&'()*+,;=-._~")
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(
        [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k not in _TRACKING_KEYS and not k.startswith(_TRACKING_PREFIXES)
        ]
    )
    return urlunsplit(("https", host, path, query, ""))


@dataclass
class Candidate(_Record):
    url: str
    title: str | None = None
    found_via: str | None = None  # hatena / note / search など
    status: str = "todo"
    source_id: str | None = None  # extracted のとき、対応する sources.jsonl の id
    reason: str | None = None  # skipped のときの理由

    _required = ("url",)

    def _validate(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"Candidate: status は {STATUSES} のいずれか: {self.status!r}")


def merge_candidates(
    existing: list[Candidate], new: list[Candidate]
) -> tuple[list[Candidate], int]:
    """既存の候補に新しい候補を足す。既存の状態は保ち、追加した件数を返す。"""
    merged = list(existing)
    seen = {canonical_url(c.url) for c in existing}
    added = 0
    for c in new:
        key = canonical_url(c.url)
        if key in seen:
            continue
        seen.add(key)
        merged.append(c)
        added += 1
    return merged, added
