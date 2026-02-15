from db.DBManager import DBManager

#
# 当日の健康データを登録または更新するクラス
#
#
class DailyHealthUpsertManager(DBManager):
    def execute_query(self, params: dict):
        self.cursor.execute(
            """
            INSERT INTO kyo.daily_helth
              (uid, record_at, meal, kcal, carbo, lipid, protein, sleep_hours, water_ml, exercise, stress, mood,
               created_user, created_at, updated_user, updated_at)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, NOW())
            ON CONFLICT (uid, record_at)
            DO UPDATE SET
              meal = EXCLUDED.meal,
              kcal = EXCLUDED.kcal,
              carbo = EXCLUDED.carbo,
              lipid = EXCLUDED.lipid,
              protein = EXCLUDED.protein,
              sleep_hours = EXCLUDED.sleep_hours,
              water_ml = EXCLUDED.water_ml,
              exercise = EXCLUDED.exercise,
              stress = EXCLUDED.stress,
              mood = EXCLUDED.mood,
              updated_user = EXCLUDED.updated_user,
              updated_at = NOW()
            """,
            (
                params["uid"],
                params["record_at"],
                params["meal"],
                params["kcal"],
                params["carbo"],
                params["lipid"],
                params["protein"],
                params["sleep_hours"],
                params["water_ml"],
                params["exercise"],
                params["stress"],
                params["mood"],
                params["created_user"],
                params["updated_user"],
            ),
        )
        return {"uid": params["uid"], "record_at": params["record_at"]}
