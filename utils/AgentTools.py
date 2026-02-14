from langchain.schema import HumanMessage, AIMessage
from langchain.tools import Tool
import constants.AgentToolsDoc as atd

#
# AgentToolを作るクラス
# カテゴリごとにツールを作ります。
#
class AgentTools:
    def __init__(self, stress_rag_chain, meals_rag_chain, exercise_rag_chain, general_rag_chain):
        self.stress_rag_chain = stress_rag_chain
        self.meals_rag_chain = meals_rag_chain
        self.exercise_rag_chain = exercise_rag_chain
        self.general_rag_chain = general_rag_chain

        # Toolごとの会話履歴
        self.stress_history = []
        self.meals_history = []
        self.exercise_history = []
        self.general_history = []

    def _invoke_chain(self, chain, chain_history: list, question: str) -> str:
        ai_msg = chain.invoke({"input": question, "chat_history": chain_history})
        chain_history.extend([HumanMessage(content=question), AIMessage(content=ai_msg["answer"])])
        return ai_msg["answer"]

    def build_tools(self) -> list:
        stress_doc_tool = Tool.from_function(
            func=lambda param: self._invoke_chain(self.stress_rag_chain, self.stress_history, param),
            name=atd.STRESS_DOC_NAME,
            description=atd.STRESS_DOC_DESC,
        )

        meals_doc_tool = Tool.from_function(
            func=lambda param: self._invoke_chain(self.meals_rag_chain, self.meals_history, param),
            name=atd.MEALS_DOC_NAME,
            description=atd.MEALS_DOC_DESC,
        )

        exercise_doc_tool = Tool.from_function(
            func=lambda param: self._invoke_chain(self.exercise_rag_chain, self.exercise_history, param),
            name=atd.EXERCISE_DOC_NAME,
            description=atd.EXERCISE_DOC_DESC,
        )

        general_doc_tool = Tool.from_function(
            func=lambda param: self._invoke_chain(self.general_rag_chain, self.general_history, param),
            name=atd.GENERAL_DOC_NAME,
            description=atd.GENERAL_DOC_DESC,
        )

        return [stress_doc_tool, meals_doc_tool, exercise_doc_tool, general_doc_tool]
