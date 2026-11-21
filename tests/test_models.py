import pytest

from korekae.models import Mention, Source, read_jsonl, write_jsonl


def test_必須項目だけでMentionを作れる():
    m = Mention.from_dict({"source_id": "s1", "name": "AirPods Pro 2"})
    assert m.source_id == "s1"
    assert m.name == "AirPods Pro 2"
    assert m.rank is None
    assert m.amazon_url is None


def test_必須項目が欠けたMentionはエラーになる():
    with pytest.raises(ValueError, match="name"):
        Mention.from_dict({"source_id": "s1"})


def test_未知の項目を含むとエラーになる():
    # 手書きのJSONLで項目名を打ち間違えたときに気づけるようにする
    with pytest.raises(ValueError, match="amazon_link"):
        Mention.from_dict({"source_id": "s1", "name": "x", "amazon_link": "https://..."})


def test_順位は正の整数でなければならない():
    with pytest.raises(ValueError, match="rank"):
        Mention.from_dict({"source_id": "s1", "name": "x", "rank": 0})


def test_Sourceは種別が既知の値でなければならない():
    with pytest.raises(ValueError, match="kind"):
        Source.from_dict({"id": "s1", "url": "https://example.com", "kind": "tv"})


def test_JSONLに書いて読み戻すと同じ内容になる(tmp_path):
    path = tmp_path / "mentions.jsonl"
    mentions = [
        Mention.from_dict({"source_id": "s1", "name": "ルンバ", "rank": 1}),
        Mention.from_dict({"source_id": "s2", "name": "AirPods Pro 2"}),
    ]
    write_jsonl(path, mentions)
    assert read_jsonl(path, Mention) == mentions
    # 日本語がエスケープされず人が読める形で保存される
    assert "ルンバ" in path.read_text(encoding="utf-8")


def test_JSONLの空行は読み飛ばす(tmp_path):
    path = tmp_path / "mentions.jsonl"
    path.write_text('{"source_id": "s1", "name": "x"}\n\n', encoding="utf-8")
    assert len(read_jsonl(path, Mention)) == 1
