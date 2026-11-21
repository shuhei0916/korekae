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
uv run korekae candidates add --year 2025 --via hatena found.tsv  # 見つけた記事URL（URL<TAB>タイトル）を候補に追加
uv run korekae ingest --year 2025 batch.txt                       # 読んだ結果（SOURCE/MENTION/SKIP 行）を取り込む
uv run korekae status --year 2025                                 # 候補と抽出の進み具合
uv run korekae run --year 2025                                    # output/2025/ranking.md ができる
uv run pytest                                                     # テスト
```

アソシエイトIDと参加表記は `config/<年>.toml` の `[affiliate]` に書きます。
出力するAmazonリンクは記事内のリンクを使わず、ASINと自分のIDから作り直すので、記事の筆者のIDが混ざることはありません。

翌年は `config/2025.toml` をコピーして `config/2026.toml` を作り、`--year 2026` で同じ手順を回します。
