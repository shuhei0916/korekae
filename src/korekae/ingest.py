"""抽出結果（Claudeが記事を読んで書き出したテキスト）の取り込み。

書式（1行1レコード。それ以外の行は無視する）:
    SOURCE  {"id": ..., "url": ..., ...}
    MENTION {"source_id": ..., "name": ..., ...}
    SKIP    <ソースIDまたはURL> <理由>
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from .candidates import Candidate, canonical_url
from .models import Mention, Source, read_jsonl, write_jsonl


@dataclass
class Extraction:
    sources: list[Source] = field(default_factory=list)
    mentions: list[Mention] = field(default_factory=list)
    skips: dict[str, str] = field(default_factory=dict)


def parse_extraction(text: str) -> Extraction:
    result = Extraction()
    for lineno, line in enumerate(text.splitlines(), 1):
        head, _, rest = line.strip().partition(" ")
        try:
            if head == "SOURCE":
                result.sources.append(Source.from_dict(json.loads(rest)))
            elif head == "MENTION":
                result.mentions.append(Mention.from_dict(json.loads(rest)))
            elif head == "SKIP":
                target, _, reason = rest.strip().partition(" ")
                result.skips[target] = reason.strip() or "対象外"
        except (ValueError, TypeError) as e:
            raise ValueError(f"{lineno}行目: {e}") from e
    ids = {s.id for s in result.sources}
    orphans = sorted({m.source_id for m in result.mentions} - ids)
    if orphans:
        raise ValueError(f"SOURCE 行のない source_id があります: {orphans}")
    return result


def _read(path: Path, cls):
    return read_jsonl(path, cls) if path.exists() else []


def ingest(year_dir: Path, text: str, id_urls: dict[str, str] | None = None) -> dict[str, int]:
    """抽出結果を data/<年>/ に取り込む。同じソースIDは置き換える。"""
    parsed = parse_extraction(text)
    new_ids = {s.id for s in parsed.sources}

    sources = [s for s in _read(year_dir / "sources.jsonl", Source) if s.id not in new_ids]
    mentions = [m for m in _read(year_dir / "mentions.jsonl", Mention) if m.source_id not in new_ids]
    write_jsonl(year_dir / "sources.jsonl", sources + parsed.sources)
    write_jsonl(year_dir / "mentions.jsonl", mentions + parsed.mentions)

    extracted = {canonical_url(s.url): s.id for s in parsed.sources}
    skipped = {}
    for target, reason in parsed.skips.items():
        url = target if target.startswith("http") else (id_urls or {}).get(target)
        if url:
            skipped[canonical_url(url)] = reason
    cpath = year_dir / "candidates.jsonl"
    candidates = _read(cpath, Candidate)
    known = set()
    for c in candidates:
        key = canonical_url(c.url)
        known.add(key)
        if key in extracted:
            c.status, c.source_id, c.reason = "extracted", extracted[key], None
        elif key in skipped:
            c.status, c.reason = "skipped", skipped[key]
    # 候補に無いソースも候補として記録しておく（再実行時の重複取得を防ぐ）
    for s in parsed.sources:
        if canonical_url(s.url) not in known:
            candidates.append(Candidate(url=s.url, title=s.title, status="extracted", source_id=s.id))
    write_jsonl(cpath, candidates)

    return {"sources": len(parsed.sources), "mentions": len(parsed.mentions), "skipped": len(skipped)}
