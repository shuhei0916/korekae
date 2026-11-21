"""集計: 商品ごとに言及数・ソース数・著者数などを数える。

スコア（重み付け）はここでは決めず、元になる数値だけを残す。
並べ方は出力側で選べるようにする。
"""

from collections import defaultdict

from .models import Product, Score, Source


def aggregate(
    sources: list[Source],
    product_ids: list[str],
    source_ids: list[str],
    ranks: list[int | None],
) -> list[Score]:
    by_id = {s.id: s for s in sources}
    stats: dict[str, dict] = defaultdict(
        lambda: {"mentions": 0, "sources": set(), "authors": set(), "top": 0}
    )
    for pid, sid, rank in zip(product_ids, source_ids, ranks, strict=True):
        if sid not in by_id:
            raise ValueError(f"sources に存在しないソースIDです: {sid}")
        source = by_id[sid]
        st = stats[pid]
        st["mentions"] += 1
        st["sources"].add(sid)
        # 著者不明のソースは、ソースそのものを1人の著者とみなす
        st["authors"].add(source.author or f"source:{sid}")
        if rank == 1:
            st["top"] += 1
    return [
        Score(
            product_id=pid,
            mention_count=st["mentions"],
            source_count=len(st["sources"]),
            author_count=len(st["authors"]),
            top_rank_count=st["top"],
        )
        for pid, st in sorted(stats.items())
    ]


def rank_products(
    products: dict[str, Product], scores: list[Score]
) -> list[tuple[Product, Score]]:
    """既定の並べ方: 著者数 → 1位に挙げられた数 → 言及数 → 商品名。"""
    pairs = [(products[s.product_id], s) for s in scores]
    return sorted(
        pairs,
        key=lambda ps: (-ps[1].author_count, -ps[1].top_rank_count, -ps[1].mention_count, ps[0].name),
    )
