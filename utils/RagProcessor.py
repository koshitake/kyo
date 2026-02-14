from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import constants.ChatOpenAI as cc
import constants.RAGBuilder as rag

#
# RAGとRetriverを作成するクラス
#
class RagProcessor:

    def __init__(self):

        self.text_splitter = CharacterTextSplitter(
            chunk_size=cc.RAG_CHUNK_SIZE,
            chunk_overlap=cc.RAG_CHUNK_OVERLAP,
            separator=cc.RAG_SEPARATOR,
        )
        self.embeddings = OpenAIEmbeddings(model=cc.RAG_CHUNK_MODEL)

    #
    # RAGとRetriverを作成する
    # 
    def process_text(self, text: str, category: str) -> dict:
        chunk_texts = self.text_splitter.split_text(text)
        vectors = self.embeddings.embed_documents(chunk_texts)

        vectorstore = Chroma(
            collection_name=category,
            embedding_function=self.embeddings
        )

        # RAGの生データを投入
        vectorstore.add_texts(chunk_texts)
        # retrieverを作成
        retriever = vectorstore.as_retriever(search_kwargs={"k":rag.SEARCH_KWARGS})        
        
        return {
            "chunk_texts": chunk_texts,
            "vectors": vectors,
            "retriever": retriever,
            "chunk_count": len(chunk_texts),
            "model": cc.RAG_CHUNK_MODEL,
        }
