import pytest

from korekae.normalize import normalize_name


def test_全角英数字と半角の表記ゆれを同一視する():
    assert normalize_name("ＡＮＫＥＲ　Ｓｏｕｎｄｃｏｒｅ") == normalize_name("Anker Soundcore")


def test_大文字小文字と空白の違いを無視する():
    assert normalize_name("AirPods Pro 2") == normalize_name("airpods  pro2")


@pytest.mark.parametrize("raw", ["「AirPods Pro 2」", "AirPods Pro 2！", "AirPods・Pro・2"])
def test_記号や括弧を無視する(raw):
    assert normalize_name(raw) == normalize_name("AirPods Pro 2")


def test_カタカナとひらがなは区別したまま残す():
    # 読みの同一視は誤統合のもとになるので行わない
    assert normalize_name("ルンバ") != normalize_name("るんば")
