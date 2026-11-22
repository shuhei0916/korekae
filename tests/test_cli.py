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


def test_candidates_todoは未読候補をID_URL_タイトルのTSVで出しそのままingestに渡せる(tmp_path, capsys):
    data = tmp_path / "data"
    write(data / "2025" / "candidates.jsonl", [
        {"url": "https://note.com/a/n/n1", "title": "A"},
        {"url": "https://note.com/b/n/n2", "title": "B"},
    ])
    assert main(["candidates", "todo", "--year", "2025", "--data-dir", str(data), "--limit", "1"]) == 0
    line = capsys.readouterr().out.strip()
    sid, url, title = line.split("\t")
    assert sid.startswith("note-a-") and url == "https://note.com/a/n/n1" and title == "A"

    ids = tmp_path / "ids.tsv"
    ids.write_text(line + "\n", encoding="utf-8")
    ext = tmp_path / "ext.txt"
    ext.write_text(f"SKIP {sid} リストではない\n", encoding="utf-8")
    assert main(["ingest", "--year", "2025", "--data-dir", str(data), "--ids", str(ids), str(ext)]) == 0
    cands = [json.loads(l) for l in (data / "2025" / "candidates.jsonl").read_text(encoding="utf-8").splitlines()]
    assert cands[0]["status"] == "skipped"


def _small_year(data):
    write(data / "2025" / "sources.jsonl", [{"id": f"s{i}", "url": f"https://a.example/{i}"} for i in range(3)])
    write(data / "2025" / "mentions.jsonl", [
        {"source_id": "s0", "name": "AirPods Pro 3", "brand": "Apple"},
        {"source_id": "s1", "name": "Apple AirPods Pro 3"},
        {"source_id": "s2", "name": "ルンバ", "amazon_url": "https://www.amazon.co.jp/dp/B000000001"},
    ])


def test_asin_todoはASINのない商品を順位順に出す(tmp_path, capsys):
    data = tmp_path / "data"
    _small_year(data)
    assert main(["asin", "todo", "--year", "2025", "--data-dir", str(data)]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["name:appleairpodspro3\tAirPods Pro 3\tApple"]


def test_asin_addで補ったASINがrunのリンクに反映される(tmp_path, capsys):
    data = tmp_path / "data"
    _small_year(data)
    tsv = tmp_path / "asins.tsv"
    tsv.write_text("name:appleairpodspro3\tB0FQXXXXXX\tメモ\n", encoding="utf-8")
    assert main(["asin", "add", "--year", "2025", "--data-dir", str(data), str(tsv)]) == 0
    assert main(["run", "--year", "2025", "--data-dir", str(data), "--out-dir", str(tmp_path / "out"), "--tag", "t-22"]) == 0
    md = (tmp_path / "out" / "2025" / "ranking.md").read_text(encoding="utf-8")
    assert "https://www.amazon.co.jp/dp/B0FQXXXXXX?tag=t-22" in md


def test_asin_addは形のおかしいASINを拒む(tmp_path, capsys):
    data = tmp_path / "data"
    _small_year(data)
    tsv = tmp_path / "asins.tsv"
    tsv.write_text("name:appleairpodspro3\tamzn.to/xyz\n", encoding="utf-8")
    assert main(["asin", "add", "--year", "2025", "--data-dir", str(data), str(tsv)]) == 1


def test_snapshotは100記事ごとに上位を保存し前回との重なりを表示する(tmp_path, capsys):
    data = tmp_path / "data"
    sources = [{"id": f"s{i}", "url": f"https://a.example/{i}"} for i in range(100)]
    write(data / "2025" / "sources.jsonl", sources)
    write(data / "2025" / "mentions.jsonl", [{"source_id": f"s{i}", "name": f"商品{i % 7}"} for i in range(100)])
    assert main(["run", "--year", "2025", "--data-dir", str(data), "--out-dir", str(tmp_path / "out")]) == 0
    capsys.readouterr()
    assert main(["snapshot", "--year", "2025", "--data-dir", str(data), "--top", "5"]) == 0
    assert "100記事" in capsys.readouterr().out
    assert (data / "2025" / "snapshots" / "100.json").exists()
    # 記事数が増えていなければ撮らない
    assert main(["snapshot", "--year", "2025", "--data-dir", str(data), "--top", "5"]) == 0
    assert "まだ" in capsys.readouterr().out


def test_merges_tsvに書いた商品はrunで1つにまとまる(tmp_path):
    data = tmp_path / "data"
    write(data / "2025" / "sources.jsonl", [
        {"id": "s1", "url": "https://a.example/", "author": "Aさん"},
        {"id": "s2", "url": "https://b.example/", "author": "Bさん"},
    ])
    write(data / "2025" / "mentions.jsonl", [
        {"source_id": "s1", "name": "Nintendo Switch 2", "amazon_url": "https://www.amazon.co.jp/dp/B0G3SXHCLJ"},
        {"source_id": "s2", "name": "任天堂 Nintendo Switch 2", "amazon_url": "https://www.amazon.co.jp/dp/B0FNC43RBM"},
    ])
    (data / "2025" / "merges.tsv").write_text(
        "# 統合元\t統合先\tメモ\nasin:B0FNC43RBM\tasin:B0G3SXHCLJ\tセット違い\n", encoding="utf-8"
    )

    assert main(["run", "--year", "2025", "--data-dir", str(data), "--out-dir", str(tmp_path / "out")]) == 0
    scores = [json.loads(l) for l in (data / "2025" / "scores.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(s["product_id"], s["author_count"]) for s in scores] == [("asin:B0G3SXHCLJ", 2)]
