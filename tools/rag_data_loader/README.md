# RAGデータ投入ツール

このツールは、`kyo` の以下テーブルにテストデータを投入します。

- `kyo.daily_helth`（日々の健康データ）
- `kyo.daily_rag_sources`（RAG化前のテキスト）
- `kyo.daily_rags`（RAG化済みチャンク）

## 対象期間

- 2026年1月（1ヶ月分）
- 2026年2月（1ヶ月分）

## 使い方

1. プロジェクトルートの `.env` に `DATABASE_URL` を設定する
2. 以下を実行する

```bash
python3 tools/rag_data_loader/load_monthly_rag_data.py --oauth-provider google --oauth-subject 1
```

実行中は `processing YYYY-MM-DD` の進捗ログが表示されます。

`--uid` を直接指定して実行することもできます（未指定時は `health_seed_config.json` の `default_uid` を使用）。

```bash
python3 tools/rag_data_loader/load_monthly_rag_data.py --uid xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

## 備考

- `daily_rags.rag_embedding_1536` には、OpenAI APIを使わない簡易ベクトル（疑似データ）を入れています。
- 既に同じ `uid + record_at` データがある場合は `ON CONFLICT` で更新されます。
