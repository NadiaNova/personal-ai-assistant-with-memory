
"""
Long-term memory for the Personal AI Assistant.

Stores memories persistently in a dedicated ChromaDB collection.
Uses the existing Ollama embedding model.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

import config

logger = logging.getLogger(__name__)


class LongTermMemory:
    """Persistent memory storage and semantic search."""

    def __init__(self):
        self.embedding_function = OllamaEmbeddings(
            model=config.EMBEDDING_MODEL,
            base_url=config.OLLAMA_BASE_URL,
        )

        # Dedicated collection: keeps memories separate from PDF data.
        self.vector_store = Chroma(
            collection_name="user_memories",
            persist_directory=str(
            config.BASE_DIR / "memoryDB"
          ),
            embedding_function=self.embedding_function,
        )

        logger.info("Long-term memory initialized.")

    def add_memory(
        self,
        text: str,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save one memory and return its ID."""

        text = text.strip()
        if not text:
            raise ValueError("Memory text cannot be empty.")

        memory_id = str(uuid.uuid4())

        memory_metadata = {
            "category": category,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if metadata:
            # Chroma metadata values must be simple supported types.
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    memory_metadata[key] = value

        document = Document(
            page_content=text,
            metadata=memory_metadata,
        )

        self.vector_store.add_documents(
            documents=[document],
            ids=[memory_id],
        )

        logger.info("Saved long-term memory: %s", memory_id)
        return memory_id

    def search_memories(
        self,
        query: str,
        k: int = 4,
    ) -> List[Document]:
        """Find memories relevant to a query."""

        if not query.strip():
            return []

        return self.vector_store.similarity_search(
            query=query,
            k=max(1, min(k, 10)),
        )

    def list_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List stored memories for the memory-management UI."""

        result = self.vector_store.get(
            limit=max(1, min(limit, 200)),
            include=["documents", "metadatas"],
        )

        memories = []
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        for index, memory_id in enumerate(ids):
            memories.append({
                "id": memory_id,
                "text": documents[index] if index < len(documents) else "",
                "metadata": (
                    metadatas[index]
                    if index < len(metadatas) and metadatas[index]
                    else {}
                ),
            })

        return memories

    def delete_memory(self, memory_id: str) -> None:
        """Delete one memory by its ID."""

        self.vector_store.delete(ids=[memory_id])
        logger.info("Deleted long-term memory: %s", memory_id)

    def clear_memories(self) -> None:
        """Delete all memories without deleting PDF documents."""

        result = self.vector_store.get(include=[])
        ids = result.get("ids", [])

        if ids:
            self.vector_store.delete(ids=ids)

        logger.info("Cleared all long-term memories.")