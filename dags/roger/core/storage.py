""" utils for roger

This is home to the utilities that were formerly in dags/roger/core.py:Util
"""

import os
import glob
import time
import pathlib
import pickle
import shutil
import yaml
import orjson as json
import requests
from pathlib import Path

from roger.logger import get_logger
from roger.config import get_default_config as get_config
from roger.core import SchemaType

log = get_logger()
config = get_config()

data_dir_env_value = os.getenv("ROGER_DATA_DIR")

if data_dir_env_value is None:
    ROGER_DATA_DIR = Path(__file__).parent.resolve() / 'data'
else:
    ROGER_DATA_DIR = Path(data_dir_env_value)


def current_time_in_millis():
    """
    Get current time in milliseconds.

    Returns
    -------
    int
    Time in milliseconds

    """
    return int(round(time.time() * 1000))

# A just do it approach to getting data.
def read_file(path):
    """ Read a file.
    :param path: Path to a file.
    """
    text = None
    with open(path, "r", encoding='utf-8') as stream:
        text = stream.read()
    return text

def read_url(url):
    """ Read data from a URL.
    :param url: The URL to read. """
    return requests.get(url, timeout=60).text

def read_data(path):
    """ Read data from a URL or File. HTTP(S) is the only supported protocol.
    :param path: A URL or file path. """
    text = None
    if is_web(path):
        text = read_url(path)
    else:
        text = read_file(path)
    return text

def read_object(path, key=None):
    """ Read on object from a path.
    :param path: A URL or file path.
                 Supports YAML and JSON depending on extension.
    :param key: A configuration key. This is prepended to the path if present.
    :raises ValueError: If the key is not in the configuration. """
    if key is not None:
        prefix = config[key]
        path = f"{prefix}/{path}" if is_web(prefix) \
            else os.path.join (prefix, path)
    obj = None
    if path.endswith(".yaml") or path.endswith (".yml"):
        obj = yaml.safe_load (read_data (path))
    elif path.endswith(".json"):
        obj = json.loads (read_data (path))
    elif path.endswith(".pickle"):
        with open(file=path, mode="rb") as stream:
            obj = pickle.load(stream)
    elif path.endswith(".jsonl"):
        obj = read_data(path)
    return obj

def is_web (uri):
    """ The URI is a web URI (starts with http or https).
    :param uri: A URI """
    return uri.startswith("http://") or uri.startswith ("https://")

def write_object (obj, path, key=None):
    """ Write an object to a path. YAML and JSON supported based on extension.
    :param obj: The object to write.
    :param path: The path to write to.
    :param key: The configuration key to prepend to the path.
    """
    # Prepend a prefix from the configuration file if a key is given.
    if key is not None:
        prefix = config[key]
        path = (f"{prefix}/{path}" if is_web(prefix)
                else os.path.join (prefix, path))

    # Ensure the directory to be written to exists.
    dirname = os.path.dirname (path)
    if not os.path.exists (dirname):
        os.makedirs (dirname, exist_ok=True)

    # Write the file in the specified format.
    if path.endswith (".yaml") or path.endswith (".yml"):
        with open(path, 'w') as outfile:
            yaml.dump (obj, outfile)
    elif path.endswith (".json"):
        with open (path, "w", encoding='utf-8') as stream:
            stream.write(str(json.dumps (obj).decode('utf-8')))
    elif path.endswith(".pickle"):
        with open (path, "wb") as stream:
            pickle.dump(obj, file=stream)
    elif path.endswith(".jsonl"):
        with open (path, "w", encoding="utf-8") as stream:
            stream.write(obj)
    else:
        # Raise an exception if invalid.
        raise ValueError (f"Unrecognized extension: {path}")

def kgx_path(name):
    """ Form a KGX object path.
    :path name: Name of the KGX object. """
    return str(ROGER_DATA_DIR / "kgx" / name)

def kgx_objects(format_="json"):
    """ A list of KGX objects. """
    kgx_pattern = kgx_path(f"**.{format_}")
    return sorted(glob.glob (kgx_pattern))

def merge_path(name):
    """ Form a merged KGX object path.
    :path name: Name of the merged KGX object. """
    return str(ROGER_DATA_DIR / 'merge' / name)

def merged_objects():
    """ A list of merged KGX objects. """
    merged_pattern = merge_path("**.json")
    return sorted(glob.glob (merged_pattern))

def schema_path(name):
    """ Path to a schema object.
    :param name: Name of the object to get a path for. """
    return str(ROGER_DATA_DIR / 'schema' / name)

