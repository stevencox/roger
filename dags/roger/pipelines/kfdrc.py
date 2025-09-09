"Pipeline for KDFRC data"

from roger.pipelines import DugPipeline
from roger.core import storage

class kfdrcPipeline(DugPipeline):
    "Pipeline for KDFRC data set"
    pipeline_name = "kfdrc"
    parser_name = "kfdrc"

    def get_objects(self, input_data_path=None):
        if not input_data_path:
            input_data_path = storage.dug_kfdrc_path()
        files = storage.get_files_recursive(
            lambda file_name: (
                not file_name.startswith('GapExchange_')
                and file_name.endswith('.xml')),
            input_data_path)
        return sorted([str(f) for f in files])
