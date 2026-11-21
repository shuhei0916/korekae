import pytest

from korekae.asin import extract_asin


def test_dp形式のURLからASINを取り出せる():
    assert extract_asin("https://www.amazon.co.jp/dp/B0CHX1W1XY") == "B0CHX1W1XY"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.amazon.co.jp/Anker-Soundcore/dp/B0CHX1W1XY/ref=sr_1_1?tag=foo-22",
        "https://www.amazon.co.jp/gp/product/B0CHX1W1XY?th=1",
        "https://amazon.co.jp/exec/obidos/ASIN/B0CHX1W1XY/foo-22/",
        "https://www.amazon.com/dp/b0chx1w1xy",
    ],
)
def test_様々な形式の商品URLからASINを取り出せる(url):
    assert extract_asin(url) == "B0CHX1W1XY"


def test_ISBN形式の10桁数字もASINとして扱う():
    assert extract_asin("https://www.amazon.co.jp/dp/4873119464") == "4873119464"


@pytest.mark.parametrize(
    "url",
    [
        "https://amzn.to/3abcXYZ",  # 短縮URLはオフラインでは展開できない
        "https://www.amazon.co.jp/s?k=イヤホン",
        "https://www.rakuten.co.jp/dp/B0CHX1W1XY",
        "",
    ],
)
def test_ASINを含まないURLではNoneを返す(url):
    assert extract_asin(url) is None
