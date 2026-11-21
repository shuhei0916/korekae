from korekae.asin import extract_asin


def test_dp形式のURLからASINを取り出せる():
    assert extract_asin("https://www.amazon.co.jp/dp/B0CHX1W1XY") == "B0CHX1W1XY"
