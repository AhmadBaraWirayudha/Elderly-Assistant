from __future__ import annotations

import os
from dataclasses import dataclass
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
import os
from config import GEMINI_API_KEY, GEMINI_MODELS, KB_PATH, FAISS_PATH, MAX_HISTORY

@dataclass
class RetrievedContext:
    text: str
    score: float
    sources: list[str]

def embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def _embeddings():
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GEMINI_API_KEY,
    )

def load_vectorstore(force_rebuild: bool = False) -> FAISS:
    emb = _embeddings()
    
    if os.path.exists(FAISS_PATH) and not force_rebuild:
        return FAISS.load_local(FAISS_PATH, emb, allow_dangerous_deserialization=True)
    loader = DirectoryLoader(KB_PATH, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"}, show_progress=True, use_multithreading=False,)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=120)
    chunks = splitter.split_documents(docs)
    vs = FAISS.from_documents(chunks, emb)
    os.makedirs(FAISS_PATH, exist_ok=True)
    vs.save_local(FAISS_PATH)
    return vs

def get_retrieval_score(query: str, vectorstore: FAISS) -> float:
    """Returns a [0,1] relevance score for routing."""
    try:
        results = vectorstore.similarity_search_with_relevance_scores(query, k=1)
        if not results:
            return 0.0
        _, score = results[0]
        return float(score)
     except Exception:
        return 0.0

def retrieve_context(query: str, vectorstore: FAISS, k: int = 3) -> RetrievedContext:
    try:
        docs = vectorstore.similarity_search_with_relevance_scores(query, k=k)
    except Exception:
        return RetrievedContext(text="", score=0.0, sources=[])

    if not docs:
        return RetrievedContext(text="", score=0.0, sources=[])

    lines: list[str] = []
    sources: list[str] = []
    top_score = 0.0

    for doc, score in docs:
        top_score = max(top_score, float(score))
        source_name = doc.metadata.get("source", "kb") if hasattr(doc, "metadata") else "kb"
        sources.append(str(source_name))
        snippet = doc.page_content.strip()
        lines.append(f"[{source_name} | score={float(score):.2f}] {snippet}")

    return RetrievedContext(text="\n\n".join(lines), score=top_score, sources=sources)

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
