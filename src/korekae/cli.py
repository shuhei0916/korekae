"""コマンドライン: `korekae run --year 2025`

data/<年>/sources.jsonl と mentions.jsonl（抽出結果）を読み、
名寄せ・集計して products.jsonl / scores.jsonl と output/<年>/ranking.md を書く。
"""

import argparse
import sys
from pathlib import Path

from .aggregate import aggregate, rank_products
from .models import Mention, Source, read_jsonl, write_jsonl
from .render import render_markdown
from .resolve import resolve


def run(year: int, data_dir: Path, out_dir: Path, tag: str | None) -> None:
    year_dir = data_dir / str(year)
    sources = read_jsonl(year_dir / "sources.jsonl", Source)
    mentions = read_jsonl(year_dir / "mentions.jsonl", Mention)

    resolved = resolve(mentions)
    scores = aggregate(
        sources,
        product_ids=resolved.product_ids,
        source_ids=[m.source_id for m in mentions],
        ranks=[m.rank for m in mentions],
    )
    write_jsonl(year_dir / "products.jsonl", resolved.products)
    write_jsonl(year_dir / "scores.jsonl", scores)

    ranked = rank_products({p.id: p for p in resolved.products}, scores)
    out = out_dir / str(year) / "ranking.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(ranked, year=year, source_count=len(sources), tag=tag), encoding="utf-8")
    print(f"{len(sources)}ソース / {len(mentions)}言及 / {len(resolved.products)}商品 → {out}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="korekae")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run", help="抽出結果から名寄せ・集計・出力までを行う")
    p_run.add_argument("--year", type=int, required=True)
    p_run.add_argument("--data-dir", type=Path, default=Path("data"))
    p_run.add_argument("--out-dir", type=Path, default=Path("output"))
    p_run.add_argument("--tag", help="Amazonアソシエイトのトラッキングタグ")
    args = parser.parse_args(argv)

    try:
        run(args.year, args.data_dir, args.out_dir, args.tag)
    except (ValueError, FileNotFoundError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
