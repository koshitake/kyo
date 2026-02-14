from utils.RagProcessor import RagProcessor
from db.DailyRagSelectManager import DailyRagSelectManager

#
# 一月分のRAGデータを読み込むクラス 
# 
class MonthlyRagLoader:
    # 1ヶ月分のRAGを読み込み、RAGデータを返す。
    def load( self, uid: str, category_id: int, base_date: str, category_name: str,) -> dict | None:
        select_manager = DailyRagSelectManager()
        rag_processor = RagProcessor()

        monthly_rags = select_manager.query(
            user_id=uid,
            category_id=category_id,
            base_date=base_date,
        )
        # 当日分は already 処理済みなので、月次側では除外して無駄な再計算を防ぐ
        today_date = str(base_date)
        history_rags = []
        for row in monthly_rags:
            if str(row["record_at"]) != today_date:
                history_rags.append(row)

        history_rag_text_list = []
        for row in history_rags:
            history_rag_text_list.append(row["rag_text"])
        history_rag_text = "\n".join(history_rag_text_list)

        if history_rag_text:
            print(f"monthly rag count: {len(monthly_rags)} (history only: {len(history_rags)})")
            return rag_processor.process_text(history_rag_text, f"{category_name}_history")

        print("monthly rag count: 0")
        return None
