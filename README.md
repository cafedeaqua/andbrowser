# andbrowser.com 公開データの保存

2026-10-22にHTTP側の公開WordPressから収集しました。HTTPS側はサーバーの初期ページだったため使用していません。

## 保存内容

- `archive/raw/`: 取得したレスポンス本文を変更せず保存。ファイル名とURLの対応は `archive/manifest.json`。
- `archive/articles.json`: 記事225件のURL、タイトル、本文HTML、本文テキスト。
- `archive/articles/`: 記事ごとのテキスト（Markdown形式）。本文の装飾や画像はJSONのHTMLと元データを参照。
- `archive/pages.json`: サイトマップから追加取得した固定ページ4件。
- `archive/errors.json`: 取得できなかったURLと理由。
- `archive/verification.json`: サイトマップとの照合結果と静的ファイル内の参照検査。
- `static-site/`: 公開ページと同一ドメインの画像・CSS等を配置し、内部参照をローカルへ変更した閲覧用コピー。

サイトマップ掲載223 URLはすべて取得済み。リンク巡回も含めて1,348 URLを保存しました（約161 MB）。同一ドメインの画像477 URLを含みます。旧リンク等110 URLは取得できず、未取得一覧に記録しています。

## ローカルで閲覧

```powershell
python -m http.server 8000 --directory static-site
```

ブラウザーで http://localhost:8000/ を開きます。内部リンクがルートからのパスのためHTMLファイルの直接ダブルクリックではなくHTTPサーバーを使ってください。

## 制約

公開ページの保存であり、WordPressデータベース・非公開記事・下書き・管理設定のバックアップではありません。外部サイトの画像や埋め込みは保存対象外で、リンク元の提供状況に依存します。取得した元HTMLは `archive/raw/` に保持しています。

閲覧用コピーではWordPress依存の検索・コメント送信フォームを案内文に変更し、インラインおよび外部スクリプトを除去しました。旧来の表示・埋め込みが変わる可能性があるため、そのまま本番公開する前に表示確認と公開用の整理が必要です。既存のコメント本文は元HTMLに残っています。

## 再生成

```powershell
python -m pip install beautifulsoup4
python scrape.py
python export_archive.py
python verify_archive.py
```

`scrape.py` は同一ホストの公開リンクを巡回し、取得済み成功レスポンスを再利用します。`sitemap-urls.json` は今回のサイトマップから抽出した一覧です。`--fill` を付けると既存記録を再巡回せず、未記録URLを補完します。

ドメイン変更、DNS変更、本番公開、旧サーバー解約は行っていません。
# andbrowser
