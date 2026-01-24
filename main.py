# codename:kyo
import streamlit as st
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from utils.NutrientsLLM import NutrientsLLM
from utils.HelthCareLLM import HelthCareLLM
import constants.ChatOpenAI as ctchat
import constants.HelthCare as hc
import constants.PurposeOfUse as pou
#
# main処理
#
load_dotenv()

#
# 描画処理
#
st.title("kyo")
st.subheader("カレンダー")
today = st.date_input("日付")

st.subheader("利用目的")
purpose = st.radio(
    "利用目的を選択",
    ["ゆるめのダイエット", "体調・健康", "本格的な健康管理"],
)
PROMPT_PURPOSE=pou.POU_DIET
if purpose == "ゆるめのダイエット":
    PROMPT_PURPOSE=pou.POU_DIET
elif purpose == "体調・健康":
    PROMPT_PURPOSE=pou.POU_HELTH
else :
    PROMPT_PURPOSE=pou.POU_PREMIUM_HELTH

st.subheader("食事")
breakfast = st.text_input("朝", placeholder="例: ごはんと卵")
lunch = st.text_input("昼", placeholder="例: サンドイッチ")
dinner = st.text_input("夜", placeholder="例: 鶏肉と野菜")
snack = st.text_input("間食・飲み物など", placeholder="例: ナッツ")

meal = f"""
        Breakfast:{breakfast}
        Lunch:{lunch}
        Dinner:{dinner}
        eating between meals]{snack}
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

st.subheader("今日のAIアドバイス")
if st.button("今日のAIアドバイスを聞く"):
    with st.spinner("アドバイスを生成しています..."):
        # 今日の記録を入力した状態を元にアドバイスを生成する
        # 何度も作り直すことができる。
        # 履歴は保存しない
        # 結果を表示
        # 目的に応じて返答方法を分ける
        print(sleep_hours)
        print(water_ml)
        print(exercise)
        print(stress)
        print(mood)
        print(meal)
        
        hcllm = HelthCareLLM()
        msg = hcllm.get_daily_helthCare(
            PROMPT_PURPOSE,
            meal,
            sleep_hours,
            water_ml,
            stress,
            mood
        )
        st.write(msg)

st.subheader("相談チャット")
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if st.session_state.chat_history:
    st.write("履歴")
    for q, a in st.session_state.chat_history:
        st.write(f"Q: {q}")
        st.write(f"A: {a}")

question = st.text_input("質問を入力")
if st.button("送信") and question:
    # TODO:会話履歴を記録したRAGでLLMを生成する
    answer = "今は簡易版のため、ここに回答が表示されます。"
    st.session_state.chat_history.append((question, answer))

st.subheader("入力内容の確認")
st.write(
    {
        "日付": str(today),
        "利用目的": purpose,
        "食事": {"朝": breakfast, "昼": lunch, "夜": dinner, "間食": snack},
        "睡眠時間(時間)": sleep_hours,
        "水分量(ml)": water_ml,
        "運動": exercise,
        "ストレス度": stress,
        "気分": mood,
    }
)
