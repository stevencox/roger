"Pipeline for Sparc data"

from roger.pipelines import DugPipeline
from roger.core import storage

class SparcPipeline(DugPipeline):
    "Pipeline for Sparc  data set"
    pipeline_name = "sparc"
    parser_name = "SciCrunch"

    def get_objects(self, input_data_path=None):
        if not input_data_path:
            input_data_path = storage.dug_heal_study_path()
        files = storage.get_files_recursive(
            lambda x: True, input_data_path
        )
        return sorted([str(f) for f in files])
