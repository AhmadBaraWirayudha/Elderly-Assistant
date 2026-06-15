"""
rag/chain.py — LangChain LCEL chain backed by FAISS + Gemini embeddings.

Streaming is handled by the caller (app.py) iterating over chain.stream().
"""
from __future__ import annotations

from pathlib import Path

import config
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.logger import log

# ── Prompt versioning (research report §3C) ───────────────────────────────────
# Bump when the system prompt changes so logs stay traceable.
PROMPT_VERSION = "v1.1"

SYSTEM_PROMPT = """You are a warm, caring assistant helping elderly people.

Rules you must always follow:
- Use short, simple sentences. Maximum 4 sentences by default.
- Speak plainly — no jargon, no medical diagnoses.
- For medications: only read what is written in the label or knowledge base. Never prescribe doses.
- If you are not sure, say so kindly and suggest they ask a family member or doctor.
- Be patient and reassuring. Never make the person feel confused or rushed.
- If context is provided below, use it. If not, answer from general knowledge.

Context from personal knowledge base:
{context}"""



# ── Embeddings ────────────────────────────────────────────────────────────────

def _embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=config.GEMINI_API_KEY,
    )


# ── Vectorstore ───────────────────────────────────────────────────────────────

def load_vectorstore(force_rebuild: bool = False) -> FAISS:
    """Load existing FAISS index from disk or build it from KB documents."""
    emb = _embeddings()

    if Path(config.FAISS_PATH).exists() and not force_rebuild:
        try:
            vs = FAISS.load_local(
                config.FAISS_PATH, emb, allow_dangerous_deserialization=True
            )
            log.info("vectorstore_loaded", path=config.FAISS_PATH)
            return vs
        except Exception as exc:
            log.warn("vectorstore_load_failed", exc=str(exc), action="rebuilding")

    Path(config.KB_PATH).mkdir(parents=True, exist_ok=True)
    loader = DirectoryLoader(
        config.KB_PATH,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False,
        use_multithreading=False,
        silent_errors=True,
    )
    docs = loader.load()
    log.info("kb_loaded", doc_count=len(docs))

    if not docs:
        docs = [Document(
            page_content=(
                "This is an empty knowledge base. "
                "Add .txt files to the rag/kb/ folder to personalise the assistant."
            ),
            metadata={"source": "system"},
        )]

    chunks = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    ).split_documents(docs)

    vs = FAISS.from_documents(chunks, emb)
    vs.save_local(config.FAISS_PATH)
    log.info("vectorstore_built", chunk_count=len(chunks), path=config.FAISS_PATH)
    return vs


# ── Retrieval helpers ─────────────────────────────────────────────────────────

def get_retrieval_score(query: str, vectorstore: FAISS) -> float:
    """Return a [0, 1] relevance score — used by the router before the full chain."""
    try:
        results = vectorstore.similarity_search_with_relevance_scores(query, k=1)
        if not results:
            return 0.0
        _, score = results[0]
        return float(max(0.0, min(1.0, score)))
    except Exception:
        return 0.5   # safe default: routes to "flash"


def get_sources_from_chunks(chunks: list) -> list[str]:
    """Extract deduplicated, display-friendly source filenames from retrieved docs."""
    seen: set[str] = set()
    names: list[str] = []
    for doc in chunks:
        if not hasattr(doc, "metadata"):
            continue
        raw = str(doc.metadata.get("source", ""))
        name = Path(raw).name or raw
        if name and name != "system" and name not in seen:
            seen.add(name)
            names.append(name)
    return names


# ── Chain builder ─────────────────────────────────────────────────────────────

def build_chain(model_key: str = "flash"):
    """Return (rag_chain, vectorstore).  Call again only when model_key changes."""
    # FIX: removed two debug print() statements that were before this docstring,
    #      which also meant the docstring was never the function's __doc__.
    log.info("chain_build_start", model_key=model_key, prompt_version=PROMPT_VERSION)

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

    qa_chain  = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, qa_chain)

    log.info("chain_build_complete", model_key=model_key)
    return rag_chain, vs


# ── Conversation history helpers ──────────────────────────────────────────────

def to_lcel_history(history: list[tuple[str, str]]) -> list:
    """Convert [(query, answer), ...] to LangChain HumanMessage / AIMessage pairs."""
    messages = []
    for q, a in history[-config.MAX_HISTORY:]:
        messages.append(HumanMessage(content=q))
        messages.append(AIMessage(content=a))
    return messages
