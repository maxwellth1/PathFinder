from langchain_core.messages import HumanMessage, AIMessage
from ..spreadsheet.state import State # Assuming State is compatible or will be made generic

def makeSummarizeConversation(llm):
    def summarize_conversation(state: State):
        # Get existing summary
        current_summary = state.get("summary", "")
        chat_history = state.get("chat_history", [])

        # Create our summarization prompt
        if current_summary:
            summary_prompt_message = (
                f"This is a summary of the conversation to date: {current_summary}\n\n"
                "Extend the summary by taking into account the new messages above:"
            )
        else:
            summary_prompt_message = "Create a summary of the conversation above:"

        # Prepare messages for the LLM to generate the summary
        # We pass the full chat history + the summarization prompt
        messages_for_llm = chat_history + [HumanMessage(content=summary_prompt_message)]

        # Invoke the LLM to get the new summary
        response = llm.invoke(messages_for_llm)
        new_summary = response.content

        # Return the updated summary.
        # The `chat_history` in the state is managed by `MemorySaver` with `auto_summarize=True`,
        # which handles its internal summarization for checkpointing.
        # Explicitly truncating `chat_history` here would conflict with `operator.add`
        # and `MemorySaver`'s intended behavior.
        return {"summary": new_summary}

    return summarize_conversation
