import os
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

from utils.RagProcessor import RagProcessor
from db.DailyRagUpsertManager import DailyRagUpsertManager
import constants.ConsulationHelth as ch


class Initialize:
    

    #
    # RAGのデータ
    # 
    def load_rag_data(self, category_name:str, dbdata: dict):

        base_data=f"{category_name}:{ch.DAILY_RAG_BASE_DATA % (dbdata['date'], category_name, dbdata['uid'])}"

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

        try:
            print(rag_text)
            #RAGとRetriver-------------------
            rag_processor = RagProcessor()
            rag_data = rag_processor.process_text(rag_text,category_name)
            # 生データ
            chunk_texts = rag_data["chunk_texts"]
            # vectorデータ
            vectors = rag_data["vectors"]
            print(f"split_pages count: {rag_data['chunk_count']}")
            print(chunk_texts)
            #DBへ保存する
            drqm = DailyRagUpsertManager()
            rag_result = drqm.query(
                user_id=dbdata["uid"],
                category_id=ch.CATEGORY_STRESS,
                record_at=dbdata["date"],
                rag_text=rag_text,
                chunk_texts=chunk_texts,
                vectors=vectors,
                model=rag_data["model"],
                created_user="system",
            )
            print(f"RAG saved: {rag_result}")

            #会話履歴とRAGをふくめRetriversを作成
            question_generator_template = "会話履歴と最新の入力をもとに、会話履歴なしでも理解できる独立した入力テキストを生成してください。"
            question_generator_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", question_generator_template),
                    MessagesPlaceholder("chat_history"),
                    ("human", "{input}"),
                ]
            )
            llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7)
            history_aware_retriever = create_history_aware_retriever(
                llm, rag_data["retriever"], question_generator_prompt
            )
            question_answer_template = """
            あなたは優秀な質問応答アシスタントです。以下のcontextを使用して質問に答えてください。
            必ず学習したデータを見て解答をしてください
            また、答えが分からない場合は、無理に答えようとせず「分からない」という旨を答えてください。"

            {context}
            """
            question_answer_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", question_answer_template),
                    MessagesPlaceholder("chat_history"),
                    ("human", "{input}"),
                ]
            )
            question_answer_chain = create_stuff_documents_chain(llm, question_answer_prompt)
            rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
            print(rag_chain)
            return rag_chain
        except Exception as e:
            print(f"Failed to connect: {e}")