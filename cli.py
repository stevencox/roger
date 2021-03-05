from roger.core import RogerUtil
from roger.Config import get_default_config as get_config
from roger.roger_util import get_logger
from dug_helpers.dug_utils import DugUtil
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
    parser.add_argument('-l', '--load-and-annotate',help="Annotates and normalizes datasets of varaibles.",
                        action="store_true")
    parser.add_argument('-t', '--make-tagged-kg', help="Creates KGX files from annotated variable datesets.",
                        action="store_true")

    """ Dug indexing CLI . """
    parser.add_argument('-I', '--index-variables', help="Index annotated variables to elastic search.",
                        action="store_true")
    parser.add_argument('-C', '--crawl-concepts', help="Crawl tranql and index concepts",
                        action="store_true")

    args = parser.parse_args ()

    config = get_config()
    if args.data_root is not None:
        data_root = args.data_root
        config.update({'data_root': data_root})
        log.info (f"data root:{data_root}")

    # When all lights are on...

    # Annotation comes first
    if args.load_and_annotate:
        DugUtil.load_and_annotate(config=config)

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

    # Back to dug indexing
    if args.index_variables:
        DugUtil.index_variables(config=config)

    if args.crawl_concepts:
        DugUtil.crawl_tranql(config=config)

    sys.exit (0)
