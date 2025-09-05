from .state import State
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage
import json
import pandas as pd


def makeGenAnswer(llm):
    def genAnswer(state: State):
        chat_context = ""
        if state.get("chat_history"):
            chat_context = "\n\nPrevious conversation:\n"
            for msg in state["chat_history"][-5:]:
                if hasattr(msg, "type"):
                    role = msg.type
                else:
                    role = "human" if "HumanMessage" in str(type(msg)) else "ai"
                chat_context += f"{role}: {msg.content}\n"

        prompt = (
            """
            Given the following user question regarding a query in an excel sheet, the corresponding pandas command, and the result of that command,
            generate a human-readable sentence with proper presentation.

            - Do not talk about any technical pandas information.
            - If the result is a list, format it for readability with multiple lines.
            - Your final output must be a single string.
            - Consider the previous conversation context when generating your response.
            
            - If there is multiple amounts of data, use markdwon tables represent it.
            """
            f"Question: {state['question']}\n"
            f"Pandas Command: {state['pandas_command']}\n"
            f"Result: {state['result']}\n"
            f"{chat_context}"
        )

        chain = llm | StrOutputParser()
        response = chain.invoke(prompt)
        return {"answer": response, "chat_history": [HumanMessage(content=state['question']), AIMessage(content=response)]}

    return genAnswer