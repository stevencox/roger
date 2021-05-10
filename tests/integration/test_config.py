import os

import yaml

from roger.Config import RogerConfig
from tests.integration import TEST_DATA_DIR


def test_config_factory():
    conf_file = TEST_DATA_DIR / 'sample_config.yaml'
    with conf_file.open() as opened_file:
        expected = yaml.load(opened_file)

    conf = RogerConfig.factory(str(conf_file))
    actual = conf.dict
    assert actual == expected


def test_elasticsearch_overrides():
    conf_file = TEST_DATA_DIR / 'sample_config.yaml'
    os.environ["ROGER_ELASTICSEARCH_PASSWORD"] = "new-password"

    conf = RogerConfig.factory(str(conf_file))
    assert conf.elasticsearch.password == "new-password"
