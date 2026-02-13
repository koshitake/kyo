# codename:kyo
import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentType, initialize_agent

from utils.NutrientsLLM import NutrientsLLM
from utils.HelthCareLLM import HelthCareLLM
from utils.AgentTools import AgentTools
from db.DailyHealthQueryManager import DailyHealthQueryManager

import constants.PurposeOfUse as pou

from initialize import Initialize
# ===========================
# 初期処理
# ===========================
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

if not "initialized" in st.session_state : 
    st.session_state.initialized = True


    dhqm = DailyHealthQueryManager()
    result = dhqm.query('google','1','2026-02-04')

    print(result)
    print(f"日付:{result[3]}")

    init = Initialize()
    dbragdata = {
        "uid"  : result[0],
        "date" : result[3],
        "meal" : result[4],
        "water" : result[5],
        "sleep_hour" : result[9],
        "stress_level":result[10],
        "mood":result[11],
        "exercise":result[12] 
    }
    
    st.session_state.stress_rag_chain = init.load_rag_data("stress",dbragdata)
    st.session_state.meals_rag_chain = init.load_rag_data("meals",dbragdata)
    st.session_state.exercise_rag_chain = init.load_rag_data("exercise",dbragdata)
    st.session_state.general_rag_chain = init.load_rag_data("general",dbragdata)

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

# 履歴の表示
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("質問を入力")

# LLMへ質問をする
if question:
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    #---これを別クラスで再利用できるようにする--------------
    agent_tools = AgentTools(
        st.session_state.stress_rag_chain,
        st.session_state.meals_rag_chain,
        st.session_state.exercise_rag_chain,
        st.session_state.general_rag_chain,
    )
    tools = agent_tools.build_tools()
    #-------------------------ここまで

    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7)

    agent_executor = initialize_agent(
        llm=llm,
        tools=tools,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )

    with st.chat_message("assistant"):
        with st.spinner("回答を生成しています..."):
            answer = agent_executor.run(question)
        st.markdown(answer)

    print(f"回答：{answer}")
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
