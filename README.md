# korekae
「買ってよかったものリスト」を網羅的に探索し、一つにまとめることで究極の「買ってよかったものリスト」を作成します。

## 仕組み

```
収集（記事を探す） → 抽出（商品を書き出す） → 名寄せ → 集計 → 出力
```

- 抽出はClaudeが記事を読んで `data/<年>/mentions.jsonl` に書き出します（ルール: [docs/extraction.md](docs/extraction.md)）。
- 名寄せ以降は `korekae run` が行います。ASIN（Amazonの商品ID）を最優先に、なければ正規化した商品名で同じ商品をまとめます。
- 集計結果は公開形式に依存しない `products.jsonl` / `scores.jsonl` に残し、そこからランキングなどを出力します。

## 使い方

```sh
uv sync
uv run korekae run --year 2025 --tag <アソシエイトタグ>   # output/2025/ranking.md ができる
uv run pytest                                            # テスト
```

翌年は `data/2026/` に sources.jsonl と mentions.jsonl を用意して `--year 2026` で実行します。
