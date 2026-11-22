"""名寄せ: 言及（Mention）を商品（Product）にまとめる。

まとめ方の優先順位:
1. ASIN（amazon_url から取り出したもの、または手で補った asin 項目）
2. 正規化した商品名。同名のASIN付き商品があればそちらに合流する
   （ブランド付きの同名なら、色違いなどで別ASINの言及も最も多いASINにまとめる）
3. merges で手で指定した統合先
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


def resolve(
    mentions: list[Mention],
    asin_overrides: dict[str, str] | None = None,
    merges: dict[str, str] | None = None,
) -> ResolveResult:
    """asin_overrides は「name:<名寄せキー>」→ ASIN の対応（短縮リンクなどでASINが取れない商品を手で補う）。

    merges は商品ID → 統合先の商品ID の対応（セット違いなどで別ASINになった同じ商品を手でまとめる）。
    統合先がさらに統合されていればたどる。
    """
    # 名前 → ASIN の対応表（ASINなしの言及を合流させるため）
    asin_by_name: dict[str, str] = {
        k.removeprefix("name:"): v.upper() for k, v in (asin_overrides or {}).items()
    }
    asin_counts: dict[str, Counter] = {}
    for mention in mentions:
        asin = mention_asin(mention)
        if asin:
            asin_counts.setdefault(name_key(mention), Counter())[asin] += 1
    for key, counts in asin_counts.items():
        # 言及の多いASINを代表にする（同数なら辞書順で先のもの）
        best = min(counts, key=lambda a: (-counts[a], a))
        asin_by_name.setdefault(key, best)

    product_ids = []
    for mention in mentions:
        asin = mention_asin(mention)
        if mention.brand and asin_by_name.get(name_key(mention)):
            # ブランド付きで同じ名前なら、色違いなどで別ASINでも1つにまとめる
            asin = asin_by_name[name_key(mention)]
        asin = asin or asin_by_name.get(name_key(mention))
        product_ids.append(_follow(merges or {}, f"asin:{asin}" if asin else f"name:{name_key(mention)}"))

    groups: dict[str, list[Mention]] = {}
    for pid, mention in zip(product_ids, mentions):
        groups.setdefault(pid, []).append(mention)

    products = [_build_product(pid, ms) for pid, ms in sorted(groups.items())]
    return ResolveResult(products=products, product_ids=product_ids)


def _follow(merges: dict[str, str], pid: str) -> str:
    seen = {pid}
    while pid in merges and merges[pid] not in seen:
        pid = merges[pid]
        seen.add(pid)
    return pid


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
