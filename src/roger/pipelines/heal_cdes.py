"Pipeline to ingest HEAL in new data model"

from roger.pipelines import DDM2Pipeline
from roger.core import storage

class HealStudiesDDM2Pipeline(DDM2Pipeline):
    "Pipeline for HEAL data using dug data model v2"
    pipeline_name = "heal-cdes"
    parser_name = "heal-ddm2"

    def get_objects(self, input_data_path=None):
        if not input_data_path:
            input_data_path = storage.dug_heal_study_path()
        files = storage.get_files_recursive(
            lambda file_name: file_name.endswith('.dug.json'),
            input_data_path)
        return sorted([str(f) for f in files])
