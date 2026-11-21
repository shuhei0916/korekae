"""コマンドライン。

- korekae run --year 2025        : 抽出結果から名寄せ・集計・出力まで
- korekae candidates add FILE    : 見つけた記事URL（TSV: URL<TAB>タイトル）を候補に追加
- korekae status --year 2025     : 候補と抽出の進み具合を表示
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from .aggregate import aggregate, rank_products
from .candidates import Candidate, merge_candidates
from .config import Config, load_config
from .models import Mention, Source, read_jsonl, write_jsonl
from .render import render_markdown
from .resolve import resolve


def _load_config(config_dir: Path, year: int) -> Config:
    path = config_dir / f"{year}.toml"
    return load_config(path) if path.exists() else Config(year=year)


def run(year: int, data_dir: Path, out_dir: Path, config: Config) -> None:
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
    out.write_text(
        render_markdown(
            ranked,
            year=year,
            source_count=len(sources),
            tag=config.tag,
            disclosure=config.disclosure,
            sources=sources,
        ),
        encoding="utf-8",
    )
    print(f"{len(sources)}ソース / {len(mentions)}言及 / {len(resolved.products)}商品 → {out}")
    if not config.tag:
        print("注意: アソシエイトタグが未設定です（config/<年>.toml の [affiliate] tag）")


def add_candidates(year: int, data_dir: Path, tsv: Path, via: str | None) -> None:
    path = data_dir / str(year) / "candidates.jsonl"
    existing = read_jsonl(path, Candidate) if path.exists() else []
    new = []
    for line in tsv.read_text(encoding="utf-8").splitlines():
        cols = line.split("\t")
        if not cols[0].strip():
            continue
        title = cols[1].strip() if len(cols) > 1 and cols[1].strip() else None
        new.append(Candidate(url=cols[0].strip(), title=title, found_via=via))
    merged, added = merge_candidates(existing, new)
    write_jsonl(path, merged)
    print(f"{added}件追加（候補は全部で{len(merged)}件）")


def show_status(year: int, data_dir: Path) -> None:
    year_dir = data_dir / str(year)
    cpath = year_dir / "candidates.jsonl"
    candidates = read_jsonl(cpath, Candidate) if cpath.exists() else []
    counts = Counter(c.status for c in candidates)
    print(
        f"候補 {len(candidates)}件（未読 {counts['todo']} / 抽出済み {counts['extracted']}"
        f" / 対象外 {counts['skipped']}）"
    )
    sources = read_jsonl(year_dir / "sources.jsonl", Source) if (year_dir / "sources.jsonl").exists() else []
    mentions = read_jsonl(year_dir / "mentions.jsonl", Mention) if (year_dir / "mentions.jsonl").exists() else []
    print(f"ソース {len(sources)}件 / 言及 {len(mentions)}件")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="korekae")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--year", type=int, required=True)
        p.add_argument("--data-dir", type=Path, default=Path("data"))

    p_run = sub.add_parser("run", help="抽出結果から名寄せ・集計・出力までを行う")
    common(p_run)
    p_run.add_argument("--out-dir", type=Path, default=Path("output"))
    p_run.add_argument("--config-dir", type=Path, default=Path("config"))
    p_run.add_argument("--tag", help="Amazonアソシエイトのトラッキングタグ（設定ファイルより優先）")

    p_cand = sub.add_parser("candidates", help="記事候補を管理する")
    cand_sub = p_cand.add_subparsers(dest="action", required=True)
    p_add = cand_sub.add_parser("add", help="TSV（URL<TAB>タイトル）の候補を追加する")
    common(p_add)
    p_add.add_argument("--via", help="見つけた場所（hatena / note / search など）")
    p_add.add_argument("file", type=Path)

    p_status = sub.add_parser("status", help="進み具合を表示する")
    common(p_status)

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            config = _load_config(args.config_dir, args.year)
            if args.tag:
                config.tag = args.tag
            run(args.year, args.data_dir, args.out_dir, config)
        elif args.command == "candidates":
            add_candidates(args.year, args.data_dir, args.file, args.via)
        elif args.command == "status":
            show_status(args.year, args.data_dir)
    except (ValueError, FileNotFoundError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
