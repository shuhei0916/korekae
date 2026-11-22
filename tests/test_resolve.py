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


def test_手で補ったASINは同じ名前の言及すべてに当てる():
    from korekae.models import Mention
    from korekae.resolve import resolve

    ms = [Mention(source_id="s1", name="AirPods Pro 3", brand="Apple"),
          Mention(source_id="s2", name="Apple AirPods Pro 3")]
    r = resolve(ms, asin_overrides={"name:appleairpodspro3": "b0fqxxxxxx"})
    assert r.product_ids == ["asin:B0FQXXXXXX", "asin:B0FQXXXXXX"]


def test_手で指定した統合先の商品に別ASINの言及をまとめる():
    mentions = [
        m("s1", "Nintendo Switch 2", brand="Nintendo", amazon_url="https://www.amazon.co.jp/dp/B0G3SXHCLJ"),
        m("s2", "任天堂 Nintendo Switch 2", brand="任天堂", amazon_url="https://www.amazon.co.jp/dp/B0FNC43RBM"),
        m("s3", "任天堂 Switch2", brand="任天堂"),
    ]
    merges = {"asin:B0FNC43RBM": "asin:B0G3SXHCLJ", "name:任天堂switch2": "asin:B0FNC43RBM"}
    result = resolve(mentions, merges=merges)
    assert [p.id for p in result.products] == ["asin:B0G3SXHCLJ"]
    assert result.product_ids == ["asin:B0G3SXHCLJ"] * 3
    assert result.products[0].asin == "B0G3SXHCLJ"


def test_ブランド付きの同じ商品名なら色違いなどで別ASINでも多いほうのASINにまとめる():
    result = resolve([
        m("s1", "Apple iPhone 17 Pro", brand="Apple", amazon_url="https://www.amazon.co.jp/dp/B0FQFPCFYH"),
        m("s2", "Apple iPhone 17 Pro", brand="Apple", amazon_url="https://www.amazon.co.jp/dp/B0FQFY14WC"),
        m("s3", "Apple iPhone 17 Pro", brand="Apple", amazon_url="https://www.amazon.co.jp/dp/B0FQFY14WC"),
    ])
    assert [p.id for p in result.products] == ["asin:B0FQFY14WC"]


def test_ブランドのない一般名は別ASINならまとめない():
    result = resolve([
        m("s1", "ノートパソコンスタンド", amazon_url="https://www.amazon.co.jp/dp/B0CPHX4R58"),
        m("s2", "ノートパソコンスタンド", amazon_url="https://www.amazon.co.jp/dp/B0F8QL6M12"),
    ])
    assert len(result.products) == 2
