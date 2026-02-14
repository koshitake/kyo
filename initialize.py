from utils.MonthlyRagLoader import MonthlyRagLoader
from utils.RagRetrieverChainBuilder import RagRetrieverChainBuilder
from utils.TodayRagSaver import TodayRagSaver
from db.CategoryMasterQueryManager import CategoryMasterQueryManager
from db.DailyHealthQueryManager import DailyHealthQueryManager
from datetime import date
from langchain.retrievers import MergerRetriever


#
# 初期処理のクラス
#
class Initialize:
    def __init__(self):
        self.category_map = self._load_category_map()

    def _load_category_map(self) -> dict:
        cqm = CategoryMasterQueryManager()
        rows = cqm.query()
        category_map = {}
        for row in rows:
            category_map[row["name"].lower()] = row["category_id"]
        return category_map

    def _get_category_id(self, category_name: str) -> int:
        key = category_name.lower()
        if key not in self.category_map:
            available = ", ".join(sorted(self.category_map.keys()))
            raise ValueError(f"category_master に '{category_name}' がありません。利用可能: {available}")
        return self.category_map[key]

    #
    # 当日のRAGの登録と、RAGのデータを読み込みます。
    # 
    # 
    def load_rag_data(self, dbdata: dict):
        rag_chains = {}
        categories = ["stress", "meals", "exercise", "general"]
        today_rag_saver = TodayRagSaver()
        monthly_loader = MonthlyRagLoader()
        chain_builder = RagRetrieverChainBuilder()

        try:
            for category_name in categories:
                category_id = self._get_category_id(category_name)

                # 1. 当日RAG更新
                today_rag_data = today_rag_saver.save(category_name, category_id, dbdata)

                # 2. 1ヶ月分のRAG読み込み
                rag_data = monthly_loader.load(
                    uid=dbdata["uid"],
                    category_id=category_id,
                    base_date=dbdata["date"],
                    category_name=category_name,
                )

                # 当日しかない場合はそのデータだけ使う
                if rag_data is None:
                    retriever = today_rag_data["retriever"]
                else:
                    # 1ヶ月分のデータがあれば当日のデータと付け合わせる
                    retriever = MergerRetriever(retrievers=[today_rag_data["retriever"], rag_data["retriever"]])

                # 3. Retriever chain 作成
                rag_chain = chain_builder.build(retriever)
                rag_chains[f"{category_name}_rag_chain"] = rag_chain

            return rag_chains
        except Exception as e:
            print(f"Failed to connect: {e}")

    def run(self, oauth_provider: str, oauth_subject: str):
        # 今日の日付を取得
        record_at = date.today().isoformat()

        # 1. 今日の健康データを取得
        daily_health_query_manager = DailyHealthQueryManager()
        daily_health_row = daily_health_query_manager.query(oauth_provider, oauth_subject, record_at)
        if daily_health_row is None:
            raise ValueError(f"対象日の健康データがありません: {record_at}")

        dbdata = {
            "uid": daily_health_row[0],
            "date": daily_health_row[3],
            "meal": daily_health_row[4],
            "water": daily_health_row[5],
            "sleep_hour": daily_health_row[9],
            "stress_level": daily_health_row[10],
            "mood": daily_health_row[11],
            "exercise": daily_health_row[12],
        }

        # 2. 今日のRAG更新 + 3. 1ヶ月分RAG読み込み
        rag_chains = self.load_rag_data(dbdata)
        return {"dbdata": dbdata, "rag_chains": rag_chains}
