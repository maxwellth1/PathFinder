from typing_extensions import TypedDict, Annotated
from typing import Dict, Optional, List
from langchain_core.messages import BaseMessage
import operator
import pandas as pd


class State(TypedDict):
    question: str
    pandas_command: str
    plotly_plot: str
    result: str
    answer: str
    chat_history: Annotated[List[BaseMessage], operator.add]
    file_path: str
    summary: str

