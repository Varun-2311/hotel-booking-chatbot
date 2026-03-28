"""
rag_pipeline.py — document ingestion and retrieval

Supports: PDF (.pdf) and plain text (.txt) files.

Flow:
  file bytes → extract text → chunk → embed (sentence-transformers)
             → FAISS index stored in st.session_state

Query:
  user question → embed → FAISS similarity search → top-k chunks → context string

Auto-ingest:
  auto_ingest_docs() is called at startup from main.py.
  It reads every file in the /docs directory and builds the initial index
  so the assistant has hotel knowledge before any user uploads anything.
  Users can still upload additional PDFs to extend the knowledge base.
"""

import io
import re
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
import streamlit as st
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from app.config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL

DOCS_DIR = Path(__file__).parent.parent / "docs"


# ── Model loading ─────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def load_embedding_model() -> SentenceTransformer:
    """
    Load once and cache for the entire server lifetime.
    @st.cache_resource is shared across all users and survives re-runs,
    so the 80 MB model is only downloaded/loaded once.
    """
    return SentenceTransformer(EMBEDDING_MODEL)


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF given its raw bytes."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())


def extract_text_from_txt(txt_bytes: bytes) -> str:
    """Decode a plain text file, trying UTF-8 then latin-1 as fallback."""
    try:
        return txt_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return txt_bytes.decode("latin-1")


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route to the right extractor based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext == ".txt":
        return extract_text_from_txt(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Prefer section-aware chunks first, then fall back to overlapping slices.
    This preserves hotel list items such as room rates and policies more reliably.
    """
    normalized = text.strip()
    if not normalized:
        return []

    section_chunks: list[str] = []
    parts = re.split(r"\n(?=[A-Z][A-Z /&()-]{3,}\n[-=]{3,})", normalized)
    for part in parts:
        block = part.strip()
        if not block:
            continue
        if len(block) <= chunk_size + 150:
            section_chunks.append(block)
            continue

        start = 0
        while start < len(block):
            chunk = block[start : start + chunk_size].strip()
            if chunk:
                section_chunks.append(chunk)
            start += chunk_size - overlap

    return section_chunks


# ── Index building ────────────────────────────────────────────────────────────

def build_index(chunks: list[str], model: SentenceTransformer) -> faiss.IndexFlatL2:
    """
    Embed all chunks and build a FAISS L2 index.
    IndexFlatL2 = brute-force exact search — correct for small corpora.
    """
    embeddings = model.encode(chunks, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index


def _store_index(chunks: list[str], index: faiss.IndexFlatL2) -> None:
    """Write the built index into session_state."""
    st.session_state["rag_chunks"] = chunks
    st.session_state["rag_index"]  = index
    st.session_state["rag_ready"]  = True


# ── Auto-ingest (called at startup) ──────────────────────────────────────────

def auto_ingest_docs() -> None:
    """
    Read every .pdf and .txt file in the /docs directory and build the initial
    FAISS index. Runs silently at startup — no spinner, no user action needed.

    Only runs once per session (guarded by rag_ready flag). If the user later
    uploads additional files via the sidebar, ingest_uploaded_files() rebuilds
    the index combining docs/ files AND the uploads.
    """
    if st.session_state.get("rag_ready"):
        return  # Already indexed this session

    supported = [".pdf", ".txt"]
    doc_files = [f for f in DOCS_DIR.iterdir() if f.suffix.lower() in supported]

    if not doc_files:
        return  # No bundled docs — user must upload manually

    model = load_embedding_model()
    all_chunks: list[str] = []

    for doc_path in doc_files:
        try:
            text = extract_text(doc_path.read_bytes(), doc_path.name)
            all_chunks.extend(chunk_text(text))
        except Exception:
            pass  # Skip unreadable files silently at startup

    if all_chunks:
        _store_index(all_chunks, build_index(all_chunks, model))


# ── Manual upload ingest (called from sidebar) ────────────────────────────────

def ingest_uploaded_files(uploaded_files: list) -> None:
    """
    Called when the user uploads files via the Streamlit uploader.
    Combines bundled docs/ content with the uploads so nothing is lost.
    Rebuilds the FAISS index from scratch.
    """
    model = load_embedding_model()
    all_chunks: list[str] = []

    # Re-include the bundled docs so they stay in the index
    supported = [".pdf", ".txt"]
    for doc_path in DOCS_DIR.iterdir():
        if doc_path.suffix.lower() in supported:
            try:
                text = extract_text(doc_path.read_bytes(), doc_path.name)
                all_chunks.extend(chunk_text(text))
            except Exception:
                pass

    # Add the user-uploaded files
    for f in uploaded_files:
        try:
            text = extract_text(f.read(), f.name)
            all_chunks.extend(chunk_text(text))
        except Exception as e:
            st.warning(f"Could not parse {f.name}: {e}")

    if not all_chunks:
        st.error("No text could be extracted from the documents.")
        return

    _store_index(all_chunks, build_index(all_chunks, model))


# Keep backward-compatible alias so main.py sidebar still works
ingest_pdfs = ingest_uploaded_files


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(query: str, top_k: int = 4) -> Optional[str]:
    """
    Embed the query and return the top_k most relevant chunks joined as a
    context string. Returns None if the index is not ready yet.
    """
    if not st.session_state.get("rag_ready"):
        return None

    model  = load_embedding_model()
    index  = st.session_state["rag_index"]
    chunks = st.session_state["rag_chunks"]

    q_vec = np.array(model.encode([query], show_progress_bar=False), dtype="float32")
    _, indices = index.search(q_vec, min(max(top_k * 3, 6), len(chunks)))
    candidates = [chunks[i] for i in indices[0] if i < len(chunks)]

    query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))

    def rerank_score(chunk: str) -> tuple[int, int]:
        chunk_terms = set(re.findall(r"[a-z0-9]+", chunk.lower()))
        overlap = len(query_terms & chunk_terms)
        exact_rate_hint = int("rate" in query.lower() and "rate:" in chunk.lower())
        return (exact_rate_hint, overlap)

    results = sorted(candidates, key=rerank_score, reverse=True)[:top_k]

    if not results:
        return None

    return "\n\n".join(f"[Excerpt {i+1}]\n{c}" for i, c in enumerate(results))
