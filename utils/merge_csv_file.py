import os
import uuid
import pandas as pd

from service.utils_controller import FILE_DIRECTORY


def merge_csv_files(file_list) -> str:
    output_file = os.path.join(FILE_DIRECTORY, str(uuid.uuid4()))
    # Read and concatenate all CSV files
    df_list = [pd.read_csv(file) for file in file_list]
    merged_df = pd.concat(df_list, ignore_index=True)

    merged_df.to_csv(output_file, index=False)
    return output_file
