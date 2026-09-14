"Pipeline for BACPAC data"

from roger.pipelines import DugPipeline

class BacPacPipeline(DugPipeline):
    "Pipeline for BACPAC data set"
    pipeline_name = "bacpac"
    parser_name = "BACPAC"
