from dotenv import load_dotenv
from database.runDBQuery import runDBQuery
from appContext import AppContext
from spreadsheet.runSpreadsheetQuery import runSpreadSheetQuery


def main():
    import os

    dotenv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )

    if not load_dotenv(dotenv_path):
        raise FileNotFoundError(".env file does not exist")

    print("Initializing Jewellery Chatbot...")
    ctx = AppContext()

    print("""
        Select Mode:
        1. Database Query
        2. Spreadsheet Query
    """)

    userChoice = int(input())

    while True:
        try:
            question = input("Ask your question: ").strip()
            if question.lower() in ["exit", "quit", "bye", "stop"]:
                print("Goodbye")
                break

            if not question:
                print("Please enter a question.")

            if userChoice == 1:
                runDBQuery(ctx, question)

            if userChoice == 2:
                runSpreadSheetQuery(question, "assets/test.xlsx", ctx)

        except KeyboardInterrupt as e:
            print("\n\nGoodbye!")

        except Exception as e:
            print(f"Error: {e}")
            print("Please try again.\n")


if __name__ == "__main__":
    main()
