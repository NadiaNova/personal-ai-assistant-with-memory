
from llm_handler import LLMHandler

def main():
    assistant = LLMHandler(provider="gemini")

    print("Testing Gemini API...")

    answer = assistant.generate_response(
        "Reply in one sentence: My Personal AI Assistant is connected."
    )

    print("\nGemini response:")
    print(answer)

if __name__ == "__main__":
    main()