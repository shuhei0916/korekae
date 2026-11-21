"""出力: 集計結果を公開用の形式にする。

公開形式（ランキング・ティア表など）が増えたら、ここに関数を足す。
"""

from .models import Product, Score


def amazon_link(asin: str, tag: str | None = None) -> str:
    url = f"https://www.amazon.co.jp/dp/{asin}"
    return f"{url}?tag={tag}" if tag else url


def _cell(text: str | None) -> str:
    return (text or "").replace("|", "\\|")


def _sort_key(score: Score) -> tuple[int, int, int]:
    return (score.author_count, score.top_rank_count, score.mention_count)


def render_markdown(
    ranked: list[tuple[Product, Score]],
    year: int,
    source_count: int,
    tag: str | None = None,
) -> str:
    lines = [
        f"# {year}年 買ってよかったものランキング",
        "",
        f"{source_count}件のソースで「買ってよかった」と挙げられた商品を、"
        "挙げた人の数が多い順に並べています。",
        "",
        "| 順位 | 商品 | ブランド | 挙げた人 | 言及数 | 1位に挙げた数 |",
        "| ---: | --- | --- | ---: | ---: | ---: |",
    ]
    rank = 0
    prev = None
    for i, (product, score) in enumerate(ranked, 1):
        if _sort_key(score) != prev:
            rank, prev = i, _sort_key(score)
        name = _cell(product.name)
        if product.asin:
            name = f"[{name}]({amazon_link(product.asin, tag)})"
        lines.append(
            f"| {rank} | {name} | {_cell(product.brand)} | {score.author_count} "
            f"| {score.mention_count} | {score.top_rank_count} |"
        )
    return "\n".join(lines) + "\n"
