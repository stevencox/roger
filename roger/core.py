import argparse
import glob
import json
import os
import ntpath
import redis
import requests
import shutil
import sys
import time
import yaml
from bmt import Toolkit
from collections import defaultdict
from enum import Enum
from io import StringIO
from roger.Config import get_default_config as get_config
from roger.roger_util import get_logger
from roger.components.data_conversion_utils import TypeConversionUtil
from redisgraph_bulk_loader.bulk_insert import bulk_insert
from roger.roger_db import RedisGraph
from string import Template

log = get_logger ()
config = get_config ()

class SchemaType(Enum):
    """ High level semantic metatdata concepts.
    Categories are classes in an ontological model like Biolink.
    Predicates are links between nodes. """
    CATEGORY = "category"
    PREDICATE = "predicate"
    
class FileFormat(Enum):
    """ File formats this module knows about. """
    JSON = "json"
    YAML = "yaml"

# @TODO move this to shared file between dug , roger etc...
class Util:

    @staticmethod
    def current_time_in_millis():
        """
        Get current time in milliseconds.
        
        Returns
        -------
        int
        Time in milliseconds
        
        """
        return int(round(time.time() * 1000))

    """ A just do it approach to getting data. """
    @staticmethod
    def read_file(path):
        """ Read a file. 
        :param path: Path to a file.
        """
        text = None
        with open(path, "r") as stream:
            text = stream.read ()
        return text
    
    @staticmethod
    def read_url(url):
        """ Read data from a URL.
        :param url: The URL to read. """
        return requests.get (url).text
    
    @staticmethod
    def read_data(path):
        """ Read data from a URL or File. HTTP(S) is the only supported protocol.
        :param path: A URL or file path. """
        text = None
        if Util.is_web(path):
            text = Util.read_url (path)
        else:
            text = Util.read_file (path)
        return text
    
    @staticmethod
    def read_object(path, key=None):
        """ Read on object from a path. 
        :param path: A URL or file path. Supports YAML and JSON depending on extension.
        :param key: A configuration key. This is prepended to the path if present.
        :raises ValueError: If the key is not in the configuration. """
        if key is not None:
            prefix = config[key]
            path = f"{prefix}/{path}" if Util.is_web(prefix) \
                else os.path.join (prefix, path)
        obj = None
        if path.endswith (".yaml") or path.endswith (".yml"):
            obj = yaml.safe_load (Util.read_data (path))
        elif path.endswith (".json"):
            obj = json.loads (Util.read_data (path))
        return obj

    @staticmethod
    def is_web (uri):
        """ The URI is a web URI (starts with http or https).
        :param uri: A URI """
        return uri.startswith("http://") or uri.startswith ("https://")
    
    @staticmethod
    def write_object (obj, path, key=None):
        """ Write an object to a path. YAML and JSON supported based on extension.
        :param obj: The object to write.
        :param path: The path to write to.
        :param key: The configuration key to prepend to the path.
        """
        """ Prepend a prefix from the configuration file if a key is given. """
        if key is not None:
            prefix = config[key]
            path = f"{prefix}/{path}" if Util.is_web(prefix) \
                else os.path.join (prefix, path)
        """ Ensure the directory to be written to exists. """
        dirname = os.path.dirname (path)
        if not os.path.exists (dirname):
            os.makedirs (dirname, exist_ok=True)
        """ Write the file in the specified format. """
        if path.endswith (".yaml") or path.endswith (".yml"):
            with open(path, 'w') as outfile:
                yaml.dump (obj, outfile)
        elif path.endswith (".json"):
            with open (path, "w") as stream:
                json.dump (obj, stream, indent=2)
        else:
            """ Raise an exception if invalid. """
            raise ValueError (f"Unrecognized extension: {path}")

    @staticmethod
    def kgx_path (name):
        """ Form a KGX object path.
        :path name: Name of the KGX object. """
        data_root = get_config()['data_root']
        return os.path.join (data_root, "kgx", name)

    @staticmethod
    def kgx_objects ():
        """ A list of KGX objects. """
        kgx_pattern = Util.kgx_path("**.json")
        return sorted(glob.glob (kgx_pattern))
    
    @staticmethod
    def merge_path (name):
        """ Form a merged KGX object path.
        :path name: Name of the merged KGX object. """
        data_root = get_config()['data_root']
        return os.path.join (data_root, "merge", name)

    @staticmethod
    def merged_objects ():
        """ A list of merged KGX objects. """
        merged_pattern = Util.merge_path("**.json")
        return sorted(glob.glob (merged_pattern))
        
    @staticmethod
    def schema_path (name):
        """ Path to a schema object.
        :param name: Name of the object to get a path for. """
        data_root = get_config()['data_root']
        return os.path.join (data_root, "schema", name)

    @staticmethod
    def bulk_path (name):
        """ Path to a bulk load object.
        :param name: Name of the object. """
        data_root = get_config()['data_root']
        return os.path.join (data_root, "bulk", name)

    @staticmethod
    def dug_kgx_path(name):
        data_root = get_config()['data_root']
        return os.path.join (data_root, "dug", "kgx",  name)

    @staticmethod
    def dug_annotation_path(name):
        data_root = get_config()['data_root']
        return os.path.join(data_root, "dug", "annotations", name)

    @staticmethod
    def dug_crawl_path(name):
        data_root = get_config()['data_root']
        return os.path.join(data_root, "dug", "crawl", name)

    @staticmethod
    def dug_kgx_objects():
        """ A list of dug KGX objects. """
        dug_kgx_pattern = Util.dug_kgx_path("**.json")
        return sorted(glob.glob(dug_kgx_pattern))

    @staticmethod
    def dug_annotation_objects():
        """ A list of dug annotation Objects. """
        annotation_pattern = Util.dug_annotation_path("**.json")
        return sorted(glob.glob(annotation_pattern))

    @staticmethod
    def dug_topmed_path(name):
        """ Topmed source files"""
        home = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(home, "..", "dug_helpers", "dug_data", "topmed_data", name)

    @staticmethod
    def dug_topmed_objects():
        topmed_file_pattern = Util.dug_topmed_path("topmed_*.csv")
        return sorted(glob.glob(topmed_file_pattern))

    @staticmethod
    def dug_dd_xml_path(name):
        """ Topmed source files"""
        home = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(home, "..", "dug_helpers", "dug_data", "dd_xml_data", name)

    @staticmethod
    def dug_dd_xml_objects():
        topmed_file_pattern = Util.dug_dd_xml_path("*.xml")
        return sorted(glob.glob(topmed_file_pattern))

    @staticmethod
    def copy_file_to_dir(file_location, dir_name):
        return shutil.copy(file_location, dir_name)

    @staticmethod
    def read_schema (schema_type: SchemaType):
        """ Read a schema object.
        :param schema_type: Schema type of the object to read. """
        path = Util.schema_path (f"{schema_type.value}-schema.json")
        return Util.read_object (path)
    
    @staticmethod
    def get_uri (path, key):
        """ Build a URI.
        :param path: The path of an object.
        :param key: The key of a configuration value to prepend to the object. """
        return f"{config[key]}/{path}"

    @staticmethod
    def get_relative_path (path):
        return os.path.join (os.path.dirname (__file__), path)

    @staticmethod
    def read_relative_object (path):
        return Util.read_object (Util.get_relative_path(path))

    @staticmethod
    def trunc(text, limit):
        return ('..' + text[-limit-2:]) if len(text) > limit else text

    @staticmethod
    def is_up_to_date (source, targets):
        target_time_list = [ os.stat (f).st_mtime for f in targets if os.path.exists(f) ]
        if len(target_time_list) == 0:
            log.debug (f"no targets found")
            return False
        source = [ os.stat (f).st_mtime for f in source if os.path.exists (f) ]
        if len(source) == 0:
            log.debug ("no source found. up to date")
            return True
        return max(source) < min(target_time_list)
        
