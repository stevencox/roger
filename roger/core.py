import argparse
import glob
import json
import os
import requests
import shutil
import time
import yaml
import sys
import traceback
from collections import defaultdict
from enum import Enum
from kgx.cli import redisgraph_upload
from roger.config import get_logger, get_config
from biolink import model

log = get_logger ()
config = get_config ()
data_root = config['data_root']
    
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
                yaml.dump (obj, stream)
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
        return os.path.join (data_root, "schema", name)

    @staticmethod
    def bulk_path (name):
        """ Path to a bulk load object.
        :param name: Name of the object. """
        return os.path.join (data_root, "bulk", name)

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

class KGXModel:
    """ Abstractions for transforming Knowledge Graph Exchange formatted data. """
    def __init__(self, biolink):
        self.biolink = biolink
        
    def get (self, dataset_version = "v0.1"):
        """ Read metadata for edge and node files, then join them into whole KGX objects
        containing both nodes and edges. 
        :param dataset_version: Data version to operate on.
        """
        metadata = Util.read_object ("metadata.yaml", key="data_root")
        for item in metadata['versions']:
            if item['version'] == dataset_version:
                for edge_url in item['edgeFiles']:                    
                    start = Util.current_time_in_millis ()
                    edge_url = Util.get_uri (edge_url, "base_data_uri")
                    node_url = edge_url.replace ("-edge-", "-node-")
                    subgraph_basename = os.path.basename (edge_url.replace ("-edge", ""))
                    subgraph_path = Util.kgx_path (subgraph_basename)
                    if os.path.exists (subgraph_path):
                        log.info (f"using cached graph: {subgraph_path}")
                        continue
                    subgraph = {
                        "edges" : Util.read_object (edge_url),
                        "nodes" : Util.read_object (node_url)
                    }
                    Util.write_object (subgraph, subgraph_path)
                    total_time = Util.current_time_in_millis () - start
                
                    edges = len(subgraph['edges'])
                    nodes = len(subgraph['nodes'])
                    #log.debug (f"Wrote {subgraph_path}: edges:{edges}, nodes: {nodes} time:{total_time}")
                    log.debug ("Wrote {:>45}: edges:{:>7} nodes: {:>7} time:{:>8}".format (
                        subgraph_path, edges, nodes, total_time))

    def create_schema (self):
        """
        Determine the schema of each type of object. We have to do this to make it possible
        to write tabular data. Need to know all possible columns in advance and correct missing
        fields.
        """
        predicate_schemas = defaultdict(lambda:None)
        category_schemas = defaultdict(lambda:None)
        for subgraph in Util.kgx_objects ():
            """ Read a kgx data file. """
            log.debug (f"analyzing schema of {subgraph}.")
            basename = os.path.basename (subgraph).replace (".json", "")
            graph = Util.read_object (subgraph)
            """ Infer predicate schemas. """
            for edge in graph['edges']:
                predicate = edge['edge_label']
                if not predicate in predicate_schemas:
                    predicate_schemas[predicate] = edge
                    for k in edge.keys ():
                        edge[k] = ''
                else:
                    for k in edge.keys ():
                        if not k in predicate_schemas[predicate]:
                            predicate_schemas[predicate][k] = ''
            """ Infer node schemas. """
            for node in graph['nodes']:
                node_type = self.biolink.get_leaf_class (node['category'])
                if not node_type in category_schemas:
                    category_schemas[node_type] = node
                    for k in node.keys ():
                        node[k] = ''
                else:
                    for k in node.keys ():
                        if not k in category_schemas[node_type]:
                            category_schemas[node_type][k] = ''
        """ Write node and predicate schemas. """
        self.write_schema (predicate_schemas, SchemaType.PREDICATE)
        self.write_schema (category_schemas, SchemaType.CATEGORY)

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
            if os.path.exists (new_path):
                log.info (f"using cached merge: {new_path}")
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
                    path_2, load_time, scope_time, merge_time))
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

    def write_schema (self, schema, schema_type: SchemaType):
        """ Output the schema file. 
        :param schema: Schema to get keys from.
        :param schema_type: Type of schema to write. """
        file_name = Util.schema_path (f"{schema_type.value}-schema.json")
        log.info (f"writing schema: {file_name}")
        dictionary = { k : self.format_keys(v.keys(), schema_type)  for k, v in schema.items () }
        Util.write_object (dictionary, file_name)

    def load (self):
        """ Use KGX to load a data set into Redisgraph """
        input_format = "json"
        uri = f"redis://{config['redisgraph']['host']}:{config['redisgraph']['ports']['http']}/"
        username = config['redisgraph']['username']
        password = config['redisgraph']['password']
        log.info (f"connecting to redisgraph: {uri}")
        for subgraph in glob.glob (f"{kgx_repo}/**.json"):
            redisgraph_upload(inputs=[ subgraph ],
                              input_format=input_format,
                              input_compression=None,
                              uri=uri,
                              username=username,
                              password=password,
                              node_filters=[],
                              edge_filters=[])