def bulk_path(name):
    """ Path to a bulk load object.
    :param name: Name of the object. """
    return str(ROGER_DATA_DIR / 'bulk' / name)

def metrics_path(name):
    """
    Path to write metrics to
    :param name:
    :return:
    """
    return str(ROGER_DATA_DIR / "metrics" / name)

def dug_kgx_path(name):
    return str(ROGER_DATA_DIR / "dug" / "kgx" / name)

def dug_annotation_path(name):
    return str(ROGER_DATA_DIR / "dug" / "annotations" / name)

def dug_expanded_concepts_path(name):
    return str(ROGER_DATA_DIR / 'dug' / 'expanded_concepts' / name)

def dug_expanded_concept_objects():
    file_pattern = dug_expanded_concepts_path(
        os.path.join('*','expanded_concepts.pickle'))
    return sorted(glob.glob(file_pattern))

def dug_extracted_elements_objects():
    file_pattern = dug_expanded_concepts_path(
        os.path.join('*', 'extracted_graph_elements.pickle'))
    return sorted(glob.glob(file_pattern))

def dug_crawl_path(name):
    return str(ROGER_DATA_DIR / 'dug' / 'crawl' / name)

def dug_kgx_objects():
    """ A list of dug KGX objects. """
    dug_kgx_pattern = dug_kgx_path("**.json")
    return sorted(glob.glob(dug_kgx_pattern))

def dug_concepts_objects():
    """ A list of dug annotation Objects. """
    concepts_file_path = dug_annotation_path(
        os.path.join('*','concepts.pickle'))
    return sorted(glob.glob(concepts_file_path))

def dug_elements_objects():
    """ A list of dug annotation Objects. """
    concepts_file_path = dug_annotation_path(
        os.path.join('*', 'elements.pickle'))
    return sorted(glob.glob(concepts_file_path))

def dug_input_files_path(name) -> pathlib.Path:
    path = ROGER_DATA_DIR / "dug" / "input_files" / name
    if not path.exists():
        log.info(f"Input file path: {path} does not exist, creating")
        path.mkdir(parents=True, exist_ok=True)
    else:
        log.info(f"Input file path: {path} already exists")
    return path

def mkdir(path, is_dir=False):
    directory = os.path.dirname(path) if not is_dir else path
    if not os.path.exists(directory):
        os.makedirs(directory)

