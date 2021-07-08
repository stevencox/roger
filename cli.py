from roger.core import RogerUtil
from roger.Config import config
from roger.roger_util import get_logger
from dug_helpers.dug_utils import DugUtil, get_topmed_files, get_dbgap_files
import sys
import argparse


log = get_logger()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Roger common cli tool.')
    """ Common CLI. """
    parser.add_argument('-d', '--data-root', help="Root of data hierarchy", default=None)

    """ Roger CLI. """
    parser.add_argument('-v', '--dataset-version', help="Dataset version.", default="v1.0")
    parser.add_argument('-g', '--get-kgx', help="Get KGX objects", action='store_true')
    parser.add_argument('-s', '--create-schema', help="Infer schema", action='store_true')
    parser.add_argument('-m', '--merge-kgx', help="Merge KGX nodes", action='store_true')
    parser.add_argument('-b', '--create-bulk', help="Create bulk load", action='store_true')
    parser.add_argument('-i', '--insert', help="Do the bulk insert", action='store_true')
    parser.add_argument('-a', '--validate', help="Validate the insert", action='store_true')

    """ Dug Annotation CLI. """
    parser.add_argument('-gd', '--get_dug_input_files', help="Gets input files for annotation",
                        action="store_true")
    parser.add_argument('-l', '--load-and-annotate',help="Annotates and normalizes datasets of varaibles.",
                        action="store_true")
    parser.add_argument('-t', '--make-tagged-kg', help="Creates KGX files from annotated variable datesets.",
                        action="store_true")

    """ Dug indexing CLI . """
    parser.add_argument('-iv', '--index-variables', help="Index annotated variables to elastic search.",
                        action="store_true")
    parser.add_argument('-C', '--crawl-concepts', help="Crawl tranql and index concepts",
                        action="store_true")

    parser.add_argument('-ic', '--index-concepts', help="Index expanded concepts to elastic search.",
                        action="store_true")

    parser.add_argument('-vc', '--validate-concepts', help="Validates indexing of concepts",
                        action="store_true")

    parser.add_argument('-vv', '--validate-variables', help="Validates indexing of variables",
                        action="store_true")

    args = parser.parse_args ()

    if args.data_root is not None:
        data_root = args.data_root
        config.data_root = data_root
        log.info (f"data root:{data_root}")

    # When all lights are on...

    # Annotation comes first
    if args.get_dug_input_files:
        get_topmed_files()
        get_dbgap_files()

    if args.load_and_annotate:
        DugUtil.annotate_db_gap_files(config=config)
        DugUtil.annotate_topmed_files(config=config)

    if args.make_tagged_kg:
        DugUtil.make_kg_tagged(config=config)

    # Roger things
    if args.get_kgx:
        RogerUtil.get_kgx(config=config)
    if args.merge_kgx:
        RogerUtil.merge_nodes(config=config)
    if args.create_schema:
        RogerUtil.create_schema(config=config)
    if args.create_bulk:
        RogerUtil.create_bulk_load(config=config)
    if args.insert:
        RogerUtil.bulk_load(config=config)
    if args.validate:
        RogerUtil.validate(config=config)
        RogerUtil.check_tranql(config=config)

    # Back to dug indexing
    if args.index_variables:
        DugUtil.index_variables(config=config)

    if args.validate_variables:
        DugUtil.validate_indexed_variables(config=config)

    if args.crawl_concepts:
        DugUtil.crawl_tranql(config=config)

    if args.index_concepts:
        DugUtil.index_concepts(config=config)

    if args.validate_concepts:
        DugUtil.validate_indexed_concepts(config=config)

    sys.exit (0)
