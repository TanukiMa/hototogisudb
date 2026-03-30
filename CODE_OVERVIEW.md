# コードベース概要と主な懸念点

## 1. ディレクトリ構成と主要モジュール

| ディレクトリ / ファイル | 目的 | 主な実装ポイント |
|--------------------------|------|-------------------|
| **mozc4med_dict/** | アプリケーションのコアロジック | DB 接続、データモデル、インポーター・エクスポーター実装 |
| `mozc4med_dict/db.py` | Supabase クライアント取得 | `dotenv` で `.env` 読み込み、`SUPABASE_URL` と `SUPABASE_SERVICE_ROLE_KEY` を必須環境変数として取得し `create_client` を返す |
| `mozc4med_dict/models.py` | Pydantic データモデル | `PosType`, `ImportBatch`, `MozcDictEntry`（`to_tsv_line` メソッドで TSV 行生成） |
| `mozc4med_dict/utils/kana.py` | カタカナ→ひらがな正規化 | 全角スペース除去、カタカナコード範囲をひらがなへシフト |
| `mozc4med_dict/importers/` | 各 SSK マスタ CSV のインポートロジック | `BaseImporter` の共通フローに従い、SHA‑256 重複チェック、`import_batches` 登録、`_parse_rows` / `_upsert_rows` 実装 |
| `mozc4med_dict/importers/ssk_shobyomei.py` | 疾患マスタ CSV → DB | `change_type` で `is_active` を算出、`dict_enabled` は UPSERT に含めず保持 |
| `mozc4med_dict/importers/ssk_iyakuhin.py` | 薬マスタ CSV → DB | `is_generic` 判定、ブランド名とジェネリック名の 2 エントリ生成は DB 側 RPC が担当 |
| `mozc4med_dict/importers/ssk_shinryo_koi.py` | 手術マスタ CSV → DB | `abbr_*` と `base_kanji_name` を取得、同様に `dict_enabled` は変更しない |
| `mozc4med_dict/importers/csv_generic.py` | カスタム CSV → `custom_terms` テーブル | UTF‑8 で読み込み、`utils.kana.normalize_reading` で `reading` 正規化、`dict_enabled=True` を明示的にセット |
| `mozc4med_dict/exporters/mozc_system_dict.py` | DB → Mozc システム辞書 TSV エクスポート | Supabase RPC `export_mozc_dict_entries` を呼び出し、結果を `MozcDictEntry` へ変換し `dist/` に書き出す |
| **scripts/** | CLI エントリポイント | `argparse` + ロギングでインポーター・エクスポーターを呼び出し、エラーハンドリングを行う |
| **tests/** | 単体・統合テスト | ユニットは `unittest.mock` で Supabase クライアントをモックし、インテグレーションは本番/テスト用 Supabase プロジェクトへ実行 |

## 2. 主な懸念点・リスク

| カテゴリ | 懸念点 | 影響・リスク |
|----------|--------|--------------|
| **UPSERT の `dict_enabled`** | `csv_generic.py` の `on_conflict="surface_form,reading"` が文字列として渡されている | Supabase‑py が期待する「リスト」形式になっておらず、複合ユニークキーでの UPSERT が機能せず重複レコードが生成される可能性 |
| **大量レコードインポート時の原子性** | `BaseImporter.run` はバッチ登録後に一括 UPSERT を実行。失敗した場合に `import_batches` 行が残る | 中途失敗で `import_batches` に孤立レコードが残り、再実行やテーブル整合性が壊れるリスク |
| **トランザクション管理** | UPSERT を個別リクエストで実行し、失敗時にロールバックが未実装 | 大量データで途中例外が起きた場合、一部だけが DB に残り不整合になる |
| **`reading` 正規化の位置** | CSV インポーターは `kana_name` などをそのまま保存。`reading` 正規化はエクスポート側 RPC に依存 | エクスポートが正しく変換しないと、Mozc 辞書にひらがな `reading` が入らず検索・変換が失敗する可能性 |
| **エラーハンドリング** | `BaseImporter._upsert_rows` が例外を捕捉せず上位へ伝搬 | 例外が起きた際にバッチ行の削除やクリーンアップが行われず、手動での汚染除去が必要 |
| **テストカバレッジ** | `csv_generic` の `on_conflict` 仕様ミスがユニットテストで検出されていない | 実装ミスが CI で見逃され、リリース時に重複レコードが混入するリスク |
| **冪等性** | `import_batches` の SHA‑256 重複チェックはあるが、UPSERT 失敗時のクリーンアップがない | 冪等性が保証されず、再試行時に二重登録や状態不整合が起きやすい |
| **README 更新** | `README.md` の自動生成・更新ルールは CLAUDE.md に記載されているが、コード側で自動トリガーが未実装 | 変更が README に反映されず、ドキュメントと実装が乖離する可能性 |
| **パフォーマンス** | 大規模 CSV を 1 回の UPSERT で送信（`BaseImporter._upsert_rows` が全行一括） | Supabase のリクエストサイズ上限やタイムアウトに引っかかり、インポートが失敗するリスク |
| **環境変数必須化** | `db.py` が `os.environ["SUPABASE_URL"]` で即 `KeyError` を投げる | 開発環境で `.env` が欠落した際にプロセスがクラッシュし、デバッグが煩雑になる |

## 3. 優先的に対応すべき改善案

1. **`csv_generic.py` の `on_conflict` 修正**
   ```python
   client.table("custom_terms").upsert(
       rows,
       on_conflict=["surface_form", "reading"],  # リスト指定へ変更
   ).execute()
   ```
2. **UPSERT のチャンク化と失敗時クリーンアップ**
   * `CHUNK_SIZE`（例: 2000）で分割し、各チャンクを `try/except` で実行。
   * 例外時は `import_batches` の該当行を削除（または全体ロールバック）して冪等性を確保。
3. **トランザクション付き SQL 関数で一括 UPSERT**
   * 各インポーター用に `INSERT … ON CONFLICT …` を `BEGIN … COMMIT` で包む PL/pgSQL 関数を作成し、Python から `client.rpc` で呼び出す。
   * 失敗時に全体がロールバックされ、途中状態が残らない。
4. **`reading` 正規化をインポーター側へ移行**
   * `utils.kana.normalize_reading` を使用して、CSV から取得した `kana_name`/`abbr_kana_name` を `reading` カラムに変換した上で DB に保存。
   * エクスポート側での変換依存を排除し、データの一貫性を保証。
5. **テスト追加**
   * `csv_generic` の `on_conflict` がリストで渡されていることを検証するユニットテスト。
   * UPSERT 失敗シナリオで `import_batches` が削除されることを確認するテスト。
   * 大量レコード（例: 10k 行）でチャンク処理が正しく呼び出されるかのテスト。
6. **README 自動更新のフック化（任意）**
   * ファイル変更時に `claude-code` の `update-config` スキルでフックを設定し、README の自動生成を走らせる。
7. **環境変数ロードの安全化**
   * `db.py` を `os.getenv` に切り替えて、欠落時にカスタム例外メッセージを出すか、デフォルトで `None` を返すようにし、呼び出し側でハンドリングできるようにする。

---

*このファイルは `CODE_OVERVIEW.md` としてリポジトリ直下に保存しました。今後の開発・レビュー時の参照にご活用ください。*