def remove(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

def clear_dir(path):
    remove(path)
    mkdir(path, is_dir=True)

def dug_topmed_path(name):
    """ Topmed source files"""
    return dug_input_files_path('topmed') / name

def dug_topmed_objects():
    topmed_file_pattern = str(dug_topmed_path("topmed_*.csv"))
    return sorted(glob.glob(topmed_file_pattern))

def dug_nida_path(name):
    """ NIDA source files"""
    return dug_input_files_path('nida') / name

def dug_sparc_path(name):
    """ NIDA source files"""
    return dug_input_files_path('sparc') / name

def dug_anvil_path():
    """Anvil source files"""
    return dug_input_files_path('anvil')

def dug_sprint_path():
    """Anvil source files"""
    return dug_input_files_path('sprint')

def dug_bacpac_path():
    """Anvil source files"""
    return dug_input_files_path('bacpac')

def dug_crdc_path():
    """Anvil source files"""
    return dug_input_files_path('crdc')

def dug_kfdrc_path():
    """Anvil source files"""
    return dug_input_files_path('kfdrc')

def dug_nida_objects():
    nida_file_pattern = str(dug_nida_path("NIDA-*.xml"))
    return sorted(glob.glob(nida_file_pattern))

def dug_sparc_objects():
    file_pattern = str(dug_sparc_path("scicrunch/*.xml"))
    return sorted(glob.glob(file_pattern))

def dug_anvil_objects():
    file_path = dug_anvil_path()
    files = get_files_recursive(
        lambda file_name: (
            not file_name.startswith('GapExchange_')
            and file_name.endswith('.xml')),
        file_path)
    return sorted([str(f) for f in files])

def dug_sprint_objects():
    file_path = dug_sprint_path()
    files = get_files_recursive(
        lambda file_name: file_name.endswith('.xml'), file_path)
    return sorted([str(f) for f in files])

def dug_bacpac_objects():
    file_path = dug_bacpac_path()
    files = get_files_recursive(
        lambda file_name: file_name.endswith('.xml'), file_path)
    return sorted([str(f) for f in files])

def dug_crdc_objects():
    file_path = dug_crdc_path()
    files = get_files_recursive(
        lambda file_name: (
            not file_name.startswith('GapExchange_')
            and file_name.endswith('.xml')),
        file_path)
    return sorted([str(f) for f in files])

def dug_kfdrc_objects():
    file_path = dug_kfdrc_path()
    files = get_files_recursive(
        lambda file_name: (
            not file_name.startswith('GapExchange_')
            and file_name.endswith('.xml')),
        file_path)
    return sorted([str(f) for f in files])


def dug_dd_xml_path():
    """ Topmed source files"""
    return dug_input_files_path('db_gap')

def get_files_recursive(file_name_filter, current_dir):
    file_paths = []
    for child in current_dir.iterdir():
        if child.is_dir():
            file_paths += get_files_recursive(file_name_filter, child)
            continue
        if not file_name_filter(child.name):
            continue
        else:
            file_paths += [child]
    return file_paths

def dug_dd_xml_objects():
    file_path = dug_dd_xml_path()
    files = get_files_recursive(
        lambda file_name: (
            not file_name.startswith('._')
            and file_name.endswith('.xml')),
        file_path)
    return sorted([str(f) for f in files])

def copy_file_to_dir(file_location, dir_name):
    return shutil.copy(file_location, dir_name)

def read_schema (schema_type: SchemaType):
    """ Read a schema object.
    :param schema_type: Schema type of the object to read. """
    path = schema_path (f"{schema_type.value}-schema.json")
    return read_object (path)

def get_uri (path, key):
    """ Build a URI.
    :param path: The path of an object.
    :param key: The key of a configuration value to prepend to the object. """
    # Incase config has http://..../ or http://... remove / and add back to
    # avoid double http://...//
    root_url = config[key].rstrip('/')
    return f"{root_url}/{path}"

def get_relative_path (path):
    return os.path.join (os.path.dirname (__file__), path)

def read_relative_object (path):
    return read_object (get_relative_path(path))

def trunc(text, limit):
    return ('..' + text[-limit-2:]) if len(text) > limit else text

def is_up_to_date (source, targets):
    target_time_list = [
        os.stat (f).st_mtime for f in targets if os.path.exists(f)]
    if len(target_time_list) == 0:
        log.debug (f"no targets found")
        return False
    source = [ os.stat (f).st_mtime for f in source if os.path.exists (f) ]
    if len(source) == 0:
        log.debug ("no source found. up to date")
        return True
    return max(source) < min(target_time_list)

def json_line_iter(jsonl_file_path):
    f = open(file=jsonl_file_path, mode='r', encoding='utf-8')
    for line in f:
        yield json.loads(line)
    f.close()

def jsonl_iter(file_name):
    # iterating over jsonl files
    with open(file_name) as stream:
        for line in stream:
            # yield on line at time
            yield json.loads(line)

def json_iter(json_file,entity_key):
    with open(json_file) as stream:
        data = json.loads(stream.read())
        return data[entity_key]

def downloadfile(thread_num, inputq, doneq):
    url = ""
    t0 = 0
    pct = 0

    def downloadprogress(blocknumber, readsize, totalfilesize):
        nonlocal thread_num
        nonlocal url, t0, pct
        blocks_expected = (
            int(totalfilesize/readsize) +
            (1 if totalfilesize%readsize != 0 else 0))
        t1 = int(current_time_in_millis()/1000)
        elapsed_delta = t1 - t0
        pct = int(100 * blocknumber / blocks_expected)
        if elapsed_delta >= 30: # every n seconds
            log.info(f"thread-{thread_num} {pct}% of size:{totalfilesize} "
                     f"({blocknumber}/{blocks_expected}) url:{url}")
            t0 = t1

    num_files_processed = 0
    while inputq.empty() is False:
        t0 = int(current_time_in_millis()/1000)
        url, dst = inputq.get()
        num_files_processed += 1
        log.info(f"thread-{thread_num} downloading {url}")
        try:
            path, httpMessage = urlretrieve(
                url, dst, reporthook=downloadprogress)
            if pct < 100:
                httpMessageKeys = httpMessage.keys()
                log.info(f"thread-{thread_num} urlretrieve path:'{path}' "
                         f"http-keys:{httpMessageKeys} "
                         f"httpMessage:'{httpMessage.as_string()}")
        except Exception as e:
            log.error(f"thread-{thread_num} downloadfile excepton: {e}")
            continue
        log.info(f"thread-{thread_num} downloaded {dst}")
    doneq.put((thread_num,num_files_processed))
    log.info(f"thread-{thread_num} done!")
    return
