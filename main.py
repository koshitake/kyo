# codename:kyo
import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentType, initialize_agent

from utils.NutrientsLLM import NutrientsLLM
from utils.HelthCareLLM import HelthCareLLM
from utils.AgentTools import AgentTools
from utils.TodayRagSaver import TodayRagSaver

import constants.PurposeOfUse as pou
import constants.ChatOpenAI as co
from LoadHelthData import LoadHelthData
from db.CategoryMasterQueryManager import CategoryMasterQueryManager
from db.DailyHealthUpsertManager import DailyHealthUpsertManager
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

def get_auth_user() -> dict:
    # 将来の認証連携では、ログイン後に st.session_state["auth_user"] を設定してください。
    # 例: {"oauth_provider": "...", "oauth_subject": "..."}
    #st.session_state["auth_user"] = {
    #"oauth_provider": "...",
    #"oauth_subject": "...",
    #}

    session_auth_user = st.session_state.get("auth_user")
    if session_auth_user is not None:
        return session_auth_user

    return {
        "oauth_provider": os.getenv("APP_OAUTH_PROVIDER", "google"),
        "oauth_subject": os.getenv("APP_OAUTH_SUBJECT", "1"),
    }

auth_user = get_auth_user()

#-------------
# 初期化処理
#-------------
if not "initialized" in st.session_state : 
    with st.spinner("読み込み中です。しばらくお待ちください..."):
        st.session_state.initialized = True
        init = LoadHelthData()
        init_result = init.run(auth_user=auth_user)
        st.session_state.today_health_data = init_result["dbdata"]
        st.session_state.selected_record_at = str(init_result["dbdata"]["date"])
        rag_chains = init_result["rag_chains"]
        for chain_name, chain in rag_chains.items():
            st.session_state[chain_name] = chain

# ===========================
# 描画処理
# ===========================
st.title("kyo")
st.subheader("カレンダー")
today = st.date_input("日付")
selected_record_at = today.isoformat()

if st.session_state.get("selected_record_at") != selected_record_at:
    with st.spinner("指定日のデータを読み込み中です..."):
        init = LoadHelthData()
        selected_dbdata = init.load_daily_health_data(
            auth_user=auth_user,
            record_at=selected_record_at,
        )

        if selected_dbdata is None:
            current_data = st.session_state.get("today_health_data", {})
            st.session_state.today_health_data = {
                "uid": current_data.get("uid"),
                "date": selected_record_at,
                "meal": "",
                "kcal": 0,
                "carbo": 0,
                "lipid": 0,
                "protein": 0,
                "sleep_hour": 0.0,
                "water": 0,
                "stress_level": 0,
                "mood": "",
                "exercise": "",
            }
            st.warning(f"{selected_record_at} のデータはまだありません。")
        else:
            st.session_state.today_health_data = selected_dbdata

        st.session_state.selected_record_at = selected_record_at


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
today_health_data = st.session_state.get("today_health_data", {})

default_breakfast = ""
default_lunch = ""
default_dinner = ""
default_snack = ""

meal_text = today_health_data.get("meal")
if meal_text is not None:
    meal_text = str(meal_text)

    # 例: 朝:パンケーキ/昼:パスタ/夜:鍋料理/間食:ケーキ
    normalized_meal_text = (
        meal_text.replace(" 昼:", "/昼:")
        .replace(" 夜:", "/夜:")
        .replace(" 間食:", "/間食:")
    )

    meal_parts = normalized_meal_text.split("/")
    for meal_part in meal_parts:
        if ":" not in meal_part:
            continue

        meal_key, meal_value = meal_part.split(":", 1)
        meal_key = meal_key.strip()
        meal_value = meal_value.strip()

        if meal_key == "朝":
            default_breakfast = meal_value
        elif meal_key == "昼":
            default_lunch = meal_value
        elif meal_key == "夜":
            default_dinner = meal_value
        elif meal_key == "間食":
            default_snack = meal_value

breakfast = st.text_input("朝", value=default_breakfast, placeholder="例: ごはんと卵")
lunch = st.text_input("昼", value=default_lunch, placeholder="例: サンドイッチ")
dinner = st.text_input("夜", value=default_dinner, placeholder="例: 鶏肉と野菜")
snack = st.text_input("間食・飲み物など", value=default_snack, placeholder="例: ナッツ")

meal = f"""
        Breakfast:{breakfast}
        Lunch:{lunch}
        Dinner:{dinner}
        eating between meals:{snack}
        """

if "nutrients_result" not in st.session_state:
    st.session_state.nutrients_result = None

if st.button("栄養素を計算する"):
    with st.spinner("計算しています..."):
        # LLM
        nl = NutrientsLLM()
        result = nl.get_nutrients(meal)
        st.session_state.nutrients_result = result
        st.write(
            f'カロリー:{result.kcal}kcal / 炭水化物:{result.carbo}g / 脂質:{result.lipid}g / タンパク質:{result.protein}g'
        )
        # アドバイス用にセッションに保管する。
        # データの保存をする

