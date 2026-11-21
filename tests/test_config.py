from korekae.config import load_config


def test_設定ファイルからアソシエイトIDと参加表記を読む(tmp_path):
    path = tmp_path / "2025.toml"
    path.write_text(
        'year = 2025\n'
        'queries = ["買ってよかったもの 2025"]\n'
        '[affiliate]\n'
        'tag = "mytag-22"\n'
        'disclosure = "Amazonのアソシエイトとして収入を得ています。"\n',
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.year == 2025
    assert config.tag == "mytag-22"
    assert config.disclosure == "Amazonのアソシエイトとして収入を得ています。"
    assert config.queries == ["買ってよかったもの 2025"]


def test_タグが空ならNoneとして扱う(tmp_path):
    path = tmp_path / "2025.toml"
    path.write_text('year = 2025\n[affiliate]\ntag = ""\n', encoding="utf-8")
    config = load_config(path)
    assert config.tag is None
    assert config.disclosure is None