class KGXModel:
    """ Abstractions for transforming Knowledge Graph Exchange formatted data. """
    def __init__(self, biolink, config=None):
        if not config:
            config = get_config()
        self.config = config
        self.biolink_version = self.config.get('kgx').get('biolink_model_version')
        log.debug(f"Trying to get biolink version : {self.biolink_version}")
        self.biolink = BiolinkModel(self.biolink_version)

    def get (self, dataset_version = "v1.0"):
        """ Read metadata for KGX files and downloads them locally.
        :param dataset_version: Data version to operate on.
        """
        metadata = Util.read_relative_object ("metadata.yaml")
        for item in metadata['versions']:
            if item['version'] == dataset_version:
                log.info(f"Getting KGX file version {item['version']}")
                for file_name in item['files']:
                    start = Util.current_time_in_millis ()
                    file_url = Util.get_uri (file_name, "base_data_uri")
                    subgraph_basename = os.path.basename (file_name)
                    subgraph_path = Util.kgx_path (subgraph_basename)
                    if os.path.exists (subgraph_path):
                        log.info (f"cached kgx: {subgraph_path}")
                        continue
                    subgraph = Util.read_object(file_url)
                    Util.write_object (subgraph, subgraph_path)
                    total_time = Util.current_time_in_millis () - start
                    edges = len(subgraph['edges'])
                    nodes = len(subgraph['nodes'])
                    log.debug ("wrote {:>45}: edges:{:>7} nodes: {:>7} time:{:>8}".format (
                        Util.trunc(subgraph_path, 45), edges, nodes, total_time))
        # Fetchs kgx generated from Dug Annotation workflow.
        self.fetch_dug_kgx()

    def fetch_dug_kgx(self):
        """
        Copies files from dug output dir to roger kgx dir.
        :return:
        """
        dug_kgx_files = Util.dug_kgx_objects()
        log.info(f"Coping dug KGX files to {Util.kgx_path('')}. Found {len(dug_kgx_files)} kgx files to copy.")
        for file in dug_kgx_files:
            file_name = ntpath.basename(file)
            dest = Util.kgx_path(file_name)
            Util.write_object({}, dest)
            log.info(f"Copying from {file} to {dest}.")
            Util.copy_file_to_dir(file, dest)
        log.info("Done coping dug KGX files.")
        return

    def create_schema (self):
        """
        Determine the schema of each type of object. We have to do this to make it possible
        to write tabular data. Need to know all possible columns in advance and correct missing
        fields.
        """
        if self.schema_up_to_date():
            log.info (f"schema is up to date.")
            return

        predicate_schemas = defaultdict(lambda:None)
        category_schemas = defaultdict(lambda:None)        
        for subgraph in Util.kgx_objects ():
            """ Read a kgx data file. """
            log.debug (f"analyzing schema of {subgraph}.")
            basename = os.path.basename (subgraph).replace (".json", "")
            graph = Util.read_object (subgraph)
            """ Infer predicate schemas. """
            for edge in graph['edges']:
                predicate = edge['predicate']
                predicate_schemas[predicate] = predicate_schemas.get(predicate, {})
                for k in edge.keys ():
                    current_type = type(edge[k]).__name__
                    if k not in predicate_schemas[predicate]:
                        predicate_schemas[predicate][k] = current_type
                    else:
                        previous_type = predicate_schemas[predicate][k]
                        predicate_schemas[predicate][k] = TypeConversionUtil.compare_types(previous_type, current_type)
            """ Infer node schemas. """
            category_error_nodes = set()
            for node in graph['nodes']:
                if not node['category']:
                    category_error_nodes.add(node['id'])
                    node['category'] = [BiolinkModel.root_type]
                node_type = self.biolink.get_leaf_class (node['category'])
                category_schemas[node_type] = category_schemas.get(node_type, {})
                for k in node.keys ():
                    current_type = type(node[k]).__name__
                    if  k not in category_schemas[node_type]:
                        category_schemas[node_type][k] = current_type
                    else:
                        previous_type = category_schemas[node_type][k]
                        category_schemas[node_type][k] = TypeConversionUtil.compare_types(previous_type, current_type)
            if len(category_error_nodes):
                log.warn(f"some nodes didn't have category assigned. KGX file has errors."
                          f"Nodes {len(category_error_nodes)}."
                          f"Showing first 10: {list(category_error_nodes)[:10]}."
                          f"These will be treated as {BiolinkModel.root_type}.")
        """ Write node and predicate schemas. """
        self.write_schema (predicate_schemas, SchemaType.PREDICATE)
        self.write_schema (category_schemas, SchemaType.CATEGORY)

    def schema_up_to_date (self):
        return Util.is_up_to_date (
            source=Util.kgx_objects (),
            targets=[
                Util.schema_path (f"{SchemaType.PREDICATE.value}-schema.json"),
                Util.schema_path (f"{SchemaType.PREDICATE.value}-schema.json")
            ])
                
    def write_schema (self, schema, schema_type: SchemaType):
        """ Output the schema file. 
        :param schema: Schema to get keys from.
        :param schema_type: Type of schema to write. """
        file_name = Util.schema_path (f"{schema_type.value}-schema.json")
        log.info (f"writing schema: {file_name}")
        dictionary = { k : v for k, v in schema.items () }
        Util.write_object (dictionary, file_name)
        
    def merge_nodes (self, L, R):
        for k in L.keys ():
            R_v = R.get (k, None)
            if R_v == '' or R_v == None:
                L[k] = R_v

    def diff_lists (self, L, R):
        return list(list(set(L)-set(R)) + list(set(R)-set(L)))

    def merge (self):
        """ Merge nodes. Would be good to have something less computationally intensive. """
        for path in Util.kgx_objects ():
            new_path = path.replace ('/kgx/', '/merge/')

            source_stats = os.stat (path)
            if os.path.exists (new_path):
                dest_stats = os.stat (new_path)
                if dest_stats.st_mtime > source_stats.st_mtime:
                    log.info (f"merge {new_path} is up to date.")
                    continue

            log.info (f"merging {path}")
            graph = Util.read_object (path)
            graph_nodes = graph.get ('nodes', [])
            graph_map = { n['id'] : n for n in graph_nodes }
            graph_keys = graph_map.keys ()
            total_merge_time = 0
            for path_2 in Util.kgx_objects ():
                if path_2 == path:
                    continue
                start = Util.current_time_in_millis ()
                other_graph = Util.read_object (path_2)
                load_time = Util.current_time_in_millis () - start

                start = Util.current_time_in_millis ()                
                other_nodes = other_graph.get('nodes', [])
                other_map = { n['id'] : n for n in other_nodes }
                other_keys = set(other_map.keys())
                intersection = [ v for v in graph_keys if v in other_keys ]
                difference = list(set(other_keys) - set(graph_keys))
                scope_time = Util.current_time_in_millis () - start
                
                start = Util.current_time_in_millis ()
                for i in intersection:
                    self.merge_nodes (graph_map[i], other_map[i])
                other_graph['nodes'] = [ other_map[i] for i in difference ]
                merge_time = Util.current_time_in_millis () - start
                
                start = Util.current_time_in_millis ()
                Util.write_object (other_graph, path_2.replace ('kgx', 'merge'))
                write_time = Util.current_time_in_millis () - start
                log.debug ("merged {:>45} load:{:>5} scope:{:>7} merge:{:>3}".format(
                    Util.trunc(path_2, 45), load_time, scope_time, merge_time))
                total_merge_time += load_time + scope_time + merge_time + write_time
                
            start = Util.current_time_in_millis ()
            Util.write_object (graph, new_path)
            rewrite_time = Util.current_time_in_millis () - start
            log.info (f"{path} rewrite: {rewrite_time}. total merge time: {total_merge_time}")

    def format_keys (self, keys, schema_type : SchemaType):
        """ Format schema keys. Make source and destination first in edges. Make
        id first in nodes. Remove keys for fields we can't yet represent.
        :param keys: List of keys.
        :param schema_type: Type of schema to conform to.
        """
        """ Sort keys. """
        k_list = sorted(keys)
        if schema_type == SchemaType.PREDICATE:
            """ Rename subject and object to src and dest """
            k_list.remove ('subject')
            k_list.remove ('object')
            k_list.insert (0, 'src')
            k_list.insert (1, 'dest')
        elif schema_type == SchemaType.CATEGORY:
            """ Make id the first field. Remove smiles. It causes ast parse errors. 
            TODO: update bulk loader to ignore AST on selected fields.
            """
            k_list.remove ('id')
            if 'simple_smiles' in k_list:
                k_list.remove ('simple_smiles')
            k_list.insert (0, 'id')
        return k_list


