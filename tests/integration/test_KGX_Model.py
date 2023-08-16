import json
import pytest
from unittest.mock import patch

from roger.models.kgx import KGXModel
from . import conftest


@pytest.fixture
def kgx_model():
    biolink = conftest.BiolinkMock()
    kgx_model = KGXModel(biolink=biolink, config={})
    return kgx_model

def setup_mock_and_run_create_schema(test_files_dir, kgx_model: KGXModel):

    with patch('roger.models.kgx.storage', conftest):
        conftest.merge_file_test_dir = test_files_dir
        with open(conftest.merge_path("expected.json")) as f:
            expected = json.load(f)
            conftest.file_content_assertions = expected
        kgx_model.create_schema()

def test_create_schema_plain(kgx_model: KGXModel):
    file_name = 'non_conflicting_prop_types__schema__kgx'
    setup_mock_and_run_create_schema(file_name, kgx_model=kgx_model)

def test_create_schema_conflicting_nodes(kgx_model: KGXModel):
    file_name = 'conflicting_prop_types__nodes__schema__kgx'
    setup_mock_and_run_create_schema(file_name, kgx_model=kgx_model)

def test_create_schema_conflicting_edges(kgx_model: KGXModel):
    file_name = 'conflicting_prop_types__edges__schema__kgx'
    setup_mock_and_run_create_schema(file_name, kgx_model=kgx_model)

def test_merge(kgx_model: KGXModel):
    with patch('roger.models.kgx.storage', conftest):
        conftest.kgx_files = [
            'data_1.merge.kgx.json',
            'data_2.merge.kgx.json'
        ]
    #TODO add tests for merge nodes
