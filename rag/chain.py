from __future__ import annotations

import os
from dataclasses import dataclass

import config
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_classic.chains import create_retrieval_chain               
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import GEMINI_API_KEY, GEMINI_MODELS, KB_PATH, FAISS_PATH, MAX_HISTORY

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a warm, caring assistant helping elderly people.

Rules you must always follow:
- Use short, simple sentences. Maximum 4 sentences by default.
- Speak plainly — no jargon, no medical diagnoses.
- If someone asks about a medication, only read what is written on the label or in the knowledge base. Never prescribe doses.
- If you are not sure, say so kindly and suggest they ask a family member or doctor.
- Be patient and reassuring. Never make the person feel confused or rushed.

Use this context from the personal knowledge base when relevant:
{context}"""


@dataclass
class RetrievedContext:
    text: str
    score: float
    sources: list[str]


# ── Embeddings & vectorstore ──────────────────────────────────────────────────

def _embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=config.GEMINI_API_KEY,
    )


def load_vectorstore(force_rebuild: bool = False) -> FAISS:
    """Load existing FAISS index or build it from KB documents."""
    emb = _embeddings()

    if os.path.exists(FAISS_PATH) and not force_rebuild:
        try:
            return FAISS.load_local(
                FAISS_PATH, emb, allow_dangerous_deserialization=True
            )
        except Exception:
            pass  # Fall through and rebuild

    os.makedirs(KB_PATH, exist_ok=True)
    loader = DirectoryLoader(
        KB_PATH,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
        use_multithreading=False,
        silent_errors=True,
    )
    docs = loader.load()

    if not docs:
        docs = [Document(
            page_content=(
                "This is an empty knowledge base. "
                "Add .txt files to the rag/kb/ folder to personalise the assistant."
            ),
            metadata={"source": "system"},
        )]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    vs = FAISS.from_documents(chunks, emb)
    vs.save_local(FAISS_PATH)          # FIX: was called twice
    return vs


def get_retrieval_score(query: str, vectorstore: FAISS) -> float:
    """Return a [0, 1] relevance score for router decisions."""
    try:
        results = vectorstore.similarity_search_with_relevance_scores(query, k=1)
        if not results:
            return 0.0
        _, score = results[0]
        return float(max(0.0, min(1.0, score)))
    except Exception:                  # FIX: had extra leading space → IndentationError
        return 0.5


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


# ── Chain builder ─────────────────────────────────────────────────────────────

def build_chain(model_key: str = "flash"):
    print("model_key =", model_key)
    print("model =", config.GEMINI_MODELS[model_key])
    """Return (rag_chain, vectorstore). Call again when model_key changes."""
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODELS[model_key],
        google_api_key=config.GEMINI_API_KEY,
        streaming=True,
        temperature=0.3,
    )

    vs = load_vectorstore()
    retriever = vs.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "score_threshold": config.RETRIEVAL_THRESHOLD,
            "k": config.RETRIEVAL_K,
        },
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    qa_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, qa_chain)

    return rag_chain, vs
    # FIX: removed all dead code that was here (old ConversationalRetrievalChain block
    # with unclosed parenthesis — this caused a SyntaxError because
    # `def to_lcel_history` appeared inside the unclosed `(`)


# ── History helpers ───────────────────────────────────────────────────────────

def to_lcel_history(history: list) -> list:
    """Convert [(query, answer), ...] to LangChain message objects."""
    messages = []
    for q, a in history[-config.MAX_HISTORY:]:
        messages.append(HumanMessage(content=q))
        messages.append(AIMessage(content=a))
    return messages
    # FIX: removed orphaned `)` and `return chain, vs` that were here
