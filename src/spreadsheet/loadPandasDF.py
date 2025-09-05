import pandas as pd
import os


def loadPandasDF(file_path):
    ext = os.path.splitext(file_path)[1]

    if ext == ".csv":
        df = pd.read_csv(file_path)
    elif ext == ".xlsx":
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported extension: {ext}")

    return df
