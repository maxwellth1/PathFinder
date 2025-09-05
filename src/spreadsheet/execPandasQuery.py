from .state import State
import pandas as pd
from datetime import date
import numpy as np


def makeExecPandasQuery():
    def execPandasQuery(state: State):
        from .loadPandasDF import loadPandasDF
        df = loadPandasDF(state["file_path"])
        pandas_command = state["pandas_command"]

        result = eval(pandas_command)

        # Instead of JSON, convert DataFrame to markdown for consumption by genPlot
        if isinstance(result, pd.DataFrame):
            # When converting to markdown, set the index to False to avoid an extra column
            # that can confuse the LLM when generating plotting code.
            result = result.to_markdown(index=False)
        elif isinstance(result, pd.Series):
            result = result.to_frame().to_markdown(index=False)
        elif isinstance(result, np.generic):
            result = result.item()
        elif isinstance(result, (pd.Period, pd.Timestamp, date)):
            result = result.isoformat()
        elif isinstance(result, set):
            result = list(result)
        
        # Ensure the result is a string for subsequent processing steps
        if not isinstance(result, str):
            result = str(result)

        return {"result": result}

    return execPandasQuery
