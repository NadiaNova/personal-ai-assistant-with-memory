
"""
Main chatbot module that orchestrates:
- PDF-based RAG
- Persistent long-term memory
- Memory retrieval across application sessions
"""

import logging
from typing import Any, Dict, List, Optional

from document_processor import DocumentProcessor
from vector_store import VectorStoreManager
from llm_handler import LLMHandler
from long_term_memory import LongTermMemory

logger = logging.getLogger(__name__)


class RAGChatbot:
    """Chatbot integrating PDF retrieval and persistent memory."""

    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.vector_store_manager = VectorStoreManager()
        self.llm_handler = LLMHandler()
        self.long_term_memory = LongTermMemory()
        self._is_initialized = False
        self.last_processing_error: Optional[str] = None

        logger.info("Initialized RAG Chatbot")

    def process_pdfs(self, uploaded_files: List) -> bool:
        """Process uploaded PDFs and initialize document-based chat."""
        self.last_processing_error = None
        try:
            if isinstance(uploaded_files, list):
                chunks = self.document_processor.process_multiple_pdfs(
                    uploaded_files
                )
            else:
                chunks = self.document_processor.process_pdf(uploaded_files)

            self.vector_store_manager.create_vector_store(chunks)

            retriever = self.vector_store_manager.get_retriever()
            self.llm_handler.create_qa_chain(retriever)

            self._is_initialized = True
            logger.info("PDF processing completed successfully")
            return True

        except Exception as error:
            self.last_processing_error = str(error)
            logger.exception("Error processing PDFs")
            return False

    def add_pdfs(self, uploaded_files: List) -> bool:
        """Add more PDFs to the existing vector store."""
        try:
            if isinstance(uploaded_files, list):
                chunks = self.document_processor.process_multiple_pdfs(
                    uploaded_files
                )
            else:
                chunks = self.document_processor.process_pdf(uploaded_files)

            self.vector_store_manager.add_documents(chunks)

            retriever = self.vector_store_manager.get_retriever()
            self.llm_handler.create_qa_chain(retriever)

            self._is_initialized = True
            logger.info("Additional PDFs added successfully")
            return True

        except Exception:
            logger.exception("Error adding PDFs")
            return False

    def save_long_term_memory(
        self, text: str, category: str = "general"
    ):
        """Save information for use in future sessions."""
        text = text.strip()

        if not text:
            raise ValueError("Memory text cannot be empty.")

        return self.long_term_memory.add_memory(
            text=text,
            category=category,
        )

    def recall_long_term_memory(
        self, query: str, k: int = 4
    ) -> list:
        """Retrieve relevant memories from persistent storage."""
        return self.long_term_memory.search_memories(
            query=query,
            k=k,
        )

    def get_long_term_memories(self, limit: int = 50) -> list:
        """Return stored long-term memories."""
        return self.long_term_memory.list_memories(limit=limit)

    def delete_long_term_memory(self, memory_id: str):
        """Delete one saved memory."""
        return self.long_term_memory.delete_memory(memory_id)

    @staticmethod
    def _get_memory_to_save(question: str):
        """
        Return the text following an explicit remember/save command.
        Ordinary messages are not automatically saved.
        """
        prefixes = (
            "please remember that ",
            "remember that ",
            "please remember ",
            "remember ",
            "save this memory: ",
            "save this: ",
            "don't forget that ",
            "do not forget that ",
        )

        cleaned = question.strip()

        for prefix in prefixes:
            if cleaned.lower().startswith(prefix):
                memory_text = cleaned[len(prefix):].strip()
                if memory_text:
                    return memory_text

        return None

    def chat(self, question: str) -> Dict[str, Any]:
        """Answer questions using saved memories and, when available, PDFs."""
        question = question.strip()

        if not question:
            return {
                "result": "Please enter a question.",
                "source_documents": [],
            }

        try:
            # 1. Explicit memory-saving request.
            memory_to_save = self._get_memory_to_save(question)

            if memory_to_save:
                self.save_long_term_memory(
                    text=memory_to_save,
                    category="user_fact",
                )

                logger.info("Saved a new long-term memory")

                return {
                    "result": (
                        "I've saved this information to long-term memory: "
                        f"{memory_to_save}"
                    ),
                    "source_documents": [],
                }

            # 2. Search persistent memories, even if no PDF was uploaded
            # during the current application session.
            memories = self.recall_long_term_memory(
                query=question,
                k=4,
            )

            memory_context = "\n".join(
                f"- {item.page_content}"
                for item in memories
            )

            # 3. If PDFs have been initialized, use the existing RAG chain.
            if self._is_initialized:
                return self.llm_handler.query(
                    question,
                    memory_context=memory_context,
                )

            # 4. Otherwise, allow memory-based chat without requiring
            # a PDF to be uploaded again after an application restart.
            
            prompt = f"""
You are a helpful personal AI assistant.

Relevant saved memories:
{memory_context if memory_context else "No relevant saved memories were found."}

User's question:
{question}

Instructions:
- Answer general knowledge questions directly and naturally.
- Use saved memories only when they are relevant to the question.
- Never say information is missing from saved memories
  when answering an ordinary general knowledge question.
- For personal questions about the user, use relevant saved
  memories and never invent personal facts.
- If relevant personal information is not available,
  clearly explain that you do not have that information.
- Keep the answer concise, accurate, and helpful.

"""

            answer = self.llm_handler.generate_response(prompt)

            return {
                "result": answer,
                "source_documents": [],
            }

        except Exception as e:
            logger.exception("Error during chat")
            return {
                "result": f"Sorry, I encountered an error: {str(e)}",
                "source_documents": [],
            }

    def search_documents(self, query: str, k: int = 4) -> List:
        """Search the PDF vector store."""
        return self.vector_store_manager.search(query, k)

    def clear_chat_history(self):
        """Clear in-session conversation history, not persistent memories."""
        self.llm_handler.clear_memory()
        logger.info("Cleared session chat history")

    def get_chat_history(self) -> list:
        """Return current in-session conversation history."""
        return self.llm_handler.get_conversation_history()

    def reset(self):
        """
        Reset PDF/chat state without deleting persistent user memories.
        """
        self.vector_store_manager.clear_vector_store()
        self.llm_handler.clear_memory()
        self._is_initialized = False
        logger.info("Reset chatbot state; long-term memories were preserved")

    @property
    def is_ready(self) -> bool:
        """Whether the PDF-based RAG chain is ready."""
        return self._is_initialized