from langgraph.graph import START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from .state import State
from .loadPandasDF import loadPandasDF
from .genPandasQuery import makeGenPandasQuery
from .execPandasQuery import makeExecPandasQuery
from .genAnswer import makeGenAnswer
from .genPlot import makeGenPlot
from ..utils.summarizeConversation import makeSummarizeConversation


def runSpreadSheetQuery(
    question: str, file_path: str, ctx, session_id: str = "default_session"
):
    llm = ctx.llm

    graph_builder = StateGraph(State)
    graph_builder.add_node("gen_pandas_query", makeGenPandasQuery(llm))
    graph_builder.add_node("exec_pandas_query", makeExecPandasQuery())
    graph_builder.add_node("gen_answer", makeGenAnswer(llm))
    graph_builder.add_node("gen_plot", makeGenPlot(llm))
    graph_builder.add_node("summarize_conversation", makeSummarizeConversation(llm))
    graph_builder.set_entry_point("gen_pandas_query")
    graph_builder.add_edge("gen_pandas_query", "exec_pandas_query")
    graph_builder.add_edge("exec_pandas_query", "gen_answer")
    graph_builder.add_edge("gen_answer", "gen_plot")
    graph_builder.add_edge("gen_plot", "summarize_conversation")

    memory = ctx.memory
    graph = graph_builder.compile(checkpointer=memory)

    config = {"configurable": {"thread_id": session_id}}

    result = None
    for step in graph.stream({"question": question, "file_path": file_path}, config):
        print(step)
        result = step
    print("\n" + "=" * 50 + "\n")

    return result

