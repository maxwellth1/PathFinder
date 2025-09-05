import pandas as pd
from typing_extensions import Annotated, TypedDict
from .state import State
from langchain_core.prompts import ChatPromptTemplate
from .genPandasPrompt import genPandasPrompt


class QueryOutput(TypedDict):
    """Generated Pandas Syntax"""

    query: Annotated[str, ..., "Syntactically valid Pandas Syntax."]


def makeGenPandasQuery(llm):
    def genPandasQuery(state: State):
        question = state["question"]
        from .loadPandasDF import loadPandasDF
        df = loadPandasDF(state["file_path"])
        # The checkpointer automatically populates the chat_history from memory
        chat_history = state.get("chat_history", [])
        prompt = genPandasPrompt(df, question, chat_history)

        structured_llm = llm.with_structured_output(QueryOutput)
        result = structured_llm.invoke(prompt)

        return {"pandas_command": result["query"]}

    return genPandasQuery
