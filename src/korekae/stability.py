"""ランキングの飽和判定。

記事が100件増えるごとに上位N件のスナップショットを撮り、前回との重なりを数える。
重なりが基準以上の回が2回続いたら、それ以上記事を足しても上位はほぼ変わらないとみなす。
"""

STEP = 100


def overlap(previous: list[str], current: list[str]) -> int:
    return len(set(previous) & set(current))


def due_snapshot(source_count: int, taken: list[int]) -> bool:
    last = max(taken) if taken else 0
    if not taken:
        return source_count >= STEP
    return source_count >= last + STEP


def judge(overlaps: list[int], threshold: int) -> bool:
    return len(overlaps) >= 2 and all(o >= threshold for o in overlaps[-2:])
