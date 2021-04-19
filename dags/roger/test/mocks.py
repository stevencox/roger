import os
from roger.core import SchemaType


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


class UtilMock:
    category = None
    predicates = None
    file_content_assertions = {}
    kgx_files = []
    merged_files = []
    schema = {
        SchemaType.PREDICATE: {},
        SchemaType.CATEGORY: {}
    }

    def __init__(self):
        pass

    @staticmethod
    def kgx_objects():
        return [os.path.join(*os.path.split(__file__)[:-1], 'data', file) for file in UtilMock.kgx_files]

    @staticmethod
    def merged_objects():
        return [os.path.join(*os.path.split(__file__)[:-1], 'data', file) for file in UtilMock.merged_files]

    @staticmethod
    def bulk_path(*args, **kwargs):
        return os.path.join(*os.path.split(__file__)[:-1], 'data', 'bulk')

    @staticmethod
    def is_up_to_date(*args, **kwargs):
        return False

    @staticmethod
    def schema_path(name, *args, **kwargs):
        return name

    @staticmethod
    def read_schema(schema_type: SchemaType, *args, **kwargs):
        return UtilMock.schema[schema_type]

    @staticmethod
    def read_object(path, *args, **kwargs):
        import json
        with open(path) as f:
            return json.load(f)

    @staticmethod
    def write_object(dictionary, file_name):
        print(dictionary, file_name)
        print(UtilMock.file_content_assertions)
        assert UtilMock.file_content_assertions[file_name] == dictionary