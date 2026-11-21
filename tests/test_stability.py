from korekae.stability import due_snapshot, judge, overlap


def test_上位N件の重なりを数える():
    assert overlap(["a", "b", "c"], ["c", "a", "x"]) == 2


def test_前回から100記事増えたら次のスナップショットを撮る():
    assert due_snapshot(source_count=99, taken=[]) is False
    assert due_snapshot(source_count=105, taken=[]) is True
    assert due_snapshot(source_count=180, taken=[105]) is False
    assert due_snapshot(source_count=205, taken=[105]) is True


def test_重なりが基準以上の回が2回続けば飽和とみなす():
    assert judge([30, 46], threshold=45) is False
    assert judge([46, 44], threshold=45) is False
    assert judge([40, 45, 47], threshold=45) is True
    assert judge([], threshold=45) is False
