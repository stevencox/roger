"Core Roger object and utilities"

import argparse
import sys
from io import StringIO
import logging

from roger.config import get_default_config as get_config
from roger.logger import get_logger
from roger.core.bulkload import BulkLoad
from roger.models.kgx import KGXModel
from roger.models.biolink import BiolinkModel

log = get_logger()

class Roger:
    """ Consolidate Roger functionality for a cleaner interface. """

    def __init__(self, to_string=False, config=None):
        """ Initialize.
        :param to_string: Log to str, available as self.log_stream.getvalue()
        after execution completes.
        """
        self.has_string_handler = to_string
        if not config:
            config = get_config()
        self.config = config
        if to_string:
            # Add a stream handler to enable to_string.
            self.log_stream = StringIO()
            self.string_handler = logging.StreamHandler (self.log_stream)
            log.addHandler (self.string_handler)
        log.debug("config is %s", config.kgx.biolink_model_version)
        self.biolink = BiolinkModel (config.kgx.biolink_model_version)
        self.kgx = KGXModel (self.biolink, config=config)
        self.bulk = BulkLoad (self.biolink, config=config)

    def __enter__(self):
        """ Implement Python's Context Manager interface. """
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """ Implement Python's Context Manager interface. We use this finalizer
        to detach the stream handler appended in the constructor.
        :param exception_type: Type of exception, if one occurred.
        :param exception_value: The exception, if one occurred.
        :param traceback: The stack trace explaining the exception.
        """
        if exception_type or exception_value or traceback:
            log.error (msg="Error:",
                       exc_info=(exception_type, exception_value, traceback))
        if self.has_string_handler:
            log.removeHandler (self.string_handler)

# interfaces abstracting Roger's inner workings to make it easier to
# incorporate into external tools like workflow engines.

def get_kgx (to_string=False, config=None):
    "get KGX dataset"
    output = None
    log.debug("Getting KGX method called.")
    with Roger (to_string, config=config) as roger:
        dataset_version=config.get('kgx', {}).get('dataset_version')
        log.debug("dataset_version is %s", dataset_version)
        roger.kgx.get(dataset_version=dataset_version)
        output = roger.log_stream.getvalue() if to_string else None
    return output

def create_schema(to_string=False, config=None):
    "Create noders and edges schemata"
    o1 = create_nodes_schema(to_string=to_string, config=config)
    o2 = create_edges_schema(to_string=to_string, config=config)
    output = (o1 + o2 ) if to_string else None
    return output

def create_edges_schema(to_string=False, config=None):
    "Create edges schema on KGX object"
    output = None
    with Roger(to_string, config=config) as roger:
        roger.kgx.create_edges_schema()
        output = roger.log_stream.getvalue() if to_string else None
    return output

def create_nodes_schema(to_string=False, config=None):
    "Create nodes schema on KGX object"
    output = None
    with Roger(to_string, config=config) as roger:
        roger.kgx.create_nodes_schema()
        output = roger.log_stream.getvalue() if to_string else None
    return output

def merge_nodes(to_string=False, config=None):
    "Run KGX merge"
    output = None
    with Roger (to_string, config=config) as roger:
        roger.kgx.merge()
        output = roger.log_stream.getvalue () if to_string else None
    return output

def create_bulk_load(to_string=False, config=None):
    "Generate bulk load files"
    o1 = create_bulk_nodes(to_string=to_string, config=config)
    o2 = create_bulk_edges(to_string=to_string, config=config)
    output = (o1 + o2) if to_string else None
    return output

def create_bulk_nodes(to_string=False, config=None):
    "Generate bulk node CSV file"
    output = None
    with Roger(to_string, config=config) as roger:
        roger.bulk.create_nodes_csv_file()
        output = roger.log_stream.getvalue() if to_string else None
    return output

def create_bulk_edges(to_string=False, config=None):
    "Create bulk edges CSV file"
    output = None
    with Roger(to_string, config=config) as roger:
        roger.bulk.create_edges_csv_file()
        output = roger.log_stream.getvalue() if to_string else None
    return output

def bulk_load(to_string=False, config=None):
    "Run bulk load insert process"
    output = None
    with Roger (to_string, config=config) as roger:
        roger.bulk.insert()
        output = roger.log_stream.getvalue () if to_string else None
    return output

def validate (to_string=False, config=None):
    "Run bulk validate process"
    output = None
    with Roger (to_string, config=config) as roger:
        roger.bulk.validate()
        output = roger.log_stream.getvalue () if to_string else None
    return output

def check_tranql(to_string=False, config=None):
    "Tranql server smoke check"
    output = None
    with Roger(to_string, config=config) as roger:
        roger.bulk.wait_for_tranql()
        output = roger.log_stream.getvalue() if to_string else None
    return output

def roger_cli():
    " Roger CLI. "
    parser = argparse.ArgumentParser(description='Roger')
    parser.add_argument('-v',
                        '--dataset-version',
                        help="Dataset version.",
                        default="v1.0")
    parser.add_argument('-d',
                        '--data-root',
                        help="Root of data hierarchy",
                        default=None)
    parser.add_argument('-g',
                        '--get-kgx',
                        help="Get KGX objects",
                        action='store_true')
    parser.add_argument('-l',
                        '--load-kgx',
                        help="Load via KGX",
                        action='store_true')
    parser.add_argument('-s',
                        '--create-schema',
                        help="Infer schema",
                        action='store_true')
    parser.add_argument('-m',
                        '--merge-kgx',
                        help="Merge KGX nodes",
                        action='store_true')
    parser.add_argument('-b',
                        '--create-bulk',
                        help="Create bulk load",
                        action='store_true')
    parser.add_argument('-i',
                        '--insert',
                        help="Do the bulk insert",
                        action='store_true')
    parser.add_argument('-a',
                        '--validate',
                        help="Validate the insert",
                        action='store_true')
    args = parser.parse_args ()

    biolink = BiolinkModel ()
    kgx = KGXModel (biolink)
    bulk = BulkLoad (biolink)
    if args.data_root is not None:
        config = get_config()
        data_root = args.data_root
        config.update({'data_root': data_root})
        log.info("data root: %s", data_root)
    if args.get_kgx:
        kgx.get (dataset_version=args.dataset_version)
    if args.load_kgx:
        kgx.load ()
    if args.merge_kgx:
        kgx.merge ()
    if args.create_schema:
        kgx.create_schema ()
    if args.create_bulk:
        bulk.create ()
    if args.insert:
        bulk.insert ()
    if args.validate:
        bulk.validate ()

    sys.exit (0)
