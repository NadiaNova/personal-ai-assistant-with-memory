from chatbot import RAGChatbot


def main():
    chatbot = RAGChatbot()

    memory_id = chatbot.save_long_term_memory(
        "I am building a Personal AI Assistant using Python.",
        category="project",
    )
    print("Saved ID:", memory_id)

    results = chatbot.recall_long_term_memory(
        "What AI project am I building?"
    )

    print("\nRecalled memories:")
    for item in results:
        print("-", item.page_content)

    print("\nTotal stored memories:",
          len(chatbot.get_long_term_memories()))


if __name__ == "__main__":
    main()