from korekae.models import Mention
from korekae.resolve import resolve


def m(source_id, name, **kw):
    return Mention.from_dict({"source_id": source_id, "name": name, **kw})


def test_同じASINの言及は表記が違っても1つの商品にまとめる():
    mentions = [
        m("s1", "AirPods Pro 2", amazon_url="https://www.amazon.co.jp/dp/B0CHX1W1XY"),
        m("s2", "Apple AirPods Pro（第2世代）", amazon_url="https://www.amazon.co.jp/gp/product/B0CHX1W1XY"),
    ]
    result = resolve(mentions)
    assert len(result.products) == 1
    assert result.products[0].asin == "B0CHX1W1XY"
    assert result.product_ids == [result.products[0].id] * 2


def test_ASINがない言及は正規化した商品名でまとめる():
    result = resolve([m("s1", "ルンバ j9+"), m("s2", "ルンバ　Ｊ９＋")])
    assert len(result.products) == 1
    assert result.products[0].asin is None


def test_ASINがない言及も同名のASIN付き商品があればそちらにまとめる():
    result = resolve([
        m("s1", "Shokz OpenDots ONE", amazon_url="https://www.amazon.co.jp/dp/B0DW3RWMNM"),
        m("s2", "Shokz OpenDots ONE"),
    ])
    assert len(result.products) == 1
    assert result.products[0].asin == "B0DW3RWMNM"


def test_手で補ったasin項目もURLと同様に使う():
    result = resolve([
        m("s1", "EarFun Clip", asin="B0F89WH1KY"),
        m("s2", "イヤーファン クリップ", amazon_url="https://www.amazon.co.jp/dp/B0F89WH1KY"),
    ])
    assert len(result.products) == 1


def test_違う商品は別々の商品になる():
    result = resolve([m("s1", "iPhone 17 Pro"), m("s2", "iPhone 16e")])
    assert len(result.products) == 2


def test_代表名は最も多く使われた表記で他の表記は別名に入る():
    result = resolve([
        m("s1", "EarFun Clip", asin="B0F89WH1KY"),
        m("s2", "イヤーファン クリップ", asin="B0F89WH1KY"),
        m("s3", "EarFun Clip", asin="B0F89WH1KY", brand="EarFun"),
    ])
    product = result.products[0]
    assert product.name == "EarFun Clip"
    assert product.aliases == ["イヤーファン クリップ"]
    assert product.brand == "EarFun"


def test_商品IDは入力の順序によらず安定している():
    a = resolve([m("s1", "iPhone 16e"), m("s2", "ルンバ")])
    b = resolve([m("s2", "ルンバ"), m("s1", "iPhone 16e")])
    assert {p.id for p in a.products} == {p.id for p in b.products}


def test_ブランドが違う一般名の商品はまとめない():
    result = resolve([m("s1", "ワイドパンツ", brand="yee"), m("s2", "ワイドパンツ", brand="UNIQLO")])
    assert len(result.products) == 2


def test_商品名にブランドが含まれていればブランドの有無にかかわらずまとめる():
    result = resolve([m("s1", "SOUNDPEATS UU", brand="SOUNDPEATS"), m("s2", "SOUNDPEATS UU")])
    assert len(result.products) == 1


def test_ブランドを名前の前に付けた表記ともまとめる():
    result = resolve([m("s1", "UU", brand="SOUNDPEATS"), m("s2", "SOUNDPEATS UU")])
    assert len(result.products) == 1
