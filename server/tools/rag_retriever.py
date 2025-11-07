# server/tools/rag_retriever.py
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from server.config import CHROMA_DIR, OPENAI_API_KEY


def build_chroma_from_texts(texts: list[str], persist_dir: str = CHROMA_DIR):
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=50)
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    vectordb = Chroma.from_texts(chunks, embeddings, persist_directory=persist_dir)
    vectordb.persist()
    return vectordb


def retrieve(query: str, k: int = 3, persist_dir: str = CHROMA_DIR):
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    vectordb = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    results = vectordb.similarity_search(query, k=k)
    return results
