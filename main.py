# codename:kyo
import streamlit as st
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage, Document
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector

from utils.NutrientsLLM import NutrientsLLM
from utils.HelthCareLLM import HelthCareLLM
import constants.ChatOpenAI as ctchat
import constants.HelthCare as hc
import constants.PurposeOfUse as pou
import constants.ConsulationHelth as cc
import psycopg2


# ===========================
# 初期処理
# ===========================
load_dotenv()

import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# ====================== 
# ConnectionTest
# ====================== 

# RAGの読み込み
# カテゴリ別に(データを読み込んで、Agentsを作成する)
# データ容量は起動の状況により調整
# 
# dailydata
# """
# {
#  date:"2025/12/01",
#  helth_data:{
#               meal:"朝：ご飯",
#               nutri:"1500kcal/炭水化物:300g/脂質:100g/タンパク質:100g", →ない時は0にする
#               sleep_hours:7.5,
#               water_ml:1500,
#               exercise:"ランニング30分",
#               stress(0-5):1,
#               mood:"元気!"},
#  }
# ""

DBURL=os.getenv("DATABASE_URL")
# Connect to the database
try:
    connection = psycopg2.connect(DBURL)
    print("Connection successful!")
    
    # Create a cursor to execute SQL queries
    cursor = connection.cursor()

    #初期ロード

    # Example query
    # oauthでユーザーをとるがとりあえず固定
    # 健康データを取得
    cursor.execute("SELECT * from kyo.users;")
    cursor.execute("""
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
        From 
            kyo.users as u,
            kyo.purpose_master as p,
            kyo.daily_helth as h
        where
            u.purpose = p.id and
            u.uid = h.uid and
            u.oauth_provider='google' and
            u.oauth_subject='1' and
            h.record_at='2026-02-04';
    """)
    result = cursor.fetchone()
    print(f"test:{result}")
    if result is None:
        raise Exception("daily_helth data not found for target date")


    # 健康データからRAGがなければ生成
    # SQLで存在チェック
    # なければRAG化
    # 生データとRAGをDBへ書き込み
    # record_at
    # category
    # uuid
    # 睡眠
    # 水分
    # ストレス
    # 気分
    # 運動

    d = cc.DAILY_RAG_BASE_DATA % ("2024-02-12", "stress", result[0])
    d2 = cc.DAILY_RAG_BASE_DATA % ("2024-02-12", "meals", result[0])
    d3 = cc.DAILY_RAG_BASE_DATA % ("2024-02-12", "exercise", result[0])
    d4 = cc.DAILY_RAG_BASE_DATA % ("2024-02-12", "general", result[0])
    
    
    s = cc.DAILY_STRESS_RAG % (result[9], result[10], result[11])
    s2 = cc.DAILY_MEAL_RAG % (result[4], result[5])
    s3 = cc.DAILY_EXERCISE_RAG % (result[9], result[5], result[12])
    s4 = cc.DAILY_GENERAL_RAG % (result[4], result[9], result[5], result[10], result[11], result[12])
    # 相談チャットのLLMに読ませる(一月分)
    aa = f"stress:{d}\n{s}"
    aa2 = f"meals:{d2}\n{s2}"
    aa3 = f"exercise:{d3}\n{s3}"
    aa4 = f"general:{d4}\n{s4}"
    print(aa)
    print(aa2)
    print(aa3)
    print(aa4)

    #RAG化
    docs = [Document(page_content=aa)]
    text_splitter = CharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separator="\n",
        )
    splitted_pages = text_splitter.split_documents(docs)
    print(f"split_pages count: {len(splitted_pages)}")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-ada-002",
    )
    # Documentオブジェクトから本文(text)だけを取り出す
    chunk_texts = []
    for chunk_doc in splitted_pages:
        chunk_texts.append(chunk_doc.page_content)

    print(chunk_texts)

    # 取り出した本文ごとにベクトル化する
    vectors = embeddings.embed_documents(chunk_texts) 
    #print(vectors)

    register_vector(connection)
    with connection:
        with connection.cursor() as cur:
            user_id = result[13]
            category_id = 1
            record_at = result[3]
            created_user = "system"

            # 元テキストを保存し、source_idを取得する
            cur.execute(
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
                (user_id, category_id, record_at, aa, created_user, created_user),
            )
            source_id = cur.fetchone()[0]

            # 再作成時の重複を防ぐ
            cur.execute("DELETE FROM kyo.daily_rags WHERE source_id = %s", (source_id,))

            rows = []
            for i, (chunk_text, vec) in enumerate(zip(chunk_texts, vectors)):
                rows.append(
                    (
                        source_id,
                        i,
                        chunk_text,
                        "text-embedding-ada-002",
                        vec,      # rag_embedding_1536
                        None,     # rag_embedding_3072
                        created_user,
                        created_user,
                    )
                )

            execute_values(
                cur,
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

    # Close the cursor and connection
    cursor.close()
    connection.close()
    print("Connection closed.")

except Exception as e:
    print(f"Failed to connect: {e}")


# ===========================
# 描画処理
# ===========================
st.title("kyo")
st.subheader("カレンダー")
today = st.date_input("日付")


# ===========================
# 利用目的ラジオボタン
# ===========================
st.subheader("利用目的")
purpose = st.radio(
    "利用目的を選択(気軽な目的だと回答は早いです)",
    ["ゆるめのダイエット", "体調・健康", "本格的な健康管理"],
)
PROMPT_PURPOSE=pou.POU_DIET
if purpose == "ゆるめのダイエット":
    PROMPT_PURPOSE=pou.POU_DIET
elif purpose == "体調・健康":
    PROMPT_PURPOSE=pou.POU_HELTH
else :
    PROMPT_PURPOSE=pou.POU_PREMIUM_HELTH


# ===========================
#  食事の入力と栄養素の計算
# ===========================
st.subheader("食事")
breakfast = st.text_input("朝", placeholder="例: ごはんと卵")
lunch = st.text_input("昼", placeholder="例: サンドイッチ")
dinner = st.text_input("夜", placeholder="例: 鶏肉と野菜")
snack = st.text_input("間食・飲み物など", placeholder="例: ナッツ")

meal = f"""
        Breakfast:{breakfast}
        Lunch:{lunch}
        Dinner:{dinner}
        eating between meals:{snack}
        """
if st.button("栄養素を計算する"):
    with st.spinner("計算しています..."):
        # LLM
        nl = NutrientsLLM()
        result = nl.get_nutrients(meal)
        st.write(
            f'カロリー:{result.kcal}kcal / 炭水化物:{result.carbo}g / 脂質:{result.lipid}g / タンパク質:{result.protein}g'
        )
        # アドバイス用にセッションに保管する。

        # データの保存をする

st.write(f"■厚生労働省が定めている１日の目安[カロリー:2,200〜2,500kcal / 炭水化物:250〜350g / 脂質:44〜67g / タンパク質:65〜100g]") 

# ===========================
# 日々の体調の入力
# ===========================
st.subheader("睡眠時間(入力)")
sleep_hours = st.number_input("睡眠時間(時間)", min_value=0.0, max_value=24.0, step=0.5)

st.subheader("水分")
water_ml = st.number_input("水分量(ml)", min_value=0, max_value=5000, step=100)

st.subheader("運動")
exercise = st.text_input("運動内容", placeholder="例: ランニング20分")

st.subheader("今日のストレス度")
stress = st.selectbox("ストレス度(0-5)", [0, 1, 2, 3, 4, 5])

st.subheader("今日の気分")
mood = st.text_input("気分", placeholder="例: 今日はだるい 肩が凝っている")


# ===========================
# 今日のAIアドバイスの生成
# ===========================
st.subheader("今日のAIアドバイス")
if st.button("今日のAIアドバイスを聞く"):
    with st.spinner("アドバイスを生成しています..."):
        print(sleep_hours)
        print(water_ml)
        print(exercise)
        print(stress)
        print(mood)
        print(meal)
        print(exercise)
        
        hcllm = HelthCareLLM()
        msg = hcllm.get_daily_helthCare(
            PROMPT_PURPOSE,
            meal,
            sleep_hours,
            water_ml,
            exercise,
            stress,
            mood,
        )
        st.write(msg)

if st.button("保存する"):
    print("保存")
    # 栄養素の内容がない時は計算
    # その日のデータをJSON化
    # DBへ保存
    # データ集計バッチが必要？
    # 一月のデータの平均値を計算
    # 1週間のデータの平均値を計算


# ===========================
# 相談チャット画面
# ===========================
st.subheader("相談チャット")
# 履歴
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

#履歴の表示
if st.session_state.chat_history:
    st.write("履歴")
    for q, a in st.session_state.chat_history:
        st.write(f"Q: {q}")
        st.write(f"A: {a}")

question = st.text_input("質問を入力")
#LLMへ質問をする
if st.button("送信") and question:
    # TODO:会話履歴を記録したRAGでLLMを生成する
    # 日次の記録を保管する(DB)
    # Agentsで専門的に特化したアドバイスを行う。
    # 利用目的に応じで回答の精度を分ける
    # 1日のデータは生データ(JSONで)
    # RAGは１ヶ月分だけデータとしてまとめる。それ以上は入れない
    # Agentsでカテゴリ別で用意しそれぞれにRAGデータを入れる
    # 過去のデータは必要に応じてRAG化する
    answer = "今は簡易版のため、ここに回答が表示されます。"
    st.session_state.chat_history.append((question, answer))

# st.subheader("入力内容の確認")
# st.write(
#     {
#         "日付": str(today),
#         "利用目的": purpose,
#         "食事": {"朝": breakfast, "昼": lunch, "夜": dinner, "間食": snack},
#         "睡眠時間(時間)": sleep_hours,
#         "水分量(ml)": water_ml,
#         "運動": exercise,
#         "ストレス度": stress,
#         "気分": mood,
#     }
# )
