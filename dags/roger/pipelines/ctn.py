"Pipeline for Clinical trials network data"

from roger.pipelines import DugPipeline

class CTNPipeline(DugPipeline):
    "Pipeline for Clinical trials nework data set"
    pipeline_name = "ctn"
    parser_name = "ctn"