class BiolinkModel:
    root_type = 'biolink:NamedThing'

    def __init__(self, bl_version='1.5.0'):
        self.bl_url = f'https://raw.githubusercontent.com/biolink/biolink-model/{bl_version}/biolink-model.yaml'
        self.toolkit = Toolkit(self.bl_url)

    """ Programmatic model of Biolink. """
    def to_camel_case(self, snake_str):
        """ Convert a snake case string to camel case. """
        components = snake_str.split('_')
        return ''.join(x.title() for x in components)

    def get_class(self, name):
        """ Get a Python class from a string name. """
        return getattr(sys.modules["biolink.model"], name)

    def is_derived (self, a_class_name, classes):
        """ Return true if the class derives from any of the provided classes. """
        for c in classes:
            if isinstance (self.get_class(self.to_camel_case(a_class_name)), c):
                return True
        return False

    def find_biolink_leaves(self, biolink_concepts):
        """
        Given a list of biolink concepts, returns the leaves removing any parent concepts.
        :param biolink_concepts: list of biolink concepts
        :return: leave concepts.
        """
        ancestry_set = set()
        all_mixins_in_tree = set()
        all_concepts = set(biolink_concepts)
        # Keep track of things like "MacromolecularMachine" in current datasets
        # @TODO remove this and make nodes as errors
        unknown_elements = set()
        for x in all_concepts:
            current_element = self.toolkit.get_element(x)
            mixins = set()
            if current_element:
                if 'mixins' in current_element and len(current_element['mixins']):
                    for m in current_element['mixins']:
                        mixins.add(self.toolkit.get_element(m).class_uri)
            else:
                unknown_elements.add(x)
            ancestors = set(self.toolkit.get_ancestors(x, reflexive=False, formatted=True))
            ancestry_set = ancestry_set.union(ancestors)
            all_mixins_in_tree = all_mixins_in_tree.union(mixins)
        leaf_set = all_concepts - ancestry_set - all_mixins_in_tree - unknown_elements
        return leaf_set

    def get_leaf_class (self, names):
        """ Return the leaf classes in the provided list of names. """
        leaves = list(self.find_biolink_leaves(names))
        return leaves[0]

