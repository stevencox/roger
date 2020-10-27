import glob
import json
import os
import requests
import yaml
import sys
from collections import defaultdict
from kgx.cli import redisgraph_upload
from roger.config import get_logger, get_config
from biolink import model

log = get_logger ()

config = get_config ()

data_root = config['data_root']
kgx_repo = os.path.join (data_root, config['kgx_repo'])
    
def init ():
    if not os.path.exists (kgx_repo):
        os.makedirs (kgx_repo)

def grok (target_version = "v0.1"):
    data_root = config['local_cache']
    url = f"{data_root}/meta-data.yaml"
    text = requests.get (url).text 
    obj = yaml.safe_load (text)
    print (json.dumps (obj, indent=2))
    for item in obj['versions']:
        if item['version'] == target_version:
            for edge_set_url in item['edgeFiles']:
                edge_set_url = f"{data_root}/{edge_set_url}"
                node_set_url = edge_set_url.replace ("-edge-", "-node-")
                subgraph_path = os.path.join (
                    kgx_repo,
                    os.path.basename (
                        edge_set_url.replace ("-edge", "")))
                if os.path.exists (subgraph_path):
                    log.info (f"using cached graph: {subgraph_path}")
                    continue
                log.debug (f"loading edges: {edge_set_url}, nodes: {node_set_url}")
                subgraph = {
                    "edges" : requests.get (edge_set_url).json (),
                    "nodes" : requests.get (node_set_url).json ()
                }
                with open (subgraph_path, "w") as stream:
                    json.dump (subgraph, stream)
                log.debug (f"Wrote {subgraph_path}: edges: {len(subgraph['edges'])}, nodes: {len(subgraph['nodes'])}")

def get_schema_path (schema_type):
    schema_path = os.path.join (data_root, "schema")
    if not os.path.exists (schema_path):
        os.makedirs (schema_path)
    return os.path.join (schema_path, f"{schema_type}-schema.json")

def make_schema ():
    """
    Determine the schema of each type of object. We have to do this to make it possible
    to write tabular data. Need to know all possible columns in advance and correct missing
    fields.
    """
    predicate_schemas = {}
    category_schemas = {}
    for subgraph in glob.glob (f"{kgx_repo}/**.json"):
        basename = os.path.basename (subgraph).replace (".json", "")
        graph = None
        log.info (f"processing {subgraph}")
        with open (subgraph, "r") as stream:
            graph = json.load (stream)
        for edge in graph['edges']:
            predicate = edge['edge_label']
            if not predicate in edge_schema:
                predicate_schemas[predicate].append (edge)
            else:
                for k, v in edge:
                    if not k in predicate_schemas[predicate]:
                        predicate_schemas[predicate][k] = ''
        for node in graph['nodes']:
            node_type = get_leaf_class (node['category'])
            if not node_type in category_schemas:
                category_schemas[node_type].append (node)
            else:
                for k, v in edge:
                    if not k in category_schemas[node_type]:
                        category_schemas[node_type][k] = ''
        write_schema (predicate_schema, "predicate", schema_path)
        write_schema (predicate_schema, "category", schema_path)

def write_schema (schema, schema_type, schema_path):
    file_name = get_schema_path (schema_type)
    with open (file_name, "w") as stream:
        json.dump (schema, stream)
        
def format_bulk_load ():
    bulk_path = os.path.join (data_root, "bulk")
    if not os.path.exists (bulk_path):
        os.makedirs (bulk_path)
        os.makedirs (os.path.join (bulk_path, "nodes"))
        os.makedirs (os.path.join (bulk_path, "edges"))
    for subgraph in glob.glob (f"{kgx_repo}/**.json"):
        basename = os.path.basename (subgraph).replace (".json", "")
        graph = None
        log.info (f"processing {subgraph}")
        with open (subgraph, "r") as stream:
            graph = json.load (stream)

        categories = defaultdict(lambda: [])
        for node in graph['nodes']:
            index = get_leaf_class (node['category'])
            categories[index].append (node)
        write_bulk_group (f"{bulk_path}/nodes", categories)

        predicates = defaultdict(lambda: [])
        for edge in graph['edges']:
            predicates[edge['edge_label']].append (edge)
            edge['src'] = edge.pop ('subject')
            edge['dest'] = edge.pop ('object')
        write_bulk_group (f"{bulk_path}/edges", predicates)

def to_camel_case(snake_str):
    components = snake_str.split('_')
    # Capitalize the first letter of each component
    # with the 'title' method and join them together.
    return ''.join(x.title() for x in components)

def get_class(name):
    return getattr(sys.modules["biolink.model"], name)

def is_derived (a_class_name, classes):
    for c in classes:
        if isinstance (get_class(to_camel_case(a_class_name)), c):
            return True
    return False

def get_leaf_class (names):
    classes = [ get_class(to_camel_case(n)) for n in names ]
    leaves = [ n for n in names if not is_derived (n, classes) ]
    return leaves [0]

def cleanup (values):
    if '[SO2(OH)(SH)]' in values:
        log.info (f"--:{json.dumps(values, indent=2)}:--")
    def _cleanup (v):
        if len(v) > 1 and v[0] == '[' and v[-1] == ']':
            return f" {v}"
        return v
    return [ _cleanup(v) for v in values ]
    
def write_bulk_group (bulk_path, obj_map):
    for key, objects in obj_map.items ():
        all_keys = { k : k for obj in objects for k in obj.keys () }.keys ()
        out_file = f"{bulk_path}/{key}.csv"
        if len(objects) == 0:
            continue
        new_file = not os.path.exists (out_file)
        with open (out_file, "a") as stream:
            if new_file:
                log.info (f"  --creating {out_file}")
                stream.write ("|".join ( all_keys ))
                stream.write ("\n")
            for obj in objects:
                for key in all_keys:
                    if not key in obj:
                        obj[key] = ""
            for obj in objects:
                clean = cleanup(list(map(str, obj.values ())))
                s = "|".join (clean)
                stream.write (s)
                stream.write ("\n")
        
def load ():
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
init ()
grok ()
#load ()
format_bulk_load ()
