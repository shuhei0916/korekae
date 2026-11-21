from korekae.aggregate import aggregate, rank_products
from korekae.models import Product, Score, Source


def src(id, author=None):
    return Source.from_dict({"id": id, "url": f"https://example.com/{id}", "author": author})


def test_ソース数と著者数を数える():
    sources = [src("s1", "Aさん"), src("s2", "Aさん"), src("s3", "Bさん")]
    scores = aggregate(
        sources,
        product_ids=["p1", "p1", "p1"],
        source_ids=["s1", "s2", "s3"],
        ranks=[None, None, None],
    )
    assert scores == [Score(product_id="p1", mention_count=3, source_count=3, author_count=2)]


def test_著者が不明なソースはソースごとに別の著者とみなす():
    scores = aggregate([src("s1"), src("s2")], ["p1", "p1"], ["s1", "s2"], [None, None])
    assert scores[0].author_count == 2


def test_同じソース内で同じ商品が重複してもソース数は1と数える():
    scores = aggregate([src("s1")], ["p1", "p1"], ["s1", "s1"], [None, None])
    assert (scores[0].mention_count, scores[0].source_count) == (2, 1)


def test_1位に挙げられた回数を数える():
    scores = aggregate([src("s1"), src("s2")], ["p1", "p1"], ["s1", "s2"], [1, 3])
    assert scores[0].top_rank_count == 1


def test_未登録のソースを参照する言及はエラーになる():
    import pytest

    with pytest.raises(ValueError, match="s9"):
        aggregate([src("s1")], ["p1"], ["s9"], [None])


def test_ランキングは著者数_1位回数_言及数の順に並ぶ():
    products = {pid: Product(id=pid, name=name) for pid, name in
                [("a", "あ"), ("b", "い"), ("c", "う"), ("d", "え")]}
    scores = [
        Score("a", mention_count=1, source_count=1, author_count=1),
        Score("b", mention_count=2, source_count=2, author_count=2),
        Score("c", mention_count=1, source_count=1, author_count=1, top_rank_count=1),
        Score("d", mention_count=2, source_count=1, author_count=1),
    ]
    ranked = rank_products(products, scores)
    assert [p.id for p, _ in ranked] == ["b", "c", "d", "a"]
