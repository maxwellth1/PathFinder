from langchain.chat_models import init_chat_model
from langchain_community.utilities import SQLDatabase
from langgraph.checkpoint.memory import MemorySaver
import os


class AppContext:
    def __init__(self) -> None:
        self.db = SQLDatabase.from_uri(os.getenv("db_uri"))
        self.memory = MemorySaver()

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")

        if azure_endpoint and azure_api_key:
            self.llm = init_chat_model(
                model_name,
                model_provider="azure_openai",
                temperature=0,
                azure_endpoint=azure_endpoint,
                api_key=azure_api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview"),
            )
            print("✅ Using Azure OpenAI")
