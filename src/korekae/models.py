"""中間データ形式（JSONL）のレコード定義と読み書き。

data/<年>/ 以下に置くファイル:
- sources.jsonl  : 1行1ソース（記事・動画など）
- mentions.jsonl : 1行1言及（ある記事がある商品を「買ってよかった」と挙げたこと）
- products.jsonl : 名寄せ後の商品（パイプラインが生成）
- scores.jsonl   : 商品ごとの集計値（パイプラインが生成）
"""

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Iterable, TypeVar

SOURCE_KINDS = ("blog", "note", "hatena", "scrapbox", "media", "youtube", "x", "other")


class _Record:
    _required: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        names = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        unknown = set(data) - names
        if unknown:
            raise ValueError(f"{cls.__name__}: 未知の項目 {sorted(unknown)}")
        missing = [k for k in cls._required if data.get(k) in (None, "")]
        if missing:
            raise ValueError(f"{cls.__name__}: 必須項目がありません {missing}")
        record = cls(**data)
        record._validate()
        return record

    def _validate(self) -> None:
        pass

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v not in (None, [], "")}  # type: ignore[call-overload]


@dataclass
class Source(_Record):
    id: str
    url: str
    kind: str = "blog"
    title: str | None = None
    author: str | None = None
    published_at: str | None = None  # YYYY-MM-DD
    lang: str = "ja"

    _required = ("id", "url")

    def _validate(self) -> None:
        if self.kind not in SOURCE_KINDS:
            raise ValueError(f"Source: kind は {SOURCE_KINDS} のいずれか: {self.kind!r}")


@dataclass
class Mention(_Record):
    source_id: str
    name: str  # 記事に書かれたままの商品名
    brand: str | None = None
    amazon_url: str | None = None
    asin: str | None = None  # URLから取れないときに手で補う
    rank: int | None = None  # 記事内で明示された順位
    category: str | None = None
    comment: str | None = None  # 短い要約（本文の転載はしない）

    _required = ("source_id", "name")

    def _validate(self) -> None:
        if self.rank is not None and (not isinstance(self.rank, int) or self.rank < 1):
            raise ValueError(f"Mention: rank は1以上の整数: {self.rank!r}")


@dataclass
class Product(_Record):
    id: str
    name: str
    asin: str | None = None
    brand: str | None = None
    category: str | None = None
    aliases: list[str] = field(default_factory=list)

    _required = ("id", "name")


@dataclass
class Score(_Record):
    product_id: str
    mention_count: int = 0  # 言及の数
    source_count: int = 0  # 言及したソースの数
    author_count: int = 0  # 言及した著者の数（同じ著者の重複を除く）
    top_rank_count: int = 0  # 記事内で1位に挙げられた数

    _required = ("product_id",)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


R = TypeVar("R", bound=_Record)


def read_jsonl(path: Path, cls: type[R]) -> list[R]:
    records = []
    with Path(path).open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(cls.from_dict(json.loads(line)))
            except (ValueError, TypeError) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e
    return records


def write_jsonl(path: Path, records: Iterable[_Record]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