class BiolinkModel:
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

    def get_leaf_class (self, names):
        """ Return the leaf classes in the provided list of names. """
        classes = [ self.get_class(self.to_camel_case(n)) for n in names ]
        leaves = [ n for n in names if not self.is_derived (n, classes) ]
        return leaves [0]

class BulkLoad:
    """ Tools for creating a Redisgraph bulk load dataset. """
    def __init__(self, biolink):
        self.biolink = biolink
        
    def create (self):
        """ Format the data for bulk load. """
        predicates_schema = Util.read_schema (SchemaType.PREDICATE)
        categories_schema = Util.read_schema (SchemaType.CATEGORY)
        bulk_path = Util.bulk_path("")
        if os.path.exists(bulk_path): 
            shutil.rmtree(bulk_path)

        state = defaultdict(lambda:None)
#        for subgraph in Util.kgx_objects ():
        for subgraph in Util.merged_objects ():
            log.info (f"processing {subgraph}")
            graph = Util.read_object (subgraph)

            """ Write node data for bulk load. """
            categories = defaultdict(lambda: [])
            for node in graph['nodes']:
                index = self.biolink.get_leaf_class (node['category'])
                categories[index].append (node)
            self.write_bulk (Util.bulk_path("nodes"), categories, categories_schema,
                        state=state, f=subgraph)

            """ Write predicate data for bulk load. """
            predicates = defaultdict(lambda: [])
            for edge in graph['edges']:
                predicates[edge['edge_label']].append (edge)
                edge['src'] = edge.pop ('subject')
                edge['dest'] = edge.pop ('object')
            self.write_bulk (Util.bulk_path("edges"), predicates, predicates_schema)
            
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
    
    def write_bulk (self, bulk_path, obj_map, schema, state={}, f=None):
        """ Write a bulk load group of objects.
        :param bulk_path: Path to the bulk loader object to write.
        :param obj_map: A map of biolink type to list of objects.
        :param schema: The schema (nodes or predicates) containing identifiers.
        :param state: Track state of already written objects to avoid duplicates.
        """
        os.makedirs (bulk_path, exist_ok=True)
        for key, objects in obj_map.items ():
            out_file = f"{bulk_path}/{key}.csv"
            if len(objects) == 0:
                continue
            new_file = not os.path.exists (out_file)
            all_keys = schema[key]
            with open (out_file, "a") as stream:
                if new_file:
                    log.info (f"  --creating {out_file}")
                    stream.write ("|".join (all_keys))
                    stream.write ("\n")
                """ Make all objects conform to the schema. """
                for obj in objects:
                    for akey in all_keys:
                        if not akey in obj:
                            obj[akey] = ""
                """ Write fields, skipping duplicate objects. """
                for obj in objects:
                    oid = str(obj['id'])
                    if oid in state:
                        continue
                    state[oid] = oid
                    values = [ self.cleanup(obj[k]) for k in all_keys if not 'smiles' in k ]
                    clean = list(map(str, values))
                    s = "|".join (clean)
                    stream.write (s)
                    stream.write ("\n")
                
if __name__ == "__main__":
    """ Roger CLI. """
    parser = argparse.ArgumentParser(description='Roger')
    parser.add_argument('-b', '--create-bulk', help="Create bulk load", action='store_true')
    parser.add_argument('-s', '--create-schema', help="Infer schema", action='store_true')
    parser.add_argument('-g', '--get-kgx', help="Get KGX objects", action='store_true')
    parser.add_argument('-l', '--load-kgx', help="Load via KGX", action='store_true')
    parser.add_argument('-m', '--merge-kgx', help="Merge KGX nodes", action='store_true')
    parser.add_argument('-v', '--dataset-version', help="Dataset version.", default="v0.1")
    args = parser.parse_args ()

    biolink = BiolinkModel ()
    kgx = KGXModel (biolink)
    bulk = BulkLoad (biolink)
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

    sys.exit (0)
