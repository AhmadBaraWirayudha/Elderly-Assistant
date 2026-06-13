
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from config import GEMINI_API_KEY, GEMINI_MODELS, KB_PATH, FAISS_PATH, MAX_HISTORY

def _embeddings():
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GEMINI_API_KEY,
    )

def load_vectorstore():
    emb = _embeddings()
    if os.path.exists(FAISS_PATH):
        return FAISS.load_local(FAISS_PATH, emb, allow_dangerous_deserialization=True)
    loader = DirectoryLoader(KB_PATH, glob="**/*.txt", loader_cls=TextLoader)
    docs = loader.load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)
    vs = FAISS.from_documents(chunks, emb)
    vs.save_local(FAISS_PATH)
    return vs

def get_retrieval_score(query: str, vectorstore) -> float:
    """Returns a [0,1] relevance score for routing."""
    results = vectorstore.similarity_search_with_relevance_scores(query, k=1)
    if not results:
        return 0.0
    _, score = results[0]
    return float(score)

def build_chain(model_key: str = "flash"):
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODELS[model_key],
        google_api_key=GEMINI_API_KEY,
        streaming=True,
        temperature=0.3,
    )
    vs = load_vectorstore()
    retriever = vs.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"score_threshold": 0.4, "k": 3},
    )
    memory = ConversationBufferWindowMemory(
        k=MAX_HISTORY,
        memory_key="chat_history",
        return_messages=True,
        output_key="answer",
    )
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True,
    )
    return chain, vs
