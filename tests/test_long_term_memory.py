from long_term_memory import LongTermMemory


def main():
    memory = LongTermMemory()

    memory_id = memory.add_memory(
        text="I am researching sugarcane leaf disease detection.",
        category="project",
    )
    print("Saved memory ID:", memory_id)

    results = memory.search_memories(
        "What research project am I working on?"
    )

    print("\nSearch results:")
    for item in results:
        print("-", item.page_content)

    print("\nStored memories:", len(memory.list_memories()))


if __name__ == "__main__":
    main()