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
