import os
from pathlib import Path

data_dir_env_value = os.getenv("ROGER_DATA_DIR")

if data_dir_env_value is None:
    ROGER_DATA_DIR = Path(__file__).parent.resolve() / 'data'
else:
    ROGER_DATA_DIR = Path(data_dir_env_value)


