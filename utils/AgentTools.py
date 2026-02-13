from langchain.schema import HumanMessage, AIMessage
from langchain.tools import Tool


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
            name="ストレスに関する情報を参照するTool",
            description="ストレスに関する質問に関して情報を参照したい場合に使う",
        )

        meals_doc_tool = Tool.from_function(
            func=lambda param: self._invoke_chain(self.meals_rag_chain, self.meals_history, param),
            name="食事の内容関する情報を参照するTool",
            description="食事の内容や改善に関する質問に関して情報を参照したい場合に使う",
        )

        exercise_doc_tool = Tool.from_function(
            func=lambda param: self._invoke_chain(self.exercise_rag_chain, self.exercise_history, param),
            name="運動の内容に関する情報を参照するTool",
            description="運動の内容ややり方に関する質問に関して情報を参照したい場合に使う",
        )

        general_doc_tool = Tool.from_function(
            func=lambda param: self._invoke_chain(self.general_rag_chain, self.general_history, param),
            name="一般的な質問に関する情報を参照するTool",
            description="一般的な質問関して情報を参照したい場合に使う",
        )

        return [stress_doc_tool, meals_doc_tool, exercise_doc_tool, general_doc_tool]
