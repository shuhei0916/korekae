"""コマンドライン。

- korekae run --year 2025        : 抽出結果から名寄せ・集計・出力まで
- korekae candidates add FILE    : 見つけた記事URL（TSV: URL<TAB>タイトル）を候補に追加
- korekae status --year 2025     : 候補と抽出の進み具合を表示
- korekae ingest --year 2025 FILE: 抽出結果（SOURCE/MENTION/SKIP 行）を取り込む
- korekae candidates todo        : 次に読む未読候補を「ID<TAB>URL<TAB>タイトル」で出す
- korekae asin todo / asin add   : ASINのない商品を出す / 調べたASINを補う
- korekae snapshot --year 2025   : 100記事ごとに上位を保存し、飽和したかを判定する
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from .aggregate import aggregate, rank_products
from .candidates import Candidate, merge_candidates, pick_todo, source_id_for
from .config import Config, load_config
from .ingest import ingest
from .models import Mention, Product, Score, Source, read_jsonl, write_jsonl
from .render import render_markdown
from .resolve import resolve
from .stability import due_snapshot, judge, overlap

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
SATURATION_THRESHOLD = 0.9  # 上位N件のうち9割が前回と同じなら「ほぼ動かない」


def _load_config(config_dir: Path, year: int) -> Config:
    path = config_dir / f"{year}.toml"
    return load_config(path) if path.exists() else Config(year=year)


def load_asin_overrides(year_dir: Path) -> dict[str, str]:
    path = year_dir / "asins.jsonl"
    if not path.exists():
        return {}
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return {r["product_id"]: r["asin"] for r in rows}


def load_merges(year_dir: Path) -> dict[str, str]:
    """merges.tsv（統合元の商品ID<TAB>統合先の商品ID<TAB>メモ、# で始まる行は注釈）を読む。"""
    path = year_dir / "merges.tsv"
    if not path.exists():
        return {}
    merges = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.split("\t")
        merges[cols[0].strip()] = cols[1].strip()
    return merges


def _compute(year_dir: Path):
    sources = read_jsonl(year_dir / "sources.jsonl", Source)
    mentions = read_jsonl(year_dir / "mentions.jsonl", Mention)
    resolved = resolve(mentions, asin_overrides=load_asin_overrides(year_dir), merges=load_merges(year_dir))
    scores = aggregate(
        sources,
        product_ids=resolved.product_ids,
        source_ids=[m.source_id for m in mentions],
        ranks=[m.rank for m in mentions],
    )
    return sources, mentions, resolved, scores


def run(year: int, data_dir: Path, out_dir: Path, config: Config) -> None:
    year_dir = data_dir / str(year)
    sources, mentions, resolved, scores = _compute(year_dir)
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


def todo_candidates(year: int, data_dir: Path, limit: int) -> None:
    path = data_dir / str(year) / "candidates.jsonl"
    candidates = read_jsonl(path, Candidate) if path.exists() else []
    for c in pick_todo(candidates, limit):
        print(f"{source_id_for(c.url)}\t{c.url}\t{c.title or ''}")


def todo_asins(year: int, data_dir: Path, limit: int | None) -> None:
    _, _, resolved, scores = _compute(data_dir / str(year))
    ranked = rank_products({p.id: p for p in resolved.products}, scores)
    missing = [p for p, _ in ranked if not p.asin]
    for p in missing[:limit] if limit else missing:
        print(f"{p.id}\t{p.name}\t{p.brand or ''}")


def add_asins(year: int, data_dir: Path, tsv: Path) -> None:
    year_dir = data_dir / str(year)
    overrides = load_asin_overrides(year_dir)
    added = 0
    for lineno, line in enumerate(tsv.read_text(encoding="utf-8").splitlines(), 1):
        cols = [c.strip() for c in line.split("\t")]
        if len(cols) < 2 or not cols[0]:
            continue
        pid, asin = cols[0], cols[1].upper()
        if not pid.startswith("name:") or not ASIN_RE.match(asin):
            raise ValueError(f"{tsv}:{lineno}行目: 「name:<キー><TAB>ASIN(英数字10桁)」の形ではありません: {line!r}")
        overrides[pid] = asin
        added += 1
    year_dir.mkdir(parents=True, exist_ok=True)
    (year_dir / "asins.jsonl").write_text(
        "".join(json.dumps({"product_id": k, "asin": v}, ensure_ascii=False) + "\n" for k, v in sorted(overrides.items())),
        encoding="utf-8",
    )
    print(f"ASINを{added}件補いました（補ったASINは全部で{len(overrides)}件）")


