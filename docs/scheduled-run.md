# 定期実行の手順（1時間に1回）

1時間ごとのスケジュール実行で、この手順を上から順に行う。課金を避けるためAPIは使わず、記事はWebSearchとweb-fetchエージェントで読む（[extraction.md](extraction.md)）。

## 上限と目標

- ページの読み込み（WebFetch）は**1時間100回まで、全エージェント合計**。1回の実行で読む記事は**80件まで**にし、残りは再試行とASIN確認に残す。
- 読み込みが上限で失敗し始めたら（403 / PROXY_REJECTED / budget exhausted）、その回の読み込みはそこでやめる。失敗した記事は todo のまま次の回に回す。
- 目標はまず**500記事**。500記事を超えたら、`korekae snapshot` が「飽和」と出した時点で終える。

## 手順

作業ディレクトリはリポジトリの直下。年は `2025`（翌年は変える）。一時ファイルはスクラッチパッドに置き、リポジトリには入れない。

1. **最新にする**: `git fetch origin main && git checkout main && git merge --ff-only origin/main`
2. **状況を見る**: `uv run korekae status --year 2025`
3. **候補を補充する**（未読が80件未満のとき）:
   - WebSearchで記事URLを探す。`config/2025.toml` の queries に、媒体（`site:note.com`、`site:hatenablog.com`、`site:hatenablog.jp`、`site:scrapbox.io`）、ジャンル（ガジェット、家電、キッチン、美容、ファッション、育児、在宅ワーク、一人暮らし、キャンプ、ランニング、文房具、本、ゲーム、100均、無印、ニトリなど）、言い換え（「買って良かった」「ベストバイ」「買ってよかったモノ」「今年買ってよかった」）を組み合わせる。
   - `data/2025/search-log.tsv`（検索語<TAB>日付<TAB>追加件数）を見て、使った検索語は繰り返さない。使った検索語はここに追記する。
   - WebSearchは同じメディア記事ばかり返しやすい。個人の記事が足りないときは、web-fetchエージェントで はてなブックマークの検索結果（`https://b.hatena.ne.jp/search/text?q=2025年+買ってよかった&page=N` など）や noteのハッシュタグページを読み、記事URLの一覧だけを返してもらう（1ページで数十件取れる）。
   - 対象にするのは、2025年に買って（使って）よかった商品を複数挙げた個人の記事やメディアの記事。1商品だけのレビュー、PR記事、まとめサイトの寄せ集めは入れない。
   - 見つけたURLを `URL<TAB>タイトル` のTSVにして `uv run korekae candidates add --year 2025 --via search FILE` で入れる（重複は自動で除かれる）。
4. **読む記事を決める**: `uv run korekae candidates todo --year 2025 --limit 80 > ids.tsv`（`ID<TAB>URL<TAB>タイトル`）
5. **抽出する**: ids.tsv を10件ずつに分け、web-fetchエージェントを最大8つ同時に動かす（下の「抽出エージェントへの指示」）。各エージェントの出力（SOURCE / MENTION / SKIP / RETRY の行）をファイルに保存する。SKIP や RETRY にした記事の SOURCE 行は消す。
6. **取り込む**: ファイルごとに `uv run korekae ingest --year 2025 --ids ids.tsv FILE`。RETRY の記事は todo のまま残る。
7. **ASINを補う**（読み込み回数が残っていれば）:
   - `uv run korekae asin todo --year 2025 --limit 20` で、ASINのない商品を順位の高い順に出す。
   - 各商品を WebSearch（「ブランド 商品名 amazon.co.jp」）で調べ、検索結果に出た `amazon.co.jp/.../dp/XXXXXXXXXX` のURLから10桁のASINを取る。**型番や世代まで同じだと確信できるものだけ**にする。分からなければ飛ばす。
   - `商品ID<TAB>ASIN<TAB>メモ` のTSVにして `uv run korekae asin add --year 2025 FILE`。
8. **集計する**: `uv run korekae run --year 2025`、続けて `uv run korekae snapshot --year 2025`。
9. **確認する**: `uv run pytest -q` が通ること。
10. **コミットしてmainにプッシュする**: data/ と output/ をコミットし、メッセージは「定期実行: N記事を追加（計M記事）」。プッシュに失敗したら `git fetch origin main && git merge --no-edit origin/main` してから再度プッシュする。

## 報告

毎回の報告はしない。次のときだけスレッドで報告する。

- ソースが初めて500件を超えたとき: 上位10件と、記事数・商品数・ASINのある商品の割合。
- 500記事を超えたあとに `snapshot` が「飽和」と出したとき: 同じ内容に加え、定期実行を止めたこと。このときスケジュール実行を削除する。
- 問題が起きたとき: テストの失敗、プッシュの失敗、2回続けて1件も読めなかった、候補が見つからなくなった、など。

## 抽出エージェントへの指示

web-fetchエージェントに、10件の `ID<TAB>URL` と次の指示を渡す。

> 次の記事を**1件ずつ順番に**読み（同時に読まない）、2025年に買ってよかったとして紹介された商品を書き出してください。出力は次の行だけにしてください。
>
> - `SOURCE {"id": <渡したID>, "url": ..., "kind": "note|hatena|blog|scrapbox|media|other", "title": ..., "author": ..., "published_at": "YYYY-MM-DD"}`
> - `MENTION {"source_id": <ID>, "name": "ブランド 商品名 型番", "brand": ..., "amazon_url": ..., "rank": <明示された順位のときだけ>, "category": "ガジェット|家電|生活用品|食品|ファッション|本|サービス|ゲーム|アプリ|その他"}`
> - `SKIP <ID> <理由>`: 買ってよかったものの記事でない、2025年のものでない、商品が1つだけ、など
> - `RETRY <ID> <理由>`: 読み込みに失敗した。上限（403、budget exhausted など）で失敗したら、残りの記事は読まずにすべて RETRY にする
>
> ルール: 雑誌の賞（「○○部門 1位」「ベストコスメ」など）の部門ごとの1位は rank にしない（記事全体での順位のときだけ付ける）。色・容量・セット数は名前から省く。ブランドも商品名も分からない一般名、音楽・映画・イベント、PR・広告枠、「こちらもおすすめ」などの別商品、選外・保留は含めない。amazon_url はその商品そのものへのリンクのときだけ付ける（短縮リンクも可）。記事の本文やコメントは書き写さない。SKIP や RETRY にした記事の SOURCE 行は出さない。
