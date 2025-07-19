from g_ask_grok import ask_grok

def main():
    """Example usage of the Grok chat script."""
    
    # Example questions to ask Grok
    questions = [
        "What's the weather like today?",
        "Can you explain quantum computing in simple terms?",
        "What are the latest developments in AI?",
        "Tell me a short joke about programming."
    ]
    
    print("Grok Chat Example")
    print("=" * 40)
    
    # Interactive mode - ask user for input
    while True:
        print("\nOptions:")
        print("1. Ask a custom question")
        print("2. Use example questions")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            question = input("Enter your question for Grok: ").strip()
            if question:
                print(f"\nAsking Grok: {question}")
                response = ask_grok(question)
                if response:
                    print(f"\nGrok's response:\n{response}")
                else:
                    print("No response received. Make sure Grok tab is open and Chrome debugging is enabled.")
        
        elif choice == "2":
            print("\nExample questions:")
            for i, q in enumerate(questions, 1):
                print(f"{i}. {q}")
            
            try:
                q_choice = int(input("\nSelect a question (1-4): ")) - 1
                if 0 <= q_choice < len(questions):
                    question = questions[q_choice]
                    print(f"\nAsking Grok: {question}")
                    response = ask_grok(question)
                    if response:
                        print(f"\nGrok's response:\n{response}")
                    else:
                        print("No response received. Make sure Grok tab is open and Chrome debugging is enabled.")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Please enter a valid number.")
        
        elif choice == "3":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
