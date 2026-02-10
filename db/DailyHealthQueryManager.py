from db.DBManager import DBManager


class DailyHealthQueryManager(DBManager):
    def execute_query(self, oauth_provider: str, oauth_subject: str, record_at: str):
        self.cursor.execute(
            """
            select
                u.uid,
                u.name,
                p.name,
                h.record_at,
                h.meal,
                h.kcal,
                h.carbo,
                h.lipid,
                h.protein,
                h.sleep_hours,
                h.stress,
                h.mood,
                h.exercise,
                u.id
            from
                kyo.users as u,
                kyo.purpose_master as p,
                kyo.daily_helth as h
            where
                u.purpose = p.id and
                u.uid = h.uid and
                u.oauth_provider = %s and
                u.oauth_subject = %s and
                h.record_at = %s;
            """,
            (oauth_provider, oauth_subject, record_at),
        )
        return self.cursor.fetchone()