def snapshot(year: int, data_dir: Path, top: int) -> None:
    year_dir = data_dir / str(year)
    sources = read_jsonl(year_dir / "sources.jsonl", Source)
    products = {p.id: p for p in read_jsonl(year_dir / "products.jsonl", Product)}
    scores = read_jsonl(year_dir / "scores.jsonl", Score)
    snap_dir = year_dir / "snapshots"
    snaps = sorted(
        (json.loads(p.read_text(encoding="utf-8")) for p in snap_dir.glob("*.json")),
        key=lambda s: s["source_count"],
    ) if snap_dir.exists() else []
    taken = [s["source_count"] for s in snaps]
    if not due_snapshot(len(sources), taken):
        nxt = (max(taken) if taken else 0) + 100
        print(f"まだ撮りません（{len(sources)}記事。次は{nxt}記事に達したとき）")
        return
    current = [p.id for p, _ in rank_products(products, scores)[:top]]
    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / f"{len(sources)}.json").write_text(
        json.dumps({"source_count": len(sources), "top": current}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    if not snaps:
        print(f"{len(sources)}記事時点の上位{top}件を保存しました（初回）")
        return
    seq = [s["top"] for s in snaps] + [current]
    overlaps = [overlap(a, b) for a, b in zip(seq, seq[1:])]
    print(f"{len(sources)}記事時点: 上位{top}件のうち{overlaps[-1]}件が前回（{taken[-1]}記事）と同じ")
    if judge(overlaps, threshold=int(top * SATURATION_THRESHOLD)):
        print(f"飽和: 2回続けて上位{top}件の{int(SATURATION_THRESHOLD * 100)}%以上が変わりませんでした")


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

    p_todo = cand_sub.add_parser("todo", help="次に読む未読候補を ID<TAB>URL<TAB>タイトル で出す")
    common(p_todo)
    p_todo.add_argument("--limit", type=int, default=80)

    p_asin = sub.add_parser("asin", help="ASINのない商品を補う")
    asin_sub = p_asin.add_subparsers(dest="action", required=True)
    p_atodo = asin_sub.add_parser("todo", help="ASINのない商品を順位順に出す")
    common(p_atodo)
    p_atodo.add_argument("--limit", type=int)
    p_aadd = asin_sub.add_parser("add", help="TSV（商品ID<TAB>ASIN）でASINを補う")
    common(p_aadd)
    p_aadd.add_argument("file", type=Path)

    p_snap = sub.add_parser("snapshot", help="100記事ごとに上位を保存し、飽和を判定する")
    common(p_snap)
    p_snap.add_argument("--top", type=int, default=50)

    p_status = sub.add_parser("status", help="進み具合を表示する")
    common(p_status)

    p_ingest = sub.add_parser("ingest", help="抽出結果を取り込む")
    common(p_ingest)
    p_ingest.add_argument("--ids", type=Path, help="SKIP 行のIDをURLに対応させるTSV（ID<TAB>URL）")
    p_ingest.add_argument("file", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            config = _load_config(args.config_dir, args.year)
            if args.tag:
                config.tag = args.tag
            run(args.year, args.data_dir, args.out_dir, config)
        elif args.command == "candidates" and args.action == "add":
            add_candidates(args.year, args.data_dir, args.file, args.via)
        elif args.command == "candidates":
            todo_candidates(args.year, args.data_dir, args.limit)
        elif args.command == "asin" and args.action == "todo":
            todo_asins(args.year, args.data_dir, args.limit)
        elif args.command == "asin":
            add_asins(args.year, args.data_dir, args.file)
        elif args.command == "snapshot":
            snapshot(args.year, args.data_dir, args.top)
        elif args.command == "status":
            show_status(args.year, args.data_dir)
        elif args.command == "ingest":
            id_urls = {}
            if args.ids:
                for line in args.ids.read_text(encoding="utf-8").splitlines():
                    if "\t" in line:
                        k, v = line.split("\t")[:2]
                        id_urls[k.strip()] = v.strip()
            summary = ingest(args.data_dir / str(args.year), args.file.read_text(encoding="utf-8"), id_urls)
            print(f"ソース{summary['sources']}件 / 言及{summary['mentions']}件 / 対象外{summary['skipped']}件")
    except (ValueError, FileNotFoundError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