class BulkLoad:
    """ Tools for creating a Redisgraph bulk load dataset. """
    def __init__(self, biolink, config=None):
        self.biolink = biolink
        if not config:
            config = get_config()
        self.config = config
        separator = self.config.get('bulk_loader',{}).get('separator', '|')
        self.separator = chr(separator) if isinstance(separator, int) else separator

    def tables_up_to_date (self):
        return Util.is_up_to_date (
            source=[
                Util.schema_path (f"{SchemaType.PREDICATE.value}-schema.json"),
                Util.schema_path (f"{SchemaType.PREDICATE.value}-schema.json")
            ] + Util.merged_objects (),
            targets=glob.glob (Util.bulk_path ("nodes/**.csv")) + \
            glob.glob (Util.bulk_path ("edges/**.csv")))

    def create (self):
        """ Check source times. """
        if self.tables_up_to_date ():
            log.info ("up to date.")
            return
        
        """ Format the data for bulk load. """
        predicates_schema = Util.read_schema (SchemaType.PREDICATE)
        categories_schema = Util.read_schema (SchemaType.CATEGORY)
        bulk_path = Util.bulk_path("")
        if os.path.exists(bulk_path): 
            shutil.rmtree(bulk_path)

        state = defaultdict(lambda:None)
        for subgraph in Util.merged_objects ():
            log.info (f"processing {subgraph}")
            graph = Util.read_object (subgraph)

            """ Write node data for bulk load. """
            categories = defaultdict(lambda: [])
            category_error_nodes = set()
            for node in graph['nodes']:
                if not node['category']:
                    category_error_nodes.add(node['id'])
                    node['category'] = [BiolinkModel.root_type]
                index = self.biolink.get_leaf_class (node['category'])
                categories[index].append (node)
            if len(category_error_nodes):
                log.error(f"some nodes didn't have category assigned. KGX file has errors."
                          f"Nodes {len(category_error_nodes)}. They will be typed {BiolinkModel.root_type}"
                          f"Showing first 10: {list(category_error_nodes)[:10]}.")
            self.write_bulk (Util.bulk_path("nodes"), categories, categories_schema,
                        state=state, f=subgraph, is_relation=False)

            """ Write predicate data for bulk load. """
            predicates = defaultdict(lambda: [])
            for edge in graph['edges']:
                predicates[edge['predicate']].append (edge)
            self.write_bulk (Util.bulk_path("edges"), predicates, predicates_schema, is_relation=True)
            
    def cleanup (self, v):
        """ Filter problematic text. 
        :param v: A value to filter and clean.
        """
        if isinstance(v, list):
            v = [ self.cleanup(val) for val in v ]
        elif isinstance (v, str):
            """ Some values contain the CSV separator character. 'fix' that. """
            if len(v) > 1 and v[0] == '[' and v[-1] == ']':
                v = v.replace ("[", "@").replace ("]", "@") #f" {v}"
            v = v.replace ("|","^")
        return v

    @staticmethod
    def create_redis_schema_header(attributes: dict, is_relation=False):
        """
        Creates col headers for csv to be used by redis bulk loader by assigning redis types
        :param attributes: dictionary of data labels with values as python type strings
        :param separator: CSV separator
        :return: list of attributes where each item  is attributeLabel:redisGraphDataType
        """
        redis_type_conversion_map = {
            'str': 'STRING',
            'float': 'FLOAT',  # Do we need to handle double
            'int': 'INT',
            'bool': 'BOOL',
            'list': 'ARRAY'
        }
        col_headers = []
        format_for_redis = lambda label, typ: f'{label}:{typ}'
        for attribute, attribute_type in attributes.items():
            col_headers.append(format_for_redis(attribute, redis_type_conversion_map[attribute_type]))
        # Note this two fields are only important to bulk loader
        # they will not be members of the graph
        # https://github.com/RedisGraph/redisgraph-bulk-loader/tree/master#input-schemas
        if is_relation:
            col_headers.append('internal_start_id:START_ID')
            col_headers.append('internal_end_id:END_ID')
        # replace id:STRING with id:ID
        col_headers.append('id:ID')
        col_headers = list(filter(lambda x: x != 'id:STRING', col_headers))
        return col_headers

    @staticmethod
    def group_items_by_attributes_set(objects: list, processed_object_ids: set):
        """
        Groups items into a dictionary where the keys are sets of attributes set for all
        items accessed in that key.
        Eg. { set(id,name,category): [{id:'xx0',name:'bbb', 'category':['type']}....
        {id:'xx1', name:'bb2', category: ['type1']}] }
        :param objects: list of nodes or edges
        :param processed_object_ids: ids of object to skip since they are processed.
        :return: dictionary grouping based on set attributes
        """
        clustered_by_set_values = {}
        improper_keys = set()
        value_set_test = lambda x: True if (x is not None and x != [] and x != '') else False
        for obj in objects:
            # redis bulk loader needs columns not to include ':'
            # till backticks are implemented we should avoid these.
            key_filter = lambda k:  ':' not in k
            keys_with_values = frozenset([k for k in obj.keys() if value_set_test(obj[k]) and key_filter(k)])
            for key in [k for k in obj.keys() if obj[k] and not key_filter(k)]:
                improper_keys.add(key)
            # group by attributes that have values. # Why?
            # Redis bulk loader has one issue
            # imagine we have {'name': 'x'} , {'name': 'y', 'is_metabolite': true}
            # we have a common schema name:STRING,is_metabolite:BOOL
            # values `x, ` and `y,true` but x not having value for is_metabolite is not handled
            # well, redis bulk loader says we should give it default if we were to enforce schema
            # but due to the nature of the data assigning defaults is very not an option.
            # hence grouping data into several csv's might be the right way (?)
            if obj['id'] not in processed_object_ids:
                clustered_by_set_values[keys_with_values] = clustered_by_set_values.get(keys_with_values, [])
                clustered_by_set_values[keys_with_values].append(obj)
        return clustered_by_set_values, improper_keys

    def write_bulk(self, bulk_path, obj_map, schema, state={}, is_relation=False, f=None):
        """ Write a bulk load group of objects.
        :param bulk_path: Path to the bulk loader object to write.
        :param obj_map: A map of biolink type to list of objects.
        :param schema: The schema (nodes or predicates) containing identifiers.
        :param state: Track state of already written objects to avoid duplicates.
        """
        os.makedirs (bulk_path, exist_ok=True)
        processed_objects_id = state.get('processed_id', set())
        called_x_times = state.get('called_times', 0)
        called_x_times += 1
        for key, objects in obj_map.items ():
            if len(objects) == 0:
                continue
            all_keys = schema[key]
            """ Make all objects conform to the schema. """
            clustered_by_set_values, improper_redis_keys = self.group_items_by_attributes_set(objects,
                                                                                              processed_objects_id)

            if len(improper_redis_keys):
                log.warning(f"The following keys were skipped since they include conflicting `:`"
                            f" that would cause errors while bulk loading to redis."
                            f"{improper_redis_keys}")
            for index, set_attributes in enumerate(clustered_by_set_values.keys()):
                items = clustered_by_set_values[set_attributes]
                # When parted files are saved let the file names be collected here
                state['file_paths'] = state.get('file_paths', {})
                state['file_paths'][key] = state['file_paths'].get(key, {})
                out_file = state['file_paths'][key][set_attributes] = state['file_paths']\
                    .get(key, {})\
                    .get(set_attributes, '')
                # When calling write bulk , lets say we have processed some
                # chemicals from file 1 and we start processing file 2
                # if we are using just index then we might (rather will) end up adding
                # records to the wrong file so we need this to be unique as possible
                # by adding called_x_times , if we already found out-file from state obj
                # we are sure that the schemas match.

                # biolink:<TYPE> is not valid name so we need to remove :
                file_key = key.replace('biolink:', '')

                out_file = f"{bulk_path}/{file_key}.csv-{index}-{called_x_times}" if not out_file else out_file
                state['file_paths'][key][set_attributes] = out_file  # store back file name
                new_file = not os.path.exists(out_file)
                keys_for_header = {x: all_keys[x] for x in all_keys if x in set_attributes}
                redis_schema_header = self.create_redis_schema_header(keys_for_header, is_relation)
                with open(out_file, "a", encoding='utf-8') as stream:
                    if new_file:
                        state['file_paths'][key][set_attributes] = out_file
                        log.info(f"  --creating {out_file}")
                        stream.write(self.separator.join(redis_schema_header))
                        stream.write("\n")
                    else:
                        log.info(f"  --appending to {out_file}")
                    """ Write fields, skipping duplicate objects. """
                    for obj in items:
                        oid = str(obj['id'])
                        if oid in processed_objects_id:
                            continue
                        processed_objects_id.add(oid)
                        """ Add ID / START_ID / END_ID depending"""
                        internal_id_fields = {
                            'internal_id': obj['id']
                        }
                        if is_relation:
                            internal_id_fields.update({
                                'internal_start_id': obj['subject'],
                                'internal_end_id': obj['object']
                            })
                        obj.update(internal_id_fields)
                        values = []
                        # uses redis schema header to preserve order when writing lines out.
                        for column_name in redis_schema_header:
                            # last key is the type
                            obj_key = ':'.join(column_name.split(':')[:-1])
                            value = obj[obj_key]

                            if obj_key not in internal_id_fields:
                                current_type = type(value).__name__
                                expected_type = all_keys[obj_key]
                                # cast it if it doesn't match type in schema keys i.e all_keys
                                value = TypeConversionUtil.cast(obj[obj_key], all_keys[obj_key]) \
                                    if expected_type != current_type else value

                            values.append(str(value))
                        s = self.separator.join(values)
                        stream.write(s)
                        stream.write("\n")
        state['processed_id'] = processed_objects_id
        state['called_times'] = called_x_times

    def insert (self):
        redisgraph = self.config.get('redisgraph', {})
        bulk_loader = self.config.get('bulk_loader', {})
        nodes = sorted(glob.glob (Util.bulk_path ("nodes/**.csv*")))
        edges = sorted(glob.glob (Util.bulk_path ("edges/**.csv*")))
        graph = redisgraph['graph']
        log.info(f"bulk loading \n  nodes: {nodes} \n  edges: {edges}")

        try:
            log.info (f"deleting graph {graph} in preparation for bulk load.")
            db = self.get_redisgraph (redisgraph)
            db.redis_graph.delete ()
        except redis.exceptions.ResponseError:
            log.info ("no graph to delete")
            
        log.info (f"bulk loading graph: {graph}")        
        args = []
        if len(nodes) > 0:
            bulk_path_root = Util.bulk_path('nodes') + os.path.sep
            nodes_with_type = [ f"biolink:{ x.replace(bulk_path_root, '').split('.')[0]} {x}"
                                for x in nodes ]
            args.extend(("-N " + " -N ".join(nodes_with_type)).split())
        if len(edges) > 0:
            bulk_path_root = Util.bulk_path('edges') + os.path.sep
            edges_with_type = [ f"biolink:{x.replace(bulk_path_root, '').strip(os.path.sep).split('.')[0]} {x}"
                               for x in edges]
            args.extend(("-R " + " -R ".join(edges_with_type)).split())
        args.extend([f"--separator={self.separator}"])
        args.extend([f"--host={redisgraph['host']}"])
        args.extend([f"--port={redisgraph['port']}"])
        args.extend([f"--password={redisgraph['password']}"])
        args.extend(['--enforce-schema'])
        args.extend([f"{redisgraph['graph']}"])
        """ standalone_mode=False tells click not to sys.exit() """
        bulk_insert (args, standalone_mode=False)

    def get_redisgraph (self, redisgraph):
        return RedisGraph (host=redisgraph['host'],
                           port=redisgraph['port'],
                           password=redisgraph.get('password', ''),
                           graph=redisgraph['graph'])
    
    def validate (self):
        redisgraph = self.config.get('redisgraph', {})
        print (f"config:{json.dumps(redisgraph, indent=2)}")
        db = self.get_redisgraph (redisgraph)
        validation_queries = config.get('validation', {}).get('queries', [])
        for key, query in validation_queries.items ():
            text = query['query']
            name = query['name']
            args = query.get('args', [{}])
            for arg in args:
                start = Util.current_time_in_millis ()
                instance = Template (text).safe_substitute (arg)
                db.query (instance)
                duration = Util.current_time_in_millis () - start
                log.info (f"Query {key}:{name} ran in {duration}ms: {instance}") 
            
