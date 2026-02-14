from db.DBManager import DBManager

#
# カテゴリの読み込みSQL
# 
class CategoryMasterQueryManager(DBManager):
    def execute_query(self):
        self.cursor.execute(
            """
            SELECT category_id, name
            FROM kyo.category_master
            ORDER BY category_id
            """,
        )
        rows = self.cursor.fetchall()
        result = []
        for row in rows:
            result.append({"category_id": row[0], "name": row[1]})
        return result
