from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import constants.ChatOpenAI as ctchat
import constants.HelthCare as hc
import constants.Restrictions as rt
from utils.TikToken import TikToken as tt
#
# AIアドバイス
#
class HelthCareLLM:

    #
    # 今日のAIアドバイスを取得する
    #
    #
    def get_daily_helthCare(self,purpose:str, meal:str, sleep_hours:str, water_ml:str, stress:str, mood:str):
        
        llm = ChatOpenAI(
                model_name=ctchat.MODEL_NAME, 
                temperature=ctchat.TEMPERATURE
                )

        prompt = PromptTemplate(
                input_variables=["purpose","meal","sleep","water","stress","mood","restrictions"],
                template=hc.SYSTEM_PROMPT_CREATE_INDEPENDENT_TEXT,
        )

        message = prompt.format(
                    purpose=purpose,
                    meal=meal,
                    sleep=sleep_hours,
                    water=water_ml,
                    stress=stress,
                    mood=mood,
                    restrictions=rt.SYSTEM_RESTRICTIONS_WORD
                )
            
        messages = [
            SystemMessage(content=ctchat.DEFAULT_SYSTEM_MESSAGE),
            HumanMessage(content=message),
        ]
        # ざっくりToken
        print(message)
        print(tt.getTokenLength(ctchat.DEFAULT_SYSTEM_MESSAGE))
        print(tt.getTokenLength(message))

        result = llm(messages)
        print(result)
        return result.content