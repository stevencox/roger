"Pipeline for Topmed data"

from roger.pipelines import DugPipeline
from roger.pipelines.base import log, os
import jsonpickle
from roger.core import storage
from roger.logger import logger
class TopmedPipeline(DugPipeline):
    "Pipeline for Topmed data set"
    pipeline_name = "topmed"
    parser_name = "TOPMedTag"

    def get_objects(self, input_data_path=None):
        if not input_data_path:
            input_data_path = str(storage.dug_input_files_path('topmed'))
        files =storage.get_files_recursive(
                lambda file_name: file_name.endswith('.csv'),
                input_data_path)
        return sorted([str(x) for x in files])

    def make_kg_tagged(self, to_string=False, elements_files=None,
                       input_data_path=None, output_data_path=None):
        "Create tagged knowledge graphs from elements"
        log.info("Override base.make_kg_tagged called")
        if not output_data_path:
            output_data_path = storage.dug_kgx_path("")
        storage.clear_dir(output_data_path)
        if not elements_files:
            elements_files = storage.dug_elements_objects(input_data_path, format='txt')
        for file_ in elements_files:
            elements = jsonpickle.decode(storage.read_object(file_))
            kg = self.make_tagged_kg(elements)
            dug_base_file_name = file_.split(os.path.sep)[-2]
            output_file_path = os.path.join(output_data_path,
                                            dug_base_file_name + '_kgx.json')
            storage.write_object(kg, output_file_path)
            log.info("Wrote %d and %d edges, to %s", len(kg['nodes']),
                     len(kg['edges']), output_file_path)
        output_log = self.log_stream.getvalue() if to_string else ''
        return output_log

