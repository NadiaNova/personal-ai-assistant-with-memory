
"""
Configuration settings for the Personal AI Assistant / RAG Chatbot.
Supports Gemini, Ollama, and optional automatic LLM fallback.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# --------------------------------------------------
# Directory configuration
# --------------------------------------------------

PDF_DIR = BASE_DIR / "pdfFiles"
VECTOR_DB_DIR = BASE_DIR / "vectorDB"

PDF_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# LLM provider configuration
# --------------------------------------------------

# Primary provider: "gemini" or "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))


# --------------------------------------------------
# Google Gemini configuration
# --------------------------------------------------

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
).strip()


# --------------------------------------------------
# Ollama configuration
# --------------------------------------------------

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:3b",
).strip()

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
).strip()


# --------------------------------------------------
# Automatic fallback configuration
# --------------------------------------------------

ENABLE_LLM_FALLBACK = (
    os.getenv("ENABLE_LLM_FALLBACK", "true").strip().lower()
    in ("true", "1", "yes", "on")
)

FALLBACK_PROVIDER = os.getenv(
    "FALLBACK_PROVIDER",
    "ollama",
).strip().lower()


# --------------------------------------------------
# Embedding configuration
# --------------------------------------------------

# Used for PDF and long-term memory semantic search.
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "nomic-embed-text:latest",
).strip()


# --------------------------------------------------
# Backwards-compatible aliases
# --------------------------------------------------

LLM_MODEL = (
    GEMINI_MODEL
    if LLM_PROVIDER == "gemini"
    else OLLAMA_MODEL
)

LLM_BASE_URL = OLLAMA_BASE_URL


# --------------------------------------------------
# Document processing configuration
# --------------------------------------------------

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


# --------------------------------------------------
# Vector database configuration
# --------------------------------------------------

CHROMA_PERSIST_DIR = str(VECTOR_DB_DIR)
COLLECTION_NAME = "pdf_documents"


# --------------------------------------------------
# Streamlit configuration
# --------------------------------------------------

PAGE_TITLE = "Personal AI Assistant with Memory"
PAGE_ICON = "🤖"
PAGE_LAYOUT = "wide"


# --------------------------------------------------
# Session state keys
# --------------------------------------------------

SESSION_MESSAGES = "messages"
SESSION_VECTOR_STORE = "vector_store"
SESSION_CONVERSATION_CHAIN = "conversation_chain"


# --------------------------------------------------
# UI messages
# --------------------------------------------------

WELCOME_MESSAGE = (
    "Your personal knowledge, ready to explore. "
    "Ask questions on anything or about your documents."
)

UPLOAD_PROMPT = "Upload a PDF file to start asking questions."

PROCESSING_MESSAGE = "Processing your PDF... Please wait."

SUCCESS_MESSAGE = (
    "PDF processed successfully! You can now ask questions."
)

ERROR_MESSAGE = "An error occurred: {}"


# --------------------------------------------------
# ChromaDB telemetry
# --------------------------------------------------

os.environ["ANONYMIZED_TELEMETRY"] = "False"


# --------------------------------------------------
# Configuration validation
# --------------------------------------------------

if LLM_PROVIDER not in ("gemini", "ollama"):
    raise ValueError(
        "LLM_PROVIDER must be either 'gemini' or 'ollama'."
    )

if FALLBACK_PROVIDER not in ("gemini", "ollama"):
    raise ValueError(
        "FALLBACK_PROVIDER must be either 'gemini' or 'ollama'."
    )

if LLM_PROVIDER == "gemini" and not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY is missing. Please configure it in .env."
    )

if LLM_PROVIDER == FALLBACK_PROVIDER and ENABLE_LLM_FALLBACK:
    raise ValueError(
        "FALLBACK_PROVIDER must differ from LLM_PROVIDER "
        "when automatic fallback is enabled."
    )