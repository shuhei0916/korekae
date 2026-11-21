"""名寄せ: 言及（Mention）を商品（Product）にまとめる。

まとめ方の優先順位:
1. ASIN（amazon_url から取り出したもの、または手で補った asin 項目）
2. 正規化した商品名。同名のASIN付き商品があればそちらに合流する
"""

from collections import Counter
from dataclasses import dataclass

from .asin import extract_asin
from .models import Mention, Product
from .normalize import normalize_name


@dataclass
class ResolveResult:
    products: list[Product]
    product_ids: list[str]  # mentions と同じ順序で、各言及が属する商品ID


def mention_asin(mention: Mention) -> str | None:
    if mention.asin:
        return mention.asin.upper()
    return extract_asin(mention.amazon_url) if mention.amazon_url else None


def name_key(mention: Mention) -> str:
    """名前による名寄せキー。商品名にブランドが含まれなければ前に付ける。

    「ワイドパンツ」のような一般名が、ブランド違いでまとまらないようにするため。
    """
    name = normalize_name(mention.name)
    brand = normalize_name(mention.brand or "")
    if brand and brand not in name:
        return brand + name
    return name


def resolve(mentions: list[Mention]) -> ResolveResult:
    # 名前 → ASIN の対応表（ASINなしの言及を合流させるため）
    asin_by_name: dict[str, str] = {}
    for mention in mentions:
        asin = mention_asin(mention)
        if asin:
            asin_by_name.setdefault(name_key(mention), asin)

    product_ids = []
    for mention in mentions:
        asin = mention_asin(mention) or asin_by_name.get(name_key(mention))
        product_ids.append(f"asin:{asin}" if asin else f"name:{name_key(mention)}")

    groups: dict[str, list[Mention]] = {}
    for pid, mention in zip(product_ids, mentions):
        groups.setdefault(pid, []).append(mention)

    products = [_build_product(pid, ms) for pid, ms in sorted(groups.items())]
    return ResolveResult(products=products, product_ids=product_ids)


def _most_common(values: list[str | None]) -> str | None:
    counted = Counter(v for v in values if v)
    return counted.most_common(1)[0][0] if counted else None


def _build_product(pid: str, mentions: list[Mention]) -> Product:
    name = _most_common([m.name for m in mentions])
    aliases = sorted({m.name for m in mentions} - {name})
    return Product(
        id=pid,
        name=name or "",
        asin=pid.removeprefix("asin:") if pid.startswith("asin:") else None,
        brand=_most_common([m.brand for m in mentions]),
        category=_most_common([m.category for m in mentions]),
        aliases=aliases,
    )
