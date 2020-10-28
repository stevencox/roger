import argparse
import glob
import json
import os
import requests
import shutil
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
    """ A just do it approach to getting data. """
    @staticmethod
    def read_file(path):
        text = None
        with open(path, "r") as stream:
            text = stream.read ()
        return text
    
    @staticmethod
    def read_url(url):
        return requests.get (url).text
    
    @staticmethod
    def read_data(path):
        text = None
        if Util.is_web(path):
            text = Util.read_url (path)
        else:
            text = Util.read_file (path)
        return text
    
    @staticmethod
    def read_object(path, key=None):
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
        return uri.startswith("http://") or uri.startswith ("https://")
    
    @staticmethod
    def write_object (obj, path, key=None, form:FileFormat=FileFormat.JSON):
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
        if form == FileFormat.JSON:
            with open (path, "w") as stream:
                json.dump (obj, stream, indent=2)
        elif form == FileFormat.YAML:
            with open(path, 'w') as outfile:
                yaml.dump (obj, stream)
        else:
            """ Raise an exception if invalid. """
            raise ValueError (f"Unknown format: {form}")

    @staticmethod
    def kgx_path (name):
        return os.path.join (data_root, "kgx", name)

    @staticmethod
    def kgx_objects ():
        kgx_pattern = Util.kgx_path("**.json")
        return sorted(glob.glob (kgx_pattern))
        
    @staticmethod
    def schema_path (name):
        return os.path.join (data_root, "schema", name)

    @staticmethod
    def bulk_path (name):
        return os.path.join (data_root, "bulk", name)

    @staticmethod
    def read_schema (schema_type: SchemaType):
        path = Util.schema_path (f"{schema_type.value}-schema.json")
        return Util.read_object (path)
    
    @staticmethod
    def get_uri (path, key):
        return f"{config[key]}/{path}"

class KGXModel:
    
    def __init__(self, biolink):
        self.biolink = biolink
        
    def get (self, dataset_version = "v0.1"):
        """ Read metadata for edge and node files, then join them into whole KGX objects
        containing both nodes and edges. 
        :param dataset_version: Data version to operate on.
        """
        metadata = Util.read_object ("metadata.yaml", key="data_root")
        log.debug (json.dumps (metadata, indent=2))
        for item in metadata['versions']:
            if item['version'] == dataset_version:
                for edge_url in item['edgeFiles']:
                    edge_url = Util.get_uri (edge_url, "base_data_uri")
                    node_url = edge_url.replace ("-edge-", "-node-")
                    subgraph_basename = os.path.basename (edge_url.replace ("-edge", ""))
                    subgraph_path = Util.kgx_path (subgraph_basename)
                    if os.path.exists (subgraph_path):
                        log.info (f"using cached graph: {subgraph_path}")
                        continue
                    log.debug (f"Getting edges: {edge_url}, nodes: {node_url}")
                    subgraph = {
                        "edges" : Util.read_object (edge_url),
                        "nodes" : Util.read_object (node_url)
                    }
                    Util.write_object (subgraph, subgraph_path)
                    edge_count = len(subgraph['edges'])
                    node_count = len(subgraph['nodes'])
                    log.debug (f"Wrote {subgraph_path}: edges: {edge_count}, nodes: {node_count}")
                    
    def create_schema (self):
        """
        Determine the schema of each type of object. We have to do this to make it possible
        to write tabular data. Need to know all possible columns in advance and correct missing
        fields.

        TODO: Need to merge duplicate nodes.
        """
        predicate_schemas = defaultdict(lambda:None)
        category_schemas = defaultdict(lambda:None)
        for subgraph in Util.kgx_objects ():
            """ Read a kgx data file. """
            basename = os.path.basename (subgraph).replace (".json", "")
            graph = Util.read_object (subgraph)
            """ Infer predicate schemas. """
            log.debug ("analyzing edge schemas.")
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
            log.debug ("analyzing node schemas.")
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

    def format_keys (self, keys, schema_type : SchemaType):
        """ Format schema keys. """
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
        """ Output the schema file. """
        file_name = Util.schema_path (f"{schema_type.value}-schema.json")
        log.info (f"writing schema: {file_name}")
        dictionary = { k : self.format_keys(v.keys(), schema_type)  for k, v in schema.items () }
        Util.write_object (dictionary, file_name)

    def load (self):
        """ Use KGX to load a data set. """
        input_format = "json"
        uri = f"redis://{config['redisgraph']['host']}:{config['redisgraph']['ports']['http']}/"
        username = config['redisgraph']['username']
        password = config['redisgraph']['password']
        log.info (f"connecting to redisgraph: {uri}")
        for subgraph in glob.glob (f"{kgx_repo}/**.json"):
            if 'pharos' in subgraph:
                continue
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

    def __init__(self, biolink):
        self.biolink = biolink
        
    def create (self):
        """ Format the data for bulk load. """
        predicates_schema = Util.read_schema (SchemaType.PREDICATE)
        categories_schema = Util.read_schema (SchemaType.CATEGORY)
        shutil.rmtree(Util.bulk_path(""))

        state = defaultdict(lambda:None)
        for subgraph in Util.kgx_objects ():
            """ TODO: do this incrementally now that we have a schema. """
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
        """ Filter problematic text. """
        if isinstance(v, list):
            v = [ self.cleanup(val) for val in v ]
        elif isinstance (v, str):
            """ Some values contain the CSV separator character. 'fix' that. """
            if len(v) > 1 and v[0] == '[' and v[-1] == ']':
                v = v.replace ("[", "@").replace ("]", "@") #f" {v}"
            v = v.replace ("|","^")
        return v
    
    def write_bulk (self, bulk_path, obj_map, schema, state={}, f=None):
        """ Write a bulk load group of objects. """
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
    """ The Roger CLI. """
    parser = argparse.ArgumentParser(description='Roger')
    parser.add_argument('-b', '--create-bulk', help="Create bulk load", action='store_true')
    parser.add_argument('-s', '--create-schema', help="Infer schema", action='store_true')
    parser.add_argument('-g', '--get-kgx', help="Get KGX objects", action='store_true')
    parser.add_argument('-l', '--load-kgx', help="Load via KGX", action='store_true')
    parser.add_argument('-v', '--dataset-version', help="Dataset version.", default="v0.1")
    args = parser.parse_args ()

    biolink = BiolinkModel ()
    kgx = KGXModel (biolink)
    bulk = BulkLoad (biolink)
    if args.get_kgx:
        kgx.get (dataset_version=args.dataset_version)
    if args.load_kgx:
        kgx.load ()
    if args.create_schema:
        kgx.create_schema ()
    if args.create_bulk:
        bulk.create ()

    sys.exit (0)
