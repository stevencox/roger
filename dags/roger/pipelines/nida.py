"NIDA data set pipeline definition"

from roger.pipelines import DugPipeline
from roger.core import storage

class NIDAPipeline(DugPipeline):
    "NIDA data pipeline"

    pipeline_name = 'nida'
    parser_name = 'NIDA'

    def get_objects(self, input_data_path=None):
        "Return list of NIDA source files"
        if not input_data_path:
            input_data_path = storage.dug_input_files_path(
                self.get_files_dir())
        files = sorted(storage.get_files_recursive(lambda x: 'NIDA-' in x , input_data_path))
        return files
