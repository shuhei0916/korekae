import json

import pytest

from korekae.candidates import Candidate
from korekae.ingest import ingest, parse_extraction
from korekae.models import Mention, Source, read_jsonl, write_jsonl

TEXT = """\
SOURCE {"id": "s1", "url": "https://a.example/x/", "kind": "note", "title": "Aの記事"}
MENTION {"source_id": "s1", "name": "EarFun Clip", "rank": 1}
MENTION {"source_id": "s1", "name": "ルンバ"}
SKIP s2 2024年の記事
ここは説明文なので無視する
"""


def test_抽出結果の行を読み取る():
    parsed = parse_extraction(TEXT)
    assert [s.id for s in parsed.sources] == ["s1"]
    assert [m.name for m in parsed.mentions] == ["EarFun Clip", "ルンバ"]
    assert parsed.skips == {"s2": "2024年の記事"}


def test_SOURCEのないMENTIONはエラーになる():
    with pytest.raises(ValueError, match="s9"):
        parse_extraction('MENTION {"source_id": "s9", "name": "x"}\n')


def test_壊れたJSONは行番号つきでエラーになる():
    with pytest.raises(ValueError, match="2行目"):
        parse_extraction('SOURCE {"id": "s1", "url": "https://a.example/"}\nMENTION {"source_id": \n')


def _setup(year_dir):
    write_jsonl(year_dir / "sources.jsonl", [Source(id="s0", url="https://z.example/")])
    write_jsonl(year_dir / "mentions.jsonl", [Mention(source_id="s0", name="古い商品")])
    write_jsonl(year_dir / "candidates.jsonl", [
        Candidate(url="https://a.example/x"),
        Candidate(url="https://b.example/"),
        Candidate(url="https://z.example/", status="extracted", source_id="s0"),
    ])


def test_取り込むとソースと言及が追記され候補の状態が更新される(tmp_path):
    _setup(tmp_path)
    text = TEXT.replace("SKIP s2 2024年の記事", "SKIP https://b.example/ 2024年の記事")

    summary = ingest(tmp_path, text)

    assert [s.id for s in read_jsonl(tmp_path / "sources.jsonl", Source)] == ["s0", "s1"]
    assert len(read_jsonl(tmp_path / "mentions.jsonl", Mention)) == 3
    cands = {c.url: c for c in read_jsonl(tmp_path / "candidates.jsonl", Candidate)}
    assert cands["https://a.example/x"].status == "extracted"
    assert cands["https://a.example/x"].source_id == "s1"
    assert cands["https://b.example/"].status == "skipped"
    assert cands["https://b.example/"].reason == "2024年の記事"
    assert summary == {"sources": 1, "mentions": 2, "skipped": 1}


def test_同じソースを取り込み直すと言及は置き換わる(tmp_path):
    _setup(tmp_path)
    ingest(tmp_path, TEXT)
    ingest(tmp_path, TEXT)
    assert len(read_jsonl(tmp_path / "sources.jsonl", Source)) == 2
    assert len(read_jsonl(tmp_path / "mentions.jsonl", Mention)) == 3
