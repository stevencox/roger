"Pipeline for BDC-dbGap data"

from roger.pipelines import DugPipeline
from roger.core import storage

class bdcPipeline(DugPipeline):
    "Pipeline for BDC-dbGap data set"
    pipeline_name = "bdc"
    parser_name = "dbgap"

    def get_objects(self, input_data_path=None):
        if not input_data_path:
            input_data_path = storage.dug_dd_xml_path()
        files = storage.get_files_recursive(
            lambda file_name: (
                not file_name.startswith('._')
                and file_name.endswith('.xml')),
            input_data_path)
        return sorted([str(f) for f in files])
