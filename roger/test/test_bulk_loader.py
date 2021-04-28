import pytest, os
from roger.core import BulkLoad
from roger.test.mocks import BiolinkMock, UtilMock
from unittest.mock import patch


@pytest.fixture
def bulk_loader():
    biolink = BiolinkMock()
    return BulkLoad(biolink=biolink, config={'separator': 30})


def test_create_redis_schema():
    test_schema = {
        'concept': {
            'attribute0': 'list',
            'attribute1': 'str',
            'attribute2': 'int',
            'attribute3': 'bool'
        }
    }
    redis_schema = BulkLoad.create_redis_schema_header(test_schema['concept'], is_relation=False)
    assert 'attribute0:ARRAY' in redis_schema
    assert 'attribute1:STRING' in redis_schema
    assert 'attribute2:INT' in redis_schema
    assert 'attribute3:BOOL' in redis_schema

    redis_schema = BulkLoad.create_redis_schema_header(test_schema['concept'], is_relation=True)
    assert 'attribute0:ARRAY' in redis_schema
    assert 'attribute1:STRING' in redis_schema
    assert 'attribute2:INT' in redis_schema
    assert 'attribute3:BOOL' in redis_schema

    # should add these columns to relationships
    assert 'internal_start_id:START_ID' in redis_schema
    assert 'internal_end_id:END_ID' in redis_schema


def test_group_by_set_attr():
    items = [
        {   # we need to make sure that empty values are the only ones ignored
            # not values that evaluate to false.
            'id': 0,
            'attr_1': '',
            'attr_2': 2,
            'attr_3': [],
            'attr_4': False,
            'attr_5': None
        },
        {
            'id': 1,
            'attr_1': 'a',
            'attr_2': 'b',
            'attr_3': 'c',
            'attr_4': ''
        }
    ]
    # first group is attr_2, attr_4, 'id'
    group_1 = frozenset(['attr_2', 'attr_4', 'id'])
    # second group is attr_1, attr_2, attr_3 , 'id'
    group_2 = frozenset(['attr_1', 'attr_2', 'attr_3', 'id'])
    grouping, invalid_keys = BulkLoad.group_items_by_attributes_set(objects=items,
                                                                    processed_object_ids=set())
    assert group_1 in grouping
    assert group_2 in grouping

    assert items[0] in grouping[group_1]
    assert items[1] in grouping[group_2]


def test_write_bulk_nodes(bulk_loader: BulkLoad):
    nodes_schema = {
        "named_thing": {
            "id": "str",
            "str": "str",
            "list_attr": "list",
            "bool_attr": "bool",
            "float_attr": "float",
            "int_attr": "int"
        }
    }
    node_objects = {
        "named_thing": [
            {
                "id": "ID:1",
                "str": "name",
                "list_attr": ["x"],
                "bool_attr": False,
                "float_attr": 0.1,
                "int_attr": 0
            }
        ]
    }
    with patch('roger.core.Util', UtilMock):
        bulk_path = UtilMock.bulk_path()
        state = {}
        bulk_loader.write_bulk(bulk_path=bulk_path,
                               obj_map=node_objects,
                               schema=nodes_schema,
                               state=state,
                               is_relation=False)
        assert len(state['file_paths']) > 0
        # @TODO add assertions.
        # with open(os.path.join(bulk_path,'named_thing_csv-0-1'))






