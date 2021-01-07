import pytest
import json
from unittest.mock import patch
from roger.core import KGXModel
from roger.test.mocks import BiolinkMock, UtilMock


@pytest.fixture
def kgx_model():
    biolink = BiolinkMock()
    kgx_model = KGXModel(biolink=biolink, config={})
    return kgx_model


def setup_mock_and_run_create_schema(test_file_name, kgx_model: KGXModel):
    with patch('roger.core.Util', UtilMock):
        UtilMock.kgx_files = [test_file_name]
        with open(UtilMock.kgx_objects()[0]) as f:

            expected = json.load(f)['expected_schema']
        UtilMock.file_content_assertions = expected
        kgx_model.create_schema()



def test_create_schema_plain(kgx_model: KGXModel):
    file_name = 'non_conflicting_prop_types.schema.kgx.json'
    setup_mock_and_run_create_schema(file_name, kgx_model=kgx_model)


def test_create_schema_conflicting_nodes(kgx_model: KGXModel):
    file_name = 'conflicting_prop_types.schema.nodes.kgx.json'
    setup_mock_and_run_create_schema(file_name, kgx_model=kgx_model)


def test_create_schema_conflicting_edges(kgx_model: KGXModel):
    file_name = 'conflicting_prop_types.schema.edges.kgx.json'
    setup_mock_and_run_create_schema(file_name, kgx_model=kgx_model)


def test_merge(kgx_model: KGXModel):
    with patch('roger.core.Util', UtilMock):
        UtilMock.kgx_files = [
            'data_1.merge.kgx.json',
            'data_2.merge.kgx.json'
        ]
    #@TODO add tests for merge nodes