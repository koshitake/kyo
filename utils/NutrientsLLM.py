from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from models.NutrientsModel import NutrientsModel
import constants.ChatOpenAI as ctchat
import constants.Nutrients as ctn

#
# 栄養素のLLM
#
class NutrientsLLM:

    #
    # 食事から栄養素を返すLLM
    #   
    def get_nutrients(self, meal:str):
        # RAG+ChatPromptTemplateで数値を取得する(RAGはまだ未実装)
        llm = ChatOpenAI(
                model_name=ctchat.MODEL_NAME, 
                temperature=ctchat.TEMPERATURE
                )
        output_parser = PydanticOutputParser(pydantic_object=NutrientsModel)
        format_instruction = output_parser.get_format_instructions()
        #print(format_instruction)

        prompt = PromptTemplate(
                input_variables=["context"],
                template=ctn.SYSTEM_PROMPT_CREATE_INDEPENDENT_TEXT,
                partial_variables={"format_instruction": format_instruction},
        )
        
        messages = [
            SystemMessage(content=ctn.DEFAULT_SYSTEM_MESSAGE),
            HumanMessage(content=prompt.format(context=meal)),
        ]

        output = llm(messages)
        #print(output.content)
        result = output_parser.parse(output.content)
        #print(result)
        return result
