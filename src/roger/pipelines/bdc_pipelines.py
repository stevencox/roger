"Dug pipeline for dbGaP data set"

from roger.pipelines import DugPipeline

class BIOLINCCdbGaPPipeline(DugPipeline):
    "Pipeline for the dbGaP data set"
    pipeline_name = 'bdc-biolincc'
    parser_name = 'biolincc'


class covid19dbGaPPipeline(DugPipeline):
    "Pipeline for the dbGaP data set"
    pipeline_name = 'bdc-covid19'
    parser_name = 'covid19'

class dirDbGaPPipeline(DugPipeline):
    pipeline_name = "bdc-dir"
    parser_name = "dir"

class LungMapDbGaPPipeline(DugPipeline):
    pipeline_name = "bdc-lungmap"
    parser_name = "lungmap"

class nsrrDbGaPPipeline(DugPipeline):
    pipeline_name = "bdc-nsrr"
    parser_name = "nsrr"

class ParentDbGaPPipeline(DugPipeline):
    pipeline_name = "bdc-parent"
    parser_name = "parent"

class PCGCDbGaPPipeline(DugPipeline):
    pipeline_name = "pcgc-dbgap"
    parser_name = "pcgc"

class RecoverDbGaPPipeline(DugPipeline):
    pipeline_name = "bdc-recover"
    parser_name = "recover"

class TopmedDBGaPPipeline(DugPipeline):
    pipeline_name = "bdc-topmed"
    parser_name = "topmeddbgap"

class CureSCPipeline(DugPipeline):
    pipeline_name = "bdc-curesc"
    parser_name = "curesc"

class HeartFailurePipeline(DugPipeline):
    pipeline_name = "bdc-heartfailure"
    parser_name = "heartfailure"

class ImagingPipeline(DugPipeline):
    pipeline_name = "bdc-imaging"
    parser_name = "imaging"

class RedsPipeline(DugPipeline):
    pipeline_name = "bdc-reds"
    parser_name = "reds"