"Pipeline for Heal-studies data"

from roger.pipelines import DugPipeline
from roger.core import storage

class HealResearchProgramPipeline(DugPipeline):
    "Pipeline for Heal-research-programs  data set"
    pipeline_name = "heal-mds-research-networks"
    parser_name = "heal-research"

    def get_objects(self, input_data_path=None):
        if not input_data_path:
            input_data_path = storage.dug_heal_research_program_path()
        files = storage.get_files_recursive(lambda file_name: file_name.endswith('.xml'),
                                    input_data_path)
        return sorted([str(f) for f in files])