# mozc4med-dict

Supabaseに医療用語（SSKマスター・カスタム語）を保存し、Mozc システム辞書 TSV としてエクスポートするデータベースシステム。

## Requirements

- Python 3.11+
- Supabase プロジェクト（本番用 + テスト用）
- SSK マスター CSV ファイルへのアクセス

## Setup

1. リポジトリをクローン
2. `.env.example` を `.env` にコピーして認証情報を入力
3. 依存関係をインストール: `pip install -e ".[dev]"`
4. Supabase プロジェクトにマイグレーションを適用 (`schema/migrations/` を順番に実行)
   - **ログイン**: `npx supabase login`（ブラウザで認証）
   - **プロジェクトリンク**: `npx supabase link --project-ref <ref>`
   - **マイグレーション適用**: `npx supabase db push`

## Importing SSK Masters

```bash
# 傷病名マスター
python scripts/import_shobyomei.py --file data/b_ALL20260325.csv --url "https://..."

# 診療行為マスター
python scripts/import_shinryo_koi.py --file data/s_ALL20260325.csv --url "https://..."

# 医薬品マスター
python scripts/import_iyakuhin.py --file data/y_ALL20260325.csv --url "https://..."

# カスタム語 CSV
python scripts/import_csv.py --file data/custom_terms.csv --source "Custom terms v1"
```

Entry points (after `pip install -e .`):

```bash
mozc4med-import-shobyomei   --file data/b_ALL20260325.csv --url "https://..."
mozc4med-import-shinryo-koi --file data/s_ALL20260325.csv --url "https://..."
mozc4med-import-iyakuhin    --file data/y_ALL20260325.csv --url "https://..."
mozc4med-import-csv         --file data/custom_terms.csv --source "Custom terms v1"
```

## Exporting the Mozc Dictionary

```bash
python scripts/export_mozc_dict.py --output dist/mozc4med_medical.txt
python scripts/export_mozc_dict.py --dry-run   # カウントのみ、ファイル出力なし

# Entry point
mozc4med-export --output dist/mozc4med_medical.txt
```

## Managing dict_enabled

```bash
# 廃止済みだが辞書に残っている語一覧
python scripts/manage_dict_enabled.py --list-abolished

# 特定コードを辞書から除外
python scripts/manage_dict_enabled.py --disable 1234567
```

## Running Tests

```bash
# ユニットテスト（ネットワーク不要）
pytest tests/unit/ -v

# 統合テスト（SUPABASE_TEST_* 環境変数が必要）
pytest tests/integration/ -v

# 全テスト
pytest -v
```

## Database Schema

テーブル構成:

| テーブル | 説明 |
|---|---|
| `pos_types` | Mozc 品詞 ID マスター |
| `import_batches` | インポート履歴（SHA-256 で重複防止） |
| `ssk_shinryo_koi` | 診療行為マスター |
| `ssk_iyakuhin` | 医薬品マスター |
| `ssk_shobyomei` | 傷病名マスター |
| `custom_terms` | カスタム・手動入力語 |

### 2フラグ設計

| フラグ | 意味 | 更新者 |
|---|---|---|
| `is_active` | SSKマスター上で現行の語 | インポーター（自動） |
| `dict_enabled` | Mozc辞書に含める | 管理者（手動） |

エクスポーターは `dict_enabled=TRUE` のみを出力。`is_active` は無視。

## GitHub Actions Workflows

| ワークフロー | トリガー | 目的 |
|---|---|---|
| `ci.yml` | PR to `main` | lint + ユニットテスト + 統合テスト |
| `export_mozc_dict.yml` | 毎週月曜 + 手動 | 辞書エクスポート、コミットバック |
| `import_ssk_master.yml` | 手動のみ | SSKマスター CSV インポート |
| `supabase_keepalive.yml` | 毎日 + 手動 | Supabase フリー枠フリーズ防止 |
| `update_changelog.yml` | `main` へのプッシュ | CHANGELOG.md 自動生成 |

## License

MIT
