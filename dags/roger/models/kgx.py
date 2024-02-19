"KGX data model for Roger"

import os
import time
import queue
from itertools import chain
import threading
from collections import defaultdict
from xxhash import xxh64_hexdigest
import orjson as json
import redis
import ntpath
from kg_utils.merging import GraphMerger, MemoryGraphMerger, DiskGraphMerger
from kg_utils.constants import *

from roger.config import get_default_config
from roger.logger import get_logger
from roger.components.data_conversion import compare_types
from roger.core import storage
from roger.models.biolink import BiolinkModel
from roger.core.enums import SchemaType

log = get_logger()

class KGXModel:
    """ Abstractions for transforming KGX formatted data.

    KGX stands for Knowledge Graph Exchange
    """
    def __init__(self, biolink=None, config=None):
        if not config:
            config = get_default_config()
        self.config = config

        # We need a temp director for the DiskGraphMerger
        self.temp_directory = storage.merge_path(
            self.config.kgx.merge_db_temp_dir)
        log.debug(f"Setting temp_directory to : {self.temp_directory}")
        isExist = os.path.exists(self.temp_directory)
        if not isExist:
            os.makedirs(self.temp_directory)

        self.merger = DiskGraphMerger(temp_directory=self.temp_directory,
                                      chunk_size=5_000_000)
        self.biolink_version = self.config.kgx.biolink_model_version
        self.merge_db_id = self.config.kgx.merge_db_id
        self.merge_db_name = f'db{self.merge_db_id}'
        log.debug(f"Trying to get biolink version : {self.biolink_version}")
        if biolink is None:
            self.biolink = BiolinkModel(self.biolink_version)
        else:
            self.biolink = biolink
        self.redis_conn = redis.Redis(
                    host=self.config.redisgraph.host,
                    port=self.config.redisgraph.port,
                    password=self.config.redisgraph.password,
                    db=self.merge_db_id)
        self.enable_metrics = self.config.get('enable_metrics', False)

    def get_kgx_json_format(self, files: list, dataset_version: str):
        """Gets Json formatted kgx files.

        These files have a the following structure:
        {"nodes": [{"id":"..."},...], "edges": [{"id":...},...}] }

        Parameters
        ----------
        files : list of file names
        dataset_version : dataset version from dataset meta-data information

        Returns None
        -------

        """
        file_tuple_q = queue.Queue()
        thread_done_q = queue.Queue()
        for nfile, file_name in enumerate(files):
            # file_url or skip
            file_name = dataset_version + "/" + file_name
            file_url = storage.get_uri(file_name, "kgx_base_data_uri")
            subgraph_basename = os.path.basename(file_name)
            subgraph_path = storage.kgx_path(subgraph_basename)
            if os.path.exists(subgraph_path):
                log.info(f"cached kgx: {subgraph_path}")
                continue
            log.debug("#{}/{} to get: {}".format(
                nfile+1, len(files), file_url))
            # folder
            dirname = os.path.dirname (subgraph_path)
            if not os.path.exists (dirname):
                os.makedirs (dirname, exist_ok=True)
            # add to queue
            file_tuple_q.put((file_url,subgraph_path))

        # start threads for each file download
        threads = []
        for thread_num in range(len(files)): # len(files)
            th = threading.Thread(
                target=storage.downloadfile,
                args=(thread_num, file_tuple_q, thread_done_q))
            th.start()
            threads.append(th)

        # wait for each thread to complete
        for nwait in range(len(threads)):
            thread_num, num_files_processed = thread_done_q.get()
            th = threads[thread_num]
            th.join()
            log.info(f"#{nwait+1}/{len(threads)} joined: "
                     f"thread-{thread_num} processed: "
                     f"{num_files_processed} file(s)")

        all_kgx_files = []
        for nfile, file_name in enumerate(files):
            start = storage.current_time_in_millis()
            file_name = dataset_version + "/" + file_name
            file_url = storage.get_uri(file_name, "kgx_base_data_uri")
            subgraph_basename = os.path.basename(file_name)
            subgraph_path = storage.kgx_path(subgraph_basename)
            all_kgx_files.append(subgraph_path)
            if os.path.exists(subgraph_path):
                log.info(f"cached kgx: {subgraph_path}")
                continue
            log.info ("#{}/{} read: {}".format(nfile+1, len(files), file_url))
            subgraph = storage.read_object(file_url)
            storage.write_object(subgraph, subgraph_path)
            total_time = storage.current_time_in_millis() - start
            edges = len(subgraph['edges'])
            nodes = len(subgraph['nodes'])
            log.info(
                "#{}/{} edges:{:>7} nodes: {:>7} time:{:>8} wrote: {}".format(
                    nfile+1, len(files), edges, nodes,
                    total_time/1000, subgraph_path))
        return all_kgx_files

    def get_kgx_jsonl_format(self, files, dataset_version):
        """gets pairs of jsonl formatted kgx files.

        Files is expected to have all the pairs.

        I.e if kgx_1_nodes.jsonl exists its expected that kgx_1_edges.jsonl
        exists in the same path.
        File names should have strings *nodes*.jsonl and *edges*.jsonl.
        Parameters
        ----------
        files
        dataset_version

        Returns
        -------

        """
        # make a paired list
        paired_up = []
        log.info(f"getting {files}")
        for file_name in files:
            if "nodes" in file_name:
                paired_up.append(
                    [file_name, file_name.replace('nodes', 'edges')])
        error = False
        # validate that all pairs exist
        if len(files) / 2 != len(paired_up):
            log.error("Error paired up kgx jsonl files don't match "
                      "list of files specified in metadata.yaml")
            error = True
        for pairs in paired_up:
            if pairs[0] not in files:
                log.error(
                    f"{pairs[0]} not in original list "
                    f"of files from metadata.yaml")
                error = True
            if pairs[1] not in files:
                error = True
                log.error(
                    f"{pairs[1]} not in original list "
                    f"of files from metadata.yaml")
        if error:
            raise Exception("Metadata.yaml has inconsistent jsonl files")

        file_tuple_q = queue.Queue()
        thread_done_q = queue.Queue()
        for npairs, pairs in enumerate(paired_up):
            for npair, p in enumerate(pairs):
                file_name = dataset_version + "/" + p
                file_url = storage.get_uri(file_name, "kgx_base_data_uri")
                subgraph_basename = os.path.basename(file_name)
                subgraph_path = storage.kgx_path(subgraph_basename)
                if os.path.exists(subgraph_path):
                    log.info(f"skip cached kgx: {subgraph_path}")
                    continue
                log.info ("#{}.{}/{} read: {}".format(
                    npairs+1, npair+1, len(paired_up), file_url))
                # folder
                dirname = os.path.dirname (subgraph_path)
                if not os.path.exists (dirname):
                    os.makedirs (dirname, exist_ok=True)
                # add to queue
                file_tuple_q.put((file_url,subgraph_path))

        # start threads for each file download
        threads = []
        for thread_num in range(file_tuple_q.qsize()):
            th = threading.Thread(
                target=storage.downloadfile,
                args=(thread_num, file_tuple_q, thread_done_q))
            th.start()
            threads.append(th)

        # wait for each thread to complete
        for nwait in range(len(threads)):
            thread_num, num_files_processed = thread_done_q.get()
            th = threads[thread_num]
            th.join()
            log.info(f"#{nwait+1}/{len(threads)} joined: "
                     f"thread-{thread_num} processed: "
                     f"{num_files_processed} file(s)")

        all_kgx_files = []
        for pairs in paired_up:
            nodes = 0
            edges = 0
            start = storage.current_time_in_millis()
            for p in pairs:
                file_name = dataset_version + "/" + p
                file_url = storage.get_uri(file_name, "kgx_base_data_uri")
                subgraph_basename = os.path.basename(file_name)
                subgraph_path = storage.kgx_path(subgraph_basename)
                all_kgx_files.append(subgraph_path)
                if os.path.exists(subgraph_path):
                    log.info(f"cached kgx: {subgraph_path}")
                    continue
                data = storage.read_object(file_url)
                storage.write_object(data, subgraph_path)
                if "edges" in p:
                    edges = len(data.split('\n'))
                else:
                    nodes = len(data.split('\n'))
            total_time = storage.current_time_in_millis() - start
            log.info(
                "wrote {:>45}: edges:{:>7} nodes: {:>7} time:{:>8}".format(
                    storage.trunc(subgraph_path, 45), edges, nodes, total_time))
        return all_kgx_files

    def get (self, dataset_version = "v1.0"):
        """ Read metadata for KGX files and downloads them locally.
        :param dataset_version: Data version to operate on.
        """
        metadata = storage.read_relative_object ("../../metadata.yaml")
        data_set_list = self.config.kgx.data_sets
        kgx_files_remote = []
        for item in metadata['kgx']['versions']:
            if (item['version'] == dataset_version and
                item['name'] in data_set_list):
                log.info(f"Getting KGX dataset {item['name']}, "
                         f"version {item['version']}")
                if item['format'] == 'json':
                    kgx_files_remote += self.get_kgx_json_format(
                        item['files'], item['version'])
                elif item['format'] == 'jsonl':
                    kgx_files_remote += self.get_kgx_jsonl_format(
                        item['files'], item['version'])
                else:
                    raise ValueError(
                        f"Unrecognized format in metadata.yaml: "
                        f"{item['format']}, valid formats are `json` "
                        f"and `jsonl`.")
        # Fetchs kgx generated from Dug Annotation workflow.
        new_files = self.fetch_dug_kgx() + kgx_files_remote
        all_files_in_dir = (
            storage.kgx_objects("json") +
            storage.kgx_objects("jsonl"))
        files_to_remove = [x for x in all_files_in_dir
                           if x not in new_files]
        if len(files_to_remove):
            log.info(
                "Found some old files to remove from kgx dir : %s",
                files_to_remove)
            for file in files_to_remove:
                storage.remove(file)
                log.info("removed %s", file)
        log.info("Done.")



    def fetch_dug_kgx(self):
        """
        Copies files from dug output dir to roger kgx dir.
        :return:
        """
        dug_kgx_files = storage.dug_kgx_objects()
        all_kgx_files = []
        log.info("Copying dug KGX files to %s. Found %d kgx files to copy.",
                 storage.kgx_path(''), len(dug_kgx_files))
        for file in dug_kgx_files:
            file_name = ntpath.basename(file)
            dest = storage.kgx_path(file_name)
            all_kgx_files.append(dest)
            storage.write_object({}, dest)
            log.info(f"Copying from {file} to {dest}.")
            storage.copy_file_to_dir(file, dest)
        log.info("Done copying dug KGX files.")
        return all_kgx_files

    def create_nodes_schema(self):
        """
        Extracts schema for nodes based on biolink leaf types
        :return:
        """

        category_schemas = defaultdict(lambda: None)
        category_error_nodes = set()
        merged_nodes_file = storage.merge_path("nodes.jsonl")
        log.info(f"Processing : {merged_nodes_file}")
        counter = 0
        for node in storage.json_line_iter(merged_nodes_file):
            # Debuging code
            if counter % 10000 == 0:
                log.info(f"Processing node : {node} counter : {counter}")
            counter += 1

            if not node['category']:
                category_error_nodes.add(node['id'])
                node['category'] = [BiolinkModel.root_type]

            # Get all leaf types of this node
            node_types = list(
                self.biolink.find_biolink_leaves(node['category']))
            # pick the fist one to work on            
            node_type = node_types[0]


            # make sure it is defined in the final dict
            category_schemas[node_type] = category_schemas.get(node_type, {})

            # compute full list of attributes and the value types of the
            # attributes for that type.
            for k in node.keys():
                current_type = type(node[k]).__name__
                if k not in category_schemas[node_type]:
                    category_schemas[node_type][k] = current_type
                else:
                    previous_type = category_schemas[node_type][k]
                    category_schemas[node_type][k] = compare_types(
                        previous_type, current_type)

            # copy over final result to every other leaf type
            for tp in node_types:
                category_schemas[tp] = category_schemas[node_type]


        if len(category_error_nodes):
            log.warn(f"some nodes didn't have category assigned. "
                     f"KGX file has errors."
                     f"Nodes {len(category_error_nodes)}."
                     f"Showing first 10: {list(category_error_nodes)[:10]}."
                     f"These will be treated as {BiolinkModel.root_type}.")

        # Write node schemas.
        self.write_schema(category_schemas, SchemaType.CATEGORY)

    def create_edges_schema(self):
        """
        Create unified schema for all edges in an edges jsonl file.
        :return:
        """
        predicate_schemas = defaultdict(lambda: None)
        merged_edges_file = storage.merge_path("edges.jsonl")
        """ Infer predicate schemas. """
        for edge in storage.json_line_iter(merged_edges_file):
            predicate = edge['predicate']
            predicate_schemas[predicate] = predicate_schemas.get(predicate,
                                                                 {})
            for k in edge.keys():
                current_type = type(edge[k]).__name__
                if k not in predicate_schemas[predicate]:
                    predicate_schemas[predicate][k] = current_type
                else:
                    previous_type = predicate_schemas[predicate][k]
                    predicate_schemas[predicate][k] = compare_types(
                        previous_type, current_type)
        self.write_schema(predicate_schemas, SchemaType.PREDICATE)

    def create_schema (self):
        """Determine the schema of each type of object.

        We have to do this to make it possible to write tabular data. Need to
        know all possible columns in advance and correct missing fields.
        """
        if self.schema_up_to_date():
            log.info (f"schema is up to date.")
            return

        self.create_nodes_schema()
        self.create_edges_schema()

    def schema_up_to_date (self):
        return storage.is_up_to_date (
            source=storage.kgx_objects(),
            targets=[
                storage.schema_path (
                    f"{SchemaType.PREDICATE.value}-schema.json"),
                storage.schema_path (
                    f"{SchemaType.PREDICATE.value}-schema.json")
            ])

    def write_schema(self, schema, schema_type: SchemaType):
        """ Output the schema file.
 
        :param schema: Schema to get keys from.
        :param schema_type: Type of schema to write.
        """
        file_name = storage.schema_path (f"{schema_type.value}-schema.json")
        log.info("writing schema: %s", file_name)
        dictionary = { k : v for k, v in schema.items () }
        storage.write_object (dictionary, file_name)

    def merge(self):
        """ This version uses the disk merging from the kg_utils module """
        data_set_version = self.config.get('kgx', {}).get('dataset_version')
        metrics = {}
        start = time.time()
        json_format_files = storage.kgx_objects("json")
        jsonl_format_files = storage.kgx_objects("jsonl")

        # Create lists of the nodes and edges files in both json and jsonl
        # formats
        jsonl_node_files = {file for file in jsonl_format_files
                            if "node" in file}
        jsonl_edge_files = {file for file in jsonl_format_files
                            if "edge" in file}

        # Create all the needed iterators and sets thereof
        jsonl_node_iterators = [storage.jsonl_iter(file_name)
                                for file_name in jsonl_node_files]
        jsonl_edge_iterators = [storage.jsonl_iter(file_name)
                                for file_name in jsonl_edge_files]
        json_node_iterators = [storage.json_iter(file_name, 'nodes')
                               for file_name in json_format_files]
        json_edge_iterators = [storage.json_iter(file_name, 'edges')
                               for file_name in json_format_files]
        all_node_iterators = json_node_iterators + jsonl_node_iterators
        all_edge_iterators = json_edge_iterators + jsonl_edge_iterators

        # chain the iterators together
        node_iterators = chain(*all_node_iterators)
        edge_iterators = chain(*all_edge_iterators)

        # now do the merge
        self.merger.merge_nodes(node_iterators)
        merged_nodes = self.merger.get_merged_nodes_jsonl()

        self.merger.merge_edges(edge_iterators)
        merged_edges = self.merger.get_merged_edges_jsonl()

        write_merge_metric = {}
        t = time.time()
        start_nodes_jsonl = time.time()
        nodes_file_path = storage.merge_path("nodes.jsonl")

        # stream out nodes to nodes.jsonl file
        with open(nodes_file_path, 'w') as stream:
            for nodes in merged_nodes:
                stream.write(nodes)

        time_difference = time.time() - start_nodes_jsonl
        log.info("writing nodes took : %s", str(time_difference))
        write_merge_metric['nodes_writing_time'] = time_difference
        start_edge_jsonl = time.time()

        # stream out edges to edges.jsonl file
        edges_file_path = storage.merge_path("edges.jsonl")
        with open(edges_file_path, 'w') as stream:
            for edges in merged_edges:
                edges = json.loads(edges)
                # Add an id field for the edges as some of the downstream
                # processing expects it.
                edges['id'] = xxh64_hexdigest(
                    edges['subject'] + edges['predicate'] +
                    edges['object'] +
                    edges.get("biolink:primary_knowledge_source", ""))
                keys_to_del = set()
                for key in edges:
                    if key.startswith('biolink:'):                        
                        keys_to_del.add(key)
                for k in keys_to_del:
                    edges[k.replace('biolink:', '')] = edges[k]
                    del edges[k]
                stream.write(json.dumps(edges).decode('utf-8') + '\n')

        write_merge_metric['edges_writing_time'] = time.time() - start_edge_jsonl
        log.info(f"writing edges took: {time.time() - start_edge_jsonl}")
        write_merge_metric['total_time'] = time.time() - t
        metrics['write_jsonl'] = write_merge_metric
        metrics['total_time'] = time.time() - start
        log.info(f"total took: {time.time() - start}")
        if self.enable_metrics:
            metricsfile_path = storage.metrics_path('merge_metrics.yaml')
            storage.write_object(metrics, metricsfile_path)
