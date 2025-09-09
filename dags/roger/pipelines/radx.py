"Pipeline for BACPAC data"

from roger.pipelines import DugPipeline
from roger.core import storage


class RadxPipeline(DugPipeline):
    "Pipeline for Radx data set"
    pipeline_name = "radx"
    parser_name = "radx"

    def get_objects(self, input_data_path=None):
        if not input_data_path:
            input_data_path = storage.dug_kfdrc_path()
        files = storage.get_files_recursive(
            lambda file_name: file_name.endswith('.json'),
            input_data_path)
        return sorted([str(f) for f in files])
