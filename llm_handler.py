
"""
LLM handler for Gemini and Ollama.

Features:
- Gemini and Ollama support
- Automatic provider fallback
- PDF retrieval-augmented generation (RAG)
- Session conversation history
- Long-term memory context support
"""

import logging
from typing import Any, Dict, Optional

from langchain_classic.chains import ConversationalRetrievalChain
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import PromptTemplate

import config

logger = logging.getLogger(__name__)


def _extract_text_content(content: Any) -> str:
    """Return only text blocks from provider content, excluding metadata."""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "".join(
            _extract_text_content(item)
            for item in content
            if isinstance(item, (str, dict, list))
        )

    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
        if isinstance(text, list):
            return _extract_text_content(text)
        return ""

    raise TypeError(
        f"Unsupported response content type: {type(content).__name__}"
    )


class LLMHandler:
    """Manage LLM providers, PDF RAG, and conversation history."""

    def __init__(
        self,
        provider: str = config.LLM_PROVIDER,
        temperature: float = config.LLM_TEMPERATURE,
    ) -> None:
        self.provider = provider.lower()
        self.temperature = temperature

        self._llm: Optional[BaseLanguageModel] = None
        self._chat_history: list[BaseMessage] = []
        self._qa_chain: Optional[ConversationalRetrievalChain] = None
        self._retriever: Any = None

        if self.provider not in ("gemini", "ollama"):
            raise ValueError(
                "Unsupported provider. Choose 'gemini' or 'ollama'."
            )

        logger.info("LLM Handler initialized: %s", self.provider)

    # --------------------------------------------------
    # LLM initialization
    # --------------------------------------------------

    def get_llm(self) -> BaseLanguageModel:
        """Create or return the active language model."""

        if self._llm is not None:
            return self._llm

        if self.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            if not config.GOOGLE_API_KEY:
                raise ValueError(
                    "GOOGLE_API_KEY is missing. Check your .env file."
                )

            self._llm = ChatGoogleGenerativeAI(
                model=config.GEMINI_MODEL,
                google_api_key=config.GOOGLE_API_KEY,
                temperature=self.temperature,
            )

            logger.info(
                "Initialized Gemini model: %s",
                config.GEMINI_MODEL,
            )

        else:
            from langchain_ollama import OllamaLLM

            self._llm = OllamaLLM(
                model=config.OLLAMA_MODEL,
                base_url=config.OLLAMA_BASE_URL,
                temperature=self.temperature,
            )

            logger.info(
                "Initialized Ollama model: %s",
                config.OLLAMA_MODEL,
            )

        return self._llm

    # --------------------------------------------------
    # Fallback helpers
    # --------------------------------------------------

    def _get_fallback_provider(self) -> str:
        """Choose the other configured provider."""

        if self.provider == config.LLM_PROVIDER:
            target = config.FALLBACK_PROVIDER
        else:
            target = config.LLM_PROVIDER

        if target not in ("gemini", "ollama"):
            raise ValueError(
                f"Invalid fallback provider: {target}"
            )

        if target == self.provider:
            raise ValueError(
                "Fallback provider must differ from the active provider."
            )

        return target

    def _activate_provider(self, provider: str) -> None:
        """Activate a provider and rebuild the QA chain if possible."""

        if provider not in ("gemini", "ollama"):
            raise ValueError(
                "Unsupported provider. Choose 'gemini' or 'ollama'."
            )

        self.provider = provider
        self._llm = None
        self._qa_chain = None

        if self._retriever is not None:
            self._build_qa_chain()

        logger.warning("Active LLM provider is now: %s", provider)

    # --------------------------------------------------
    # PDF RAG chain
    # --------------------------------------------------

    def _build_qa_chain(self) -> ConversationalRetrievalChain:
        """Build the conversational PDF QA chain for the active provider."""

        if self._retriever is None:
            raise ValueError("No document retriever is configured.")

        prompt_template = """You are a helpful assistant answering questions
using the provided document context and relevant saved user memories.

BACKGROUND MEMORY (not PDF evidence):
{memory_context}

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{question}

INSTRUCTIONS:
- Use document context for PDF-specific factual answers.
- Use background memory only when relevant to the question.
- Do not treat saved memories as evidence from the PDF.
- Use conversation history to understand follow-up questions.
- Do not invent facts missing from the available information.
- If a question asks specifically about the PDF and its answer is absent,
  say that the information was not found in the document.
- Keep answers clear and relevant.

ANSWER:"""

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=[
                "context",
                "question",
                "memory_context",
            ],
        )

        self._qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.get_llm(),
            retriever=self._retriever,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": prompt},
            verbose=False,
        )

        logger.info(
            "Created conversational QA chain using %s",
            self.provider,
        )

        return self._qa_chain

    def create_qa_chain(
        self,
        retriever: Any,
    ) -> ConversationalRetrievalChain:
        """Create the QA chain, trying fallback if initialization fails."""

        self._retriever = retriever

        try:
            return self._build_qa_chain()

        except Exception:
            logger.exception(
                "Could not initialize QA chain with %s.",
                self.provider,
            )

            if not config.ENABLE_LLM_FALLBACK:
                raise

            fallback_provider = self._get_fallback_provider()

            logger.warning(
                "Trying fallback provider: %s",
                fallback_provider,
            )

            self._activate_provider(fallback_provider)

            if self._qa_chain is None:
                raise RuntimeError(
                    "Fallback provider could not create the QA chain."
                )

            return self._qa_chain

    # --------------------------------------------------
    # Query with conversation history and long-term memory
    # --------------------------------------------------

    def query(
        self,
        question: str,
        memory_context: str = "",
    ) -> Dict[str, Any]:
        """Answer a question with PDF context and optional saved memories."""

        if self._qa_chain is None:
            raise ValueError(
                "QA chain not initialized. Process a PDF first."
            )

        try:
            response = self._qa_chain.invoke(
                {
                    "question": question,
                    "chat_history": self._chat_history,
                    "memory_context": memory_context or "No relevant saved memories.",
                }
            )

        except Exception:
            logger.exception(
                "Query failed with provider %s.",
                self.provider,
            )

            if not config.ENABLE_LLM_FALLBACK:
                raise

            fallback_provider = self._get_fallback_provider()

            logger.warning(
                "Query failed. Retrying with fallback provider: %s",
                fallback_provider,
            )

            # Activate the other provider and rebuild the QA chain.
            self._activate_provider(fallback_provider)

            # Retry once only; do not create an endless fallback loop.
            response = self._qa_chain.invoke(
                {
                    "question": question,
                    "chat_history": self._chat_history,
                    "memory_context": memory_context or "No relevant saved memories.",
                }
            )

        answer = _extract_text_content(response.get("answer", ""))

        self._chat_history.extend(
            [
                HumanMessage(content=question),
                AIMessage(content=answer),
            ]
        )

        logger.info(
            "Query completed using provider %s.",
            self.provider,
        )

        return {
            "result": answer,
            "source_documents": response.get("source_documents", []),
        }

    # --------------------------------------------------
    # Direct LLM response without PDF retrieval
    # --------------------------------------------------

    def generate_response(self, prompt: str) -> str:
        """Generate a direct response, with optional fallback."""

        try:
            response = self.get_llm().invoke(prompt)

        except Exception:
            logger.exception(
                "Direct response failed with provider %s.",
                self.provider,
            )

            if not config.ENABLE_LLM_FALLBACK:
                raise

            fallback_provider = self._get_fallback_provider()

            logger.warning(
                "Retrying direct response with %s.",
                fallback_provider,
            )

            self._activate_provider(fallback_provider)
            response = self.get_llm().invoke(prompt)

        content = getattr(response, "content", response)

        return _extract_text_content(content)

    # --------------------------------------------------
    # Session conversation history
    # --------------------------------------------------

    def clear_memory(self) -> None:
        """Clear only the current session's conversation history."""

        self._chat_history.clear()
        logger.info("Session conversation history cleared.")

    def get_conversation_history(self) -> list:
        """Return the current session's conversation history."""

        return list(self._chat_history)

    # --------------------------------------------------
    # Manual provider switching
    # --------------------------------------------------

    def switch_provider(self, provider: str) -> None:
        """Manually switch providers and rebuild the QA chain."""

        self._activate_provider(provider.lower())

    @property
    def current_provider(self) -> str:
        return self.provider

    @property
    def model_info(self) -> Dict[str, str]:
        """Return information about the active provider."""

        if self.provider == "gemini":
            return {
                "provider": "Google Gemini",
                "model": config.GEMINI_MODEL,
            }

        return {
            "provider": "Ollama",
            "model": config.OLLAMA_MODEL,
            "endpoint": config.OLLAMA_BASE_URL,
        }