# ===========================
#　相談チャットのプロンプト
# ===========================
SYSTEM_MESSAGE = """
あなたは、{jobs}です。
{purpose}を目的とし、
{category}について利用者の１週間の健康状態を元にユーザーの入力に応じて相談をしてください。

# 利用者の1週間健康状態
  - 食事
    {meal}
  - 睡眠時間
    {sleep}h
  - 水分
    {water}ml
  - ストレス度(0:最小 / 5:最大)
    {stress}
  - 今日の気分
    {mood}
"""
# ヘルスケアカウンセラー 
# メンタルヘルスアドバイザー (ストレス度が高い場合)
# 栄養管理士/食育アドバイザー
# 理学療法士/作業療法士
# 用途に応じて追加する

#RAG基本データ
DAILY_RAG_BASE_DATA="[日付:%s] [category: %s] [uid: %s]"

#ストレスに関するアドバイス
DAILY_STRESS_RAG="睡眠時間: %sh / ストレスレベル: %s (最大:5) / 今日の気分: %s / 運動内容: %s"

#食事のアドバイス
DAILY_MEAL_RAG="食事内容:%s / 水分量: %sml"

#運動のアドバイス
DAILY_EXERCISE_RAG="睡眠時間: %sh / 水分量: %sml / 運動内容: %s"

#その他のアドバイス
DAILY_GENERAL_RAG="食事内容:%s / 睡眠時間: %sh / 水分量: %sml / ストレスレベル: %s (最大:5) / 今日の気分: %s / 運動内容: %s"

#
CATEGORY_STRESS=1
CATEGORY_MEAL=2
CATEGORY_EXERCICE=3
CATEGORY_GENERAL=4