"""CLI interface for roger
"""

import sys
import argparse
import os
import time
import pathlib

import roger
from roger.config import config
from roger.logger import get_logger
from roger.pipelines import get_pipeline_classes

log = get_logger()

def get_arguments():
    "Parse argv"

    parser = argparse.ArgumentParser(description='Roger common cli tool.')
    """ Common CLI. """
    parser.add_argument('-d', '--data-root', default=None,
                        help="Root of data hierarchy")
    parser.add_argument('-ip', '--input-path', default=None, type=pathlib.Path,
                        help="Input files path")
    parser.add_argument('-op', '--output-path', default=None, type=pathlib.Path,
                        help="Output files path")

    """ Roger CLI. """
    parser.add_argument('-v', '--dataset-version', help="Dataset version.",
                        default="v1.0")
    parser.add_argument('-g', '--get-kgx', help="Get KGX objects",
                        action='store_true')
    parser.add_argument('-s', '--create-schema', help="Infer schema",
                        action='store_true')
    parser.add_argument('-m', '--merge-kgx', help="Merge KGX nodes",
                        action='store_true')
    parser.add_argument('-b', '--create-bulk', help="Create bulk load",
                        action='store_true')
    parser.add_argument('-i', '--insert', help="Do the bulk insert",
                        action='store_true')
    parser.add_argument('-a', '--validate', help="Validate the insert",
                        action='store_true')

    dataset_envspec = os.getenv("ROGER_DUG__INPUTS_DATA__SETS",
                        "topmed:v2.0,dbGaP:v1.0,anvil:v1.0")
    data_sets = dataset_envspec.split(",")
    parser.add_argument('-D', '--datasets', action="append",
                        default=None,
                        help="Dataset pipelines name:vers to run. "
                        f"(default: f{str(data_sets)}")

    """ Dug Annotation CLI. """
    parser.add_argument('-gd', '--get_dug_input_files', action="store_true",
                        help="Gets input files for annotation")
    parser.add_argument('-l', '--load-and-annotate', action="store_true",
                        help="Annotates and normalizes datasets of varaibles.")
    parser.add_argument('-t', '--make-tagged-kg', action="store_true",
                        help="Creates KGX files from annotated variable "
                        "datasets.")

    """ Dug indexing CLI . """
    parser.add_argument('-iv', '--index-variables', action="store_true",
                        help="Index annotated variables to elastic search.")
    parser.add_argument('-C', '--crawl-concepts', action="store_true",
                        help="Crawl tranql and index concepts")
    parser.add_argument('-ic', '--index-concepts', action="store_true",
                        help="Index expanded concepts to elastic search.")

    parser.add_argument('-vc', '--validate-concepts', action="store_true",
                        help="Validates indexing of concepts")

    parser.add_argument('-vv', '--validate-variables', action="store_true",
                        help="Validates indexing of variables")

    args = parser.parse_args ()

    if args.data_root is not None:
        data_root = args.data_root
        config.data_root = data_root
        log.info (f"data root:{data_root}")

    if not args.datasets:
        args.datasets = data_sets

    return args

def main():
    start = time.time()
    log.info(f"Start TIME:{start}")

    args = get_arguments()
    # When all lights are on...

    # Instantiate the pipeline classes
    pipeline_names = {x.split(':')[0]: x.split(':')[1] for x in args.datasets}
    log.info("Working on dataset list %s", str(pipeline_names))
    pipeline_classes = get_pipeline_classes(pipeline_names)
    pipelines = [pipeclass(config) for pipeclass in pipeline_classes]

    for pipe in pipelines:
        # Do all actions for one pipeline first, then move on to the next:
        log.info("Running pipeline %s", pipe.pipeline_name)

        # Annotation comes first
        if args.get_dug_input_files:
            pipe.get_versioned_files()

        if args.load_and_annotate:
            pipe.clear_annotation_cached(output_data_path=args.output_path)
            pipe.annotate(input_data_path=args.input_path,
                          output_data_path=args.output_path)

        if args.make_tagged_kg:
            pipe.make_kg_tagged()

        # Roger things
        if args.get_kgx:
            roger.get_kgx(config=config)
        if args.merge_kgx:
            roger.merge_nodes(config=config)
        if args.create_schema:
            roger.create_schema(config=config)
        if args.create_bulk:
            roger.create_bulk_load(config=config)
        if args.insert:
            roger.bulk_load(config=config)
        if args.validate:
            roger.validate(config=config)
            roger.check_tranql(config=config)

        # Back to dug indexing
        if args.index_variables:
            pipe.index_variables()

        if args.validate_variables:
            pipe.validate_indexed_variables()

        if args.crawl_concepts:
            pipe.crawl_tranql()

        if args.index_concepts:
            pipe.index_concepts()

        if args.validate_concepts:
            pipe.validate_indexed_concepts()

    end = time.time()
    time_elapsed = end - start
    log.info(f"Completion TIME:{time_elapsed}")

    sys.exit (0)

if __name__ == "__main__":
    main()
