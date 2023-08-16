import os

from roger.core.enums import SchemaType
import json

class BiolinkMock:
    def __init__(self):
        self.leafs = [
            'chemical_substance',
            'molecular_activity',
            'gene',
            'biological_process',
            'disease',
            'phenotypic_feature'
        ]

    def get_leaf_class(self, class_names):
        for y in self.leafs:
            if y in class_names:
                return y
        return class_names[0]

    def find_biolink_leaves(self, biolink_concepts):
        return set([concept for concept in biolink_concepts
                    if concept in ['named_thing', 'some_other_type']])

category = None
predicates = None
file_content_assertions = {}
kgx_files = []
merged_files = []
merge_file_test_dir = ''
schema = {
    SchemaType.PREDICATE: {},
    SchemaType.CATEGORY: {}
}

def kgx_objects():
    return [os.path.join(*os.path.split(__file__)[:-1], 'data', file)
            for file in kgx_files]

def merged_objects():
    return [os.path.join(*os.path.split(__file__)[:-1], 'data', file)
            for file in merged_files]

def bulk_path(*args, **kwargs):
    return os.path.join(*os.path.split(__file__)[:-1], 'data', 'bulk')

def is_up_to_date(*args, **kwargs):
    return False

def schema_path(name, *args, **kwargs):
    return name

def read_schema(schema_type: SchemaType, *args, **kwargs):
    return conftest.schema[schema_type]

def read_object(path, *args, **kwargs):
    import json
    with open(path) as f:
        return json.load(f)

def write_object(dictionary, file_name):
    print(dictionary, file_name)
    print(file_content_assertions)
    assert file_content_assertions[file_name] == dictionary

def merge_path(file_name):
    return os.path.join(*os.path.split(__file__)[:-1], 'data', 'merge',
                        merge_file_test_dir, file_name)

def json_line_iter(jsonl_file_path):
    f = open(file=jsonl_file_path, mode='r')
    for line in f:
        yield json.loads(line)
    f.close()
