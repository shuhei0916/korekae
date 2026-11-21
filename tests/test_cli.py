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