st.write(f"■厚生労働省が定めている１日の目安[カロリー:2,200〜2,500kcal / 炭水化物:250〜350g / 脂質:44〜67g / タンパク質:65〜100g]") 

# ===========================
# 日々の体調の入力
# ===========================
default_sleep_hour = today_health_data.get("sleep_hour")
if default_sleep_hour is None:
    default_sleep_hour = 0.0
default_sleep_hour = float(default_sleep_hour)

default_water = today_health_data.get("water")
if default_water is None:
    default_water = 0
default_water = int(default_water)

default_exercise = today_health_data.get("exercise")
if default_exercise is None:
    default_exercise = ""

default_stress = today_health_data.get("stress_level")
if default_stress is None:
    default_stress = 0
default_stress = int(default_stress)

default_mood = today_health_data.get("mood")
if default_mood is None:
    default_mood = ""

st.subheader("睡眠時間(入力)")
sleep_hours = st.number_input("睡眠時間(時間)", min_value=0.0, max_value=24.0, step=0.5, value=default_sleep_hour)

st.subheader("水分")
water_ml = st.number_input("水分量(ml)", min_value=0, max_value=5000, step=100, value=default_water)

st.subheader("運動")
exercise = st.text_input("運動内容", value=default_exercise, placeholder="例: ランニング20分")

st.subheader("今日のストレス度")
stress_options = [0, 1, 2, 3, 4, 5]
stress_index = 0
if default_stress in stress_options:
    stress_index = stress_options.index(default_stress)
stress = st.selectbox("ストレス度(0-5)", stress_options, index=stress_index)

st.subheader("今日の気分")
mood = st.text_input("気分", value=default_mood, placeholder="例: 今日はだるい 肩が凝っている")


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

#------------------------
# 保存処理
#------------------------
if st.button("保存する"):
    with st.spinner("保存しています..."):
        record_at = today.isoformat()

        uid = st.session_state.today_health_data["uid"]
        meal_for_db = f"朝:{breakfast}/昼:{lunch}/夜:{dinner}/間食:{snack}"

        nutrients_result = st.session_state.get("nutrients_result")
        if nutrients_result is not None:
            kcal = int(nutrients_result.kcal)
            carbo = float(nutrients_result.carbo)
            lipid = float(nutrients_result.lipid)
            protein = float(nutrients_result.protein)
        else:
            kcal = int(today_health_data.get("kcal") or 0)
            carbo = float(today_health_data.get("carbo") or 0)
            lipid = float(today_health_data.get("lipid") or 0)
            protein = float(today_health_data.get("protein") or 0)

        upsert_params = {
            "uid": uid,
            "record_at": record_at,
            "meal": meal_for_db,
            "kcal": kcal,
            "carbo": carbo,
            "lipid": lipid,
            "protein": protein,
            "sleep_hours": float(sleep_hours),
            "water_ml": int(water_ml),
            "exercise": exercise,
            "stress": int(stress),
            "mood": mood,
            "created_user": "system",
            "updated_user": "system",
        }
        daily_health_upsert_manager = DailyHealthUpsertManager()
        daily_health_upsert_manager.query(upsert_params)

        save_dbdata = {
            "uid": uid,
            "date": record_at,
            "meal": meal_for_db,
            "kcal": kcal,
            "carbo": carbo,
            "lipid": lipid,
            "protein": protein,
            "sleep_hour": float(sleep_hours),
            "water": int(water_ml),
            "stress_level": int(stress),
            "mood": mood,
            "exercise": exercise,
        }

        category_master_query_manager = CategoryMasterQueryManager()
        category_rows = category_master_query_manager.query()
        category_map = {}
        for row in category_rows:
            category_map[str(row["name"]).lower()] = row["category_id"]

        today_rag_saver = TodayRagSaver()
        for category_name in ["stress", "meals", "exercise", "general"]:
            category_id = category_map[category_name]
            today_rag_saver.save(category_name, category_id, save_dbdata)

        st.session_state.today_health_data = save_dbdata
        st.success("保存しました。")


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

    required_chain_names = [
        "stress_rag_chain",
        "meals_rag_chain",
        "exercise_rag_chain",
        "general_rag_chain",
    ]
    missing_chain_names = []
    for chain_name in required_chain_names:
        if chain_name not in st.session_state:
            missing_chain_names.append(chain_name)

    if missing_chain_names:
        message = "RAGデータが未作成です。先に「保存する」を押してデータを作成してください。"
        with st.chat_message("assistant"):
            st.markdown(message)
        st.session_state.chat_history.append({"role": "assistant", "content": message})
        st.stop()

    agent_tools = AgentTools(
        st.session_state.stress_rag_chain,
        st.session_state.meals_rag_chain,
        st.session_state.exercise_rag_chain,
        st.session_state.general_rag_chain,
    )
    tools = agent_tools.build_tools()
    llm = ChatOpenAI(model_name=co.MODEL_NAME, temperature=co.TEMPERATURE)

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