class Roger:
    """ Consolidate Roger functionality for a cleaner interface. """

    def __init__(self, to_string=False, config=None):
        """ Initialize.
        :param to_string: Log messages to a string, available as self.log_stream.getvalue() 
        after execution completes.
        """
        import logging
        self.has_string_handler = to_string
        if not config:
            config = get_config()
        self.config = config
        if to_string:
            """ Add a stream handler to enable to_string. """
            self.log_stream = StringIO()
            self.string_handler = logging.StreamHandler (self.log_stream)
            log.addHandler (self.string_handler)
        self.biolink = BiolinkModel ()
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
            log.error ("{} {} {}".format (exception_type, exception_value, traceback))
        if self.has_string_handler:
            log.removeHandler (self.string_handler)
        
class RogerUtil:
    """ An interface abstracting Roger's inner workings to make it easier to
    incorporate into external tools like workflow engines. """
    @staticmethod
    def get_kgx (to_string=False, config=None):
        output = None
        log.debug("Getting KGX method called.")
        with Roger (to_string, config=config) as roger:
            roger.kgx.get ()
            output = roger.log_stream.getvalue () if to_string else None
        return output
    
    @staticmethod
    def create_schema (to_string=False, config=None):
        output = None
        with Roger (to_string, config=config) as roger:
            roger.kgx.create_schema ()
            output = roger.log_stream.getvalue () if to_string else None
        return output
    
    @staticmethod
    def merge_nodes (to_string=False, config=None):
        output = None
        with Roger (to_string, config=config) as roger:
            roger.kgx.merge ()
            output = roger.log_stream.getvalue () if to_string else None
        return output
    
    @staticmethod
    def create_bulk_load (to_string=False, config=None):
        output = None
        with Roger (to_string, config=config) as roger:
            roger.bulk.create ()
            output = roger.log_stream.getvalue () if to_string else None
        return output

    @staticmethod
    def bulk_load (to_string=False, config=None):
        output = None
        with Roger (to_string, config=config) as roger:
            roger.bulk.insert ()
            output = roger.log_stream.getvalue () if to_string else None
        return output

    @staticmethod
    def validate (to_string=False, config=None):
        output = None
        with Roger (to_string, config=config) as roger:
            roger.bulk.validate ()
            output = roger.log_stream.getvalue () if to_string else None
        return output

if __name__ == "__main__":
    """ Roger CLI. """
    parser = argparse.ArgumentParser(description='Roger')
    parser.add_argument('-v', '--dataset-version', help="Dataset version.", default="v1.0")
    parser.add_argument('-d', '--data-root', help="Root of data hierarchy", default=None)
    parser.add_argument('-g', '--get-kgx', help="Get KGX objects", action='store_true')
    parser.add_argument('-l', '--load-kgx', help="Load via KGX", action='store_true')
    parser.add_argument('-s', '--create-schema', help="Infer schema", action='store_true')
    parser.add_argument('-m', '--merge-kgx', help="Merge KGX nodes", action='store_true')
    parser.add_argument('-b', '--create-bulk', help="Create bulk load", action='store_true')
    parser.add_argument('-i', '--insert', help="Do the bulk insert", action='store_true')
    parser.add_argument('-a', '--validate', help="Validate the insert", action='store_true')
    args = parser.parse_args ()

    biolink = BiolinkModel ()
    kgx = KGXModel (biolink)
    bulk = BulkLoad (biolink)
    if args.data_root is not None:
        config = get_config()
        data_root = args.data_root
        config.update({'data_root': data_root})
        log.info (f"data root:{data_root}")
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
