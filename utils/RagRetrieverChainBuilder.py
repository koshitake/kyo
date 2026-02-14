from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import constants.RAGBuilder as rag
import constants.ChatOpenAI as co
#
# Retriverから履歴もわかるようにするためのretriverChaninを作るクラス
#
#
class RagRetrieverChainBuilder:
    
    
    def build(self, retriever):
        question_generator_template = rag.QUESTION_GENERATOR_TEMPLATE
        question_generator_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", question_generator_template),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        llm = ChatOpenAI(model_name=co.MODEL_NAME, temperature=co.TEMPERATURE)
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, question_generator_prompt
        )

        question_answer_template = rag.QUESTION_ANSWER_TEMPLATE
        question_answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", question_answer_template),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        question_answer_chain = create_stuff_documents_chain(llm, question_answer_prompt)
        return create_retrieval_chain(history_aware_retriever, question_answer_chain)
