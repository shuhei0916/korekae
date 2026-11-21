import json

from korekae.cli import main


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def test_runで抽出結果からランキングまで一気通貫で作れる(tmp_path):
    data = tmp_path / "data"
    write(data / "2025" / "sources.jsonl", [
        {"id": "s1", "url": "https://a.example/", "author": "Aさん"},
        {"id": "s2", "url": "https://b.example/", "author": "Bさん"},
    ])
    write(data / "2025" / "mentions.jsonl", [
        {"source_id": "s1", "name": "EarFun Clip", "amazon_url": "https://www.amazon.co.jp/dp/B0F89WH1KY", "rank": 1},
        {"source_id": "s2", "name": "EarFun Clip"},
        {"source_id": "s2", "name": "ルンバ"},
    ])

    code = main(["run", "--year", "2025", "--data-dir", str(data), "--out-dir", str(tmp_path / "out"), "--tag", "t-22"])

    assert code == 0
    products = (data / "2025" / "products.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(products) == 2
    scores = [json.loads(l) for l in (data / "2025" / "scores.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {"product_id": "asin:B0F89WH1KY", "mention_count": 2, "source_count": 2,
            "author_count": 2, "top_rank_count": 1} in scores
    md = (tmp_path / "out" / "2025" / "ranking.md").read_text(encoding="utf-8")
    assert "| 1 | [EarFun Clip](https://www.amazon.co.jp/dp/B0F89WH1KY?tag=t-22) |" in md


def test_入力ファイルが壊れていれば行番号つきで失敗する(tmp_path, capsys):
    data = tmp_path / "data"
    write(data / "2025" / "sources.jsonl", [{"id": "s1", "url": "https://a.example/"}])
    write(data / "2025" / "mentions.jsonl", [{"source_id": "s1"}])

    code = main(["run", "--year", "2025", "--data-dir", str(data), "--out-dir", str(tmp_path / "out")])

    assert code == 1
    assert "mentions.jsonl:1" in capsys.readouterr().err


def _minimal_data(data):
    write(data / "2025" / "sources.jsonl", [{"id": "s1", "url": "https://a.example/", "title": "Aの記事"}])
    write(data / "2025" / "mentions.jsonl", [
        {"source_id": "s1", "name": "EarFun Clip", "amazon_url": "https://www.amazon.co.jp/dp/B0F89WH1KY?tag=someone-22"},
    ])


def test_runは設定ファイルのタグと参加表記を使う(tmp_path):
    data = tmp_path / "data"
    _minimal_data(data)
    config = tmp_path / "config"
    config.mkdir()
    (config / "2025.toml").write_text(
        'year = 2025\n[affiliate]\ntag = "mine-22"\ndisclosure = "参加表記です。"\n', encoding="utf-8")

    code = main(["run", "--year", "2025", "--data-dir", str(data), "--out-dir", str(tmp_path / "out"),
                 "--config-dir", str(config)])

    assert code == 0
    md = (tmp_path / "out" / "2025" / "ranking.md").read_text(encoding="utf-8")
    assert "dp/B0F89WH1KY?tag=mine-22" in md
    assert "someone-22" not in md
    assert "参加表記です。" in md
    assert "- [Aの記事](https://a.example/)" in md


def test_candidates_addでTSVの候補URLを重複なく追加できる(tmp_path, capsys):
    data = tmp_path / "data"
    tsv = tmp_path / "found.tsv"
    tsv.write_text("https://a.example/x/\tAの記事\nhttps://a.example/x?utm_source=t\tAの記事\n\nhttps://b.example/\tB\n",
                   encoding="utf-8")

    assert main(["candidates", "add", "--year", "2025", "--data-dir", str(data), "--via", "hatena", str(tsv)]) == 0
    assert main(["candidates", "add", "--year", "2025", "--data-dir", str(data), "--via", "hatena", str(tsv)]) == 0

    lines = (data / "2025" / "candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    out = capsys.readouterr().out
    assert "2件追加" in out and "0件追加" in out


def test_statusで候補と抽出の進み具合を表示する(tmp_path, capsys):
    data = tmp_path / "data"
    _minimal_data(data)
    write(data / "2025" / "candidates.jsonl", [
        {"url": "https://a.example/", "status": "extracted", "source_id": "s1"},
        {"url": "https://b.example/"},
        {"url": "https://c.example/", "status": "skipped", "reason": "2024年の記事"},
    ])

    assert main(["status", "--year", "2025", "--data-dir", str(data)]) == 0

    out = capsys.readouterr().out
    assert "候補 3件（未読 1 / 抽出済み 1 / 対象外 1）" in out
    assert "ソース 1件 / 言及 1件" in out


def test_ingestで抽出結果を取り込める(tmp_path, capsys):
    data = tmp_path / "data"
    write(data / "2025" / "candidates.jsonl", [{"url": "https://a.example/"}, {"url": "https://b.example/"}])
    extraction = tmp_path / "batch1.txt"
    extraction.write_text(
        'SOURCE {"id": "a", "url": "https://a.example/"}\n'
        'MENTION {"source_id": "a", "name": "EarFun Clip"}\n'
        'SKIP b 2024年の記事\n', encoding="utf-8")
    ids = tmp_path / "ids.tsv"
    ids.write_text("a\thttps://a.example/\nb\thttps://b.example/\n", encoding="utf-8")

    assert main(["ingest", "--year", "2025", "--data-dir", str(data), "--ids", str(ids), str(extraction)]) == 0

    assert "ソース1件 / 言及1件 / 対象外1件" in capsys.readouterr().out
    assert '"status": "skipped"' in (data / "2025" / "candidates.jsonl").read_text(encoding="utf-8")
