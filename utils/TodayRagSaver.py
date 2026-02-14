from utils.RagProcessor import RagProcessor
from db.DailyRagUpsertManager import DailyRagUpsertManager
import constants.ConsulationHelth as ch

#
# 当日の健康データをRAG化しDBに保存するクラス
#
#
class TodayRagSaver:
    # 当日のRAGを作成してDBに保存する。
    # 1カテゴリ分の登録処理を行います。
    def save(self, category_name: str, category_id: int, dbdata: dict) -> dict:
        rag_processor = RagProcessor()
        upsert_manager = DailyRagUpsertManager()

        base_data = f"{category_name}:{ch.DAILY_RAG_BASE_DATA % (dbdata['date'], category_name, dbdata['uid'])}"
        if category_name == "stress":
            rag_text = f"""
                {base_data}
                {ch.DAILY_STRESS_RAG % (dbdata["sleep_hour"], dbdata["stress_level"], dbdata["mood"], dbdata["exercise"])}
            """
        elif category_name == "meals":
            rag_text = f"""
                {base_data}
                {ch.DAILY_MEAL_RAG % (dbdata["meal"], dbdata["water"])}
            """
        elif category_name == "exercise":
            rag_text = f"""
                {base_data}
                {ch.DAILY_EXERCISE_RAG % (dbdata["sleep_hour"], dbdata["water"], dbdata["exercise"])}
            """
        else:
            rag_text = f"""
                {base_data}
                {ch.DAILY_GENERAL_RAG % (dbdata["meal"], dbdata["sleep_hour"], dbdata["water"], dbdata["stress_level"], dbdata["mood"], dbdata["exercise"])}
            """

        print(rag_text)

        rag_data = rag_processor.process_text(rag_text, category_name)
        chunk_texts = rag_data["chunk_texts"]
        vectors = rag_data["vectors"]

        print(f"split_pages count: {rag_data['chunk_count']}")
        print(chunk_texts)

        rag_upsert_param = {
            "user_id": dbdata["uid"],
            "category_id": category_id,
            "record_at": dbdata["date"],
            "rag_text": rag_text,
            "chunk_texts": chunk_texts,
            "vectors": vectors,
            "model": rag_data["model"],
            "created_user": "system",
        }
        rag_result = upsert_manager.query(rag_upsert_param)
        print(f"RAG saved: {rag_result}")
        return rag_data
