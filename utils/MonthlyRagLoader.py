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
        history_rag_text_list = []
        for row in monthly_rags:
            history_rag_text_list.append(row["rag_text"])
        history_rag_text = "\n".join(history_rag_text_list)

        if history_rag_text:
            print(f"monthly rag count: {len(monthly_rags)}")
            return rag_processor.process_text(history_rag_text, f"{category_name}_history")

        print("monthly rag count: 0")
        return None
