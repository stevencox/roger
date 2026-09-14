from roger.pipelines import DugPipeline
from roger.core import  storage
from roger.logger import logger


class PicSure(DugPipeline):
    "Pipeline for BACPAC data set"
    pipeline_name = "bdc-test6"  #lakefs 
    parser_name = "dbgap"
    files_dir = "anvil"

    def get_objects(self, input_data_path=None):
        """Retrieve anvil objects

        This code is imported from roger.core.storage.dug_anvil_objects
        """
        if not input_data_path:
            input_data_path = storage.dug_input_files_path(
                self.files_dir)
        files = storage.get_files_recursive(
            lambda file_name: (
                not file_name.startswith('GapExchange_')
                and file_name.endswith('.xml')),
            input_data_path)
        logger.info("**********")
        logger.info(files)
        return sorted([str(f) for f in files])
