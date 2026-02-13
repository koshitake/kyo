from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from db.DBManager import DBManager


class DailyRagUpsertManager(DBManager):
    def execute_query(
        self,
        user_id: str,
        category_id: int,
        record_at=None,
        rag_text: str = "",
        chunk_texts: list[str] | None = None,
        vectors: list[list[float]] | None = None,
        model: str = "text-embedding-ada-002",
        created_user: str = "system",
    ):
        if chunk_texts is None:
            chunk_texts = []
        if vectors is None:
            vectors = []

        register_vector(self.connection)

        # 元テキストを保存し、source_idを取得する
        self.cursor.execute(
            """
            INSERT INTO kyo.daily_rag_sources
              (uid, category_id, record_at, rag_text, created_user, created_at, updated_user, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s, NOW())
            ON CONFLICT (uid, category_id, record_at)
            DO UPDATE SET
              rag_text = EXCLUDED.rag_text,
              updated_user = EXCLUDED.updated_user,
              updated_at = NOW()
            RETURNING id
            """,
            (user_id, category_id, record_at, rag_text, created_user, created_user),
        )
        source_id = self.cursor.fetchone()[0]

        # 再作成時の重複を防ぐ
        self.cursor.execute("DELETE FROM kyo.daily_rags WHERE source_id = %s", (source_id,))

        rows = []
        for i, (chunk_text, vec) in enumerate(zip(chunk_texts, vectors)):
            rows.append(
                (
                    source_id,
                    i,
                    chunk_text,
                    model,
                    vec,
                    None,
                    created_user,
                    created_user,
                )
            )

        if rows:
            execute_values(
                self.cursor,
                """
                INSERT INTO kyo.daily_rags
                (source_id, chunk_index, chunk_text, model,
                rag_embedding_1536, rag_embedding_3072,
                created_user, created_at, updated_user, updated_at)
                VALUES %s
                """,
                rows,
                template="(%s,%s,%s,%s,%s,%s,%s,NOW(),%s,NOW())",
            )

        return {"source_id": source_id, "chunk_count": len(rows)}
