from korekae.models import Product, Score
from korekae.render import amazon_link, render_markdown


def test_アソシエイトタグ付きのAmazonリンクを作る():
    assert amazon_link("B0F89WH1KY", tag="korekae-22") == "https://www.amazon.co.jp/dp/B0F89WH1KY?tag=korekae-22"


def test_タグがなければタグなしのリンクを作る():
    assert amazon_link("B0F89WH1KY") == "https://www.amazon.co.jp/dp/B0F89WH1KY"


def _ranked():
    return [
        (Product("asin:B0F89WH1KY", "EarFun Clip", asin="B0F89WH1KY", brand="EarFun"),
         Score("asin:B0F89WH1KY", mention_count=2, source_count=2, author_count=2, top_rank_count=1)),
        (Product("name:x", "ルンバ"), Score("name:x", 1, 1, 1)),
        (Product("name:y", "A|B"), Score("name:y", 1, 1, 1)),
    ]


def test_Markdownのランキング表を出力する():
    md = render_markdown(_ranked(), year=2025, source_count=10)
    assert md.startswith("# 2025年 買ってよかったものランキング")
    assert "10件のソース" in md
    assert "| 1 | [EarFun Clip](https://www.amazon.co.jp/dp/B0F89WH1KY) | EarFun | 2 | 2 | 1 |" in md


def test_同じ成績の商品は同じ順位になる():
    md = render_markdown(_ranked(), year=2025, source_count=10)
    assert "| 2 | ルンバ |" in md
    assert "| 2 | A\\|B |" in md  # 表を壊す記号はエスケープする


def test_参加表記を末尾に出力する():
    md = render_markdown(_ranked(), year=2025, source_count=10, tag="mytag-22",
                         disclosure="Amazonのアソシエイトとして収入を得ています。")
    assert md.rstrip().endswith("Amazonのアソシエイトとして収入を得ています。")


def test_記事内の他人のタグではなく指定したタグでリンクを作る():
    # Product には ASIN しか持たせないので、出力リンクは常に自分のタグになる
    md = render_markdown(_ranked(), year=2025, source_count=10, tag="mytag-22")
    assert "dp/B0F89WH1KY?tag=mytag-22" in md


def test_出典の一覧を出力する():
    from korekae.models import Source

    sources = [Source(id="s1", url="https://a.example/", title="Aさんの2025年ベストバイ")]
    md = render_markdown(_ranked(), year=2025, source_count=1, sources=sources)
    assert "## 出典" in md
    assert "- [Aさんの2025年ベストバイ](https://a.example/)" in md
