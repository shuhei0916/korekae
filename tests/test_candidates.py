import pytest

from korekae.candidates import Candidate, canonical_url, merge_candidates


@pytest.mark.parametrize(
    "a, b",
    [
        ("https://example.com/post/1/", "https://example.com/post/1"),
        ("http://example.com/post/1", "https://example.com/post/1"),
        ("https://EXAMPLE.com/post/1", "https://example.com/post/1"),
        ("https://example.com/post/1#section", "https://example.com/post/1"),
        ("https://example.com/post/1?utm_source=x&utm_medium=y", "https://example.com/post/1"),
        ("https://example.com/post/1?fbclid=abc", "https://example.com/post/1"),
        ("https://example.com/%e8%b2%b7", "https://example.com/%E8%B2%B7"),
        ("https://example.com/買", "https://example.com/%E8%B2%B7"),
    ],
)
def test_同じ記事を指すURLは同じ正規形になる(a, b):
    assert canonical_url(a) == canonical_url(b)


def test_記事を区別するクエリは残す():
    assert canonical_url("https://kajetblog.com/?p=44899") != canonical_url("https://kajetblog.com/?p=49099")


def test_候補を追加すると正規化したURLで重複を除く():
    existing = [Candidate(url="https://example.com/a", found_via="search")]
    new = [
        Candidate(url="https://example.com/a/", found_via="hatena"),
        Candidate(url="https://example.com/b", found_via="hatena"),
        Candidate(url="https://example.com/b?utm_source=x", found_via="hatena"),
    ]
    merged, added = merge_candidates(existing, new)
    assert [c.url for c in merged] == ["https://example.com/a", "https://example.com/b"]
    assert added == 1


def test_既存候補の状態は上書きしない():
    existing = [Candidate(url="https://example.com/a", status="extracted")]
    merged, _ = merge_candidates(existing, [Candidate(url="https://example.com/a")])
    assert merged[0].status == "extracted"


def test_候補の状態は既知の値でなければならない():
    with pytest.raises(ValueError, match="status"):
        Candidate.from_dict({"url": "https://example.com/a", "status": "done"})


from korekae.candidates import pick_todo, source_id_for


def test_記事IDはサイト名と短いハッシュからなり同じ記事なら同じになる():
    a = source_id_for("https://note.com/foo_bar/n/n123abc")
    assert a.startswith("note-foo_bar-")
    assert a == source_id_for("http://note.com/foo_bar/n/n123abc/?utm_source=x")
    assert a != source_id_for("https://note.com/foo_bar/n/n999")


def test_はてなブログはサブドメインを記事IDに使う():
    assert source_id_for("https://aurorai.hatenablog.com/entry/2026/01/05/1").startswith("hatena-aurorai-")


def test_その他のサイトはホスト名の先頭を使う():
    assert source_id_for("https://www.gizmodo.jp/2025/12/x.html").startswith("gizmodo-")


def test_未読の候補だけを先頭から指定件数とりだす():
    cs = [
        Candidate(url="https://a.example/1", status="extracted"),
        Candidate(url="https://a.example/2"),
        Candidate(url="https://a.example/3", status="skipped"),
        Candidate(url="https://a.example/4"),
        Candidate(url="https://a.example/5"),
    ]
    assert [c.url for c in pick_todo(cs, limit=2)] == ["https://a.example/2", "https://a.example/4"]
