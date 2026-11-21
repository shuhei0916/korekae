"""年ごとの設定（config/<年>.toml）。"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    year: int
    tag: str | None = None  # Amazonアソシエイトのトラッキングタグ（自分のもの）
    disclosure: str | None = None  # アソシエイト参加表記
    queries: list[str] = field(default_factory=list)  # 記事を探す検索語


def load_config(path: Path) -> Config:
    with Path(path).open("rb") as f:
        data = tomllib.load(f)
    affiliate = data.get("affiliate", {})
    return Config(
        year=data["year"],
        tag=affiliate.get("tag") or None,
        disclosure=affiliate.get("disclosure") or None,
        queries=data.get("queries", []),
    )
