from db.DBManager import DBManager


class DailyRagSelectManager(DBManager):
    def execute_query(
        self,
        user_id: str,
        category_id: int,
        base_date,
    ):
        self.cursor.execute(
            """
            SELECT record_at, rag_text
            FROM kyo.daily_rag_sources
            WHERE uid = %s
              AND category_id = %s
              AND record_at >= date_trunc('month', %s::date)::date
              AND record_at < (date_trunc('month', %s::date) + INTERVAL '1 month')::date
            ORDER BY record_at ASC
            """,
            (user_id, category_id, base_date, base_date),
        )
        rows = self.cursor.fetchall()
        return [{"record_at": row[0], "rag_text": row[1]} for row in rows]
