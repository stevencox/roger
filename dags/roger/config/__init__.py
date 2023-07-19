import json
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, List

import yaml
from dug.config import Config as DugConfig
from flatten_dict import flatten, unflatten

from ._base import DictLike
from .s3_config import S3Config

CONFIG_FILENAME = Path(__file__).parent.resolve() / "config.yaml"


@dataclass
class RedisConfig(DictLike):
    username: str = ""
    password: str = ""
    host: str = "redis"
    graph: str = "test"
    port: int = 6379

    def __post_init__(self):
        self.port = int(self.port)


@dataclass
class LoggingConfig(DictLike):
    level: str = "DEBUG"
    format: str = '[%(name)s][%(filename)s][%(lineno)d][%(funcName)20s] %(levelname)s: %(message)s'


@dataclass
class KgxConfig(DictLike):
    biolink_model_version: str = "1.5.0"
    dataset_version: str = "v1.0"
    merge_db_id: int = 1
    merge_db_temp_dir: str = "workspace"
    data_sets: List = field(default_factory=lambda: ['baseline-graph'])

    def __post_init__(self):
        # Convert strings to list. In cases where this is passed as env variable with a single value
        # cast it to a list. eg ROGER_KGX_DATA__SET="spark,baseline-data" could be converted to
        # config.kgx.data_set = ["spark", "baseline-data"]
        self.data_sets = [data_set.strip(" ") for data_set in self.data_sets.split(",")] \
            if isinstance(self.data_sets, str) else self.data_sets


@dataclass
class DugInputsConfig(DictLike):
    data_source: str = 'stars'
    data_sets: List = field(default_factory=lambda: ['topmed', 'bdc'])

    def __post_init__(self):
        # Convert strings to list. In cases where this is passed as env variable with a single value
        # cast it to a list. eg ROGER_KGX_DATA__SET="spark,baseline-data" could be converted to
        # config.kgx.data_set = ["spark", "baseline-data"]
        self.data_sets = [data_set.strip(" ") for data_set in self.data_sets.split(",")] \
            if isinstance(self.data_sets, str) else self.data_sets


@dataclass
class BulkLoaderConfig(DictLike):
    separator: str = "0x1E"
    enforce_schema: bool = False
    skip_invalid_nodes: bool = False
    skip_invalid_edges: bool = False
    quote: int = 0
    max_token_count: int = 1024
    max_buffer_size: int = 2048
    max_token_size: int = 500
    index: list = field(default_factory=list)
    full_text_index: list = field(default_factory=list)


@dataclass
class AnnotationConfig(DictLike):
    annotator: str = "https://api.monarchinitiative.org/api/nlp/annotate/entities?min_length=4&longest_only=false&include_abbreviation=false&include_acronym=false&include_numbers=false&content="
    normalizer: str = "https://nodenormalization-sri.renci.org/get_normalized_nodes?curie="
    synonym_service: str = "https://onto.renci.org/synonyms/"
    ontology_metadata: str = "https://api.monarchinitiative.org/api/bioentity/"
    clear_http_cache: bool = False
    preprocessor: dict = field(default_factory=lambda:
        {
            "debreviator": {
                "BMI": "body mass index"
            },
            "stopwords": "the",
        }
   )

    ontology_greenlist: List[str] = field(default_factory=lambda: [
        "PATO", "CHEBI", "MONDO", "UBERON", "HP", "MESH", "UMLS"
    ])



@dataclass
class IndexingConfig(DictLike):
    variables_index: str = "variables_index"
    concepts_index: str = "concepts_index"
    kg_index: str = "kg_index"
    tranql_min_score: float = 0.2
    excluded_identifiers: List[str] = field(default_factory=lambda: [
        "CHEBI:17336"
    ])

    queries: dict = field(default_factory=lambda: {
        "disease": ["disease", "phenotypic_feature"],
        "pheno": ["phenotypic_feature", "disease"],
        "anat": ["disease", "anatomical_entity"],
        "chem_to_disease": ["chemical_substance", "disease"],
        "phen_to_anat": ["phenotypic_feature", "anatomical_entity"],
        "anat_to_disease": ["anatomical_entity", "disease"],
        "anat_to_pheno": ["anatomical_entity", "phenotypic_feature"],
    })
    tranql_endpoint: str = "http://tranql:8081/tranql/query?dynamic_id_resolution=true&asynchronous=false"
    # by default skips node to element queries
    node_to_element_queries: dict = field(default_factory=lambda: {})

    def __post_init__(self):
        node_to_el_enabled = True if str(self.node_to_element_queries.get("enabled")).lower() == "true" else False
        final_node_to_element_queries = {}
        if node_to_el_enabled:
            for key in filter(lambda k: k != "enabled", self.node_to_element_queries.keys()):
                final_node_to_element_queries[key] = self.node_to_element_queries[key]
        self.node_to_element_queries = final_node_to_element_queries

@dataclass
class ElasticsearchConfig(DictLike):
    host: str = "elasticsearch"
    username: str = "elastic"
    password: str = ""
    nboost_host: str = ""



class RogerConfig(DictLike):

    OS_VAR_PREFIX = "ROGER_"

    def __init__(self, **kwargs):
        self.redisgraph = RedisConfig(**kwargs.pop('redisgraph', {}))
        self.logging = LoggingConfig(**kwargs.pop('logging', {}))
        self.kgx = KgxConfig(**kwargs.pop('kgx', {}))
        self.dug_inputs = DugInputsConfig(**kwargs.pop('dug_inputs', {}))
        self.bulk_loader = BulkLoaderConfig(**kwargs.pop('bulk_loader', {}))
        self.annotation = AnnotationConfig(**kwargs.pop('annotation', {}))
        self.indexing = IndexingConfig(**kwargs.pop('indexing', {}))
        self.elasticsearch = ElasticsearchConfig(**kwargs.pop('elasticsearch'))
        self.s3_config = S3Config(**kwargs.pop('s3', {}))

        self.data_root: str = kwargs.pop("data_root", "")
        self.dug_data_root: str = kwargs.pop("dug_data_root", "")
        self.kgx_base_data_uri: str = kwargs.pop("kgx_base_data_uri", "")
        self.annotation_base_data_uri: str = kwargs.pop("annotation_base_data_uri", "")
        self.validation = kwargs.pop("validation")
        self.dag_run = kwargs.pop('dag_run', None)

    def to_dug_conf(self) -> DugConfig:
        return DugConfig(
            elastic_host=self.elasticsearch.host,
            elastic_password=self.elasticsearch.password,
            elastic_username=self.elasticsearch.username,
            redis_host=self.redisgraph.host,
            redis_password=self.redisgraph.password,
            redis_port=self.redisgraph.port,
            nboost_host=self.elasticsearch.nboost_host,
            preprocessor=self.annotation.preprocessor,
            annotator={
                'url': self.annotation.annotator,
            },
            normalizer={
                'url': self.annotation.normalizer,
            },
            synonym_service={
                'url': self.annotation.synonym_service,
            },
            ontology_helper={
                'url': self.annotation.ontology_metadata,
            },
            tranql_exclude_identifiers=self.indexing.excluded_identifiers,
            tranql_queries=self.indexing.queries,
            concept_expander={
                'url': self.indexing.tranql_endpoint,
                'min_tranql_score': self.indexing.tranql_min_score,
            },
            ontology_greenlist=self.annotation.ontology_greenlist,
            node_to_element_queries=self.indexing.node_to_element_queries,
        )

    @property
    def dict(self):
        output = {}
        for key, value in self.__dict__.items():
            if hasattr(value, '__dict__'):
                output[key] = value.__dict__
            else:
                output[key] = value
        return output

    @classmethod
    def factory(cls, file_path: str):
        file_path = Path(file_path).resolve()
        with file_path.open() as config_file:
            file_data = yaml.load(config_file, Loader=yaml.FullLoader)

        override_data = cls.get_override_data(cls.OS_VAR_PREFIX)

        combined_data = cls.merge_dicts(file_data, override_data)

        return RogerConfig(**combined_data)

    @staticmethod
    def merge_dicts(dict_a, dict_b):
        flat_a = flatten(dict_a, reducer='dot')
        flat_b = flatten(dict_b, reducer='dot')
        flat_a.update(flat_b)
        return unflatten(flat_a, 'dot')

    @staticmethod
    def get_override_data(prefix):
        override_data = {}
        os_var_keys = os.environ.keys()
        keys_of_interest = filter(lambda x: x.startswith(prefix), os_var_keys)
        for key in keys_of_interest:
            value = os.environ.get(key)
            var_name = key.replace(prefix, "", 1)
            var_name = var_name.lstrip("_")
            var_name = var_name.replace("__", "~")
            var_name = var_name.replace("_", ".")
            var_name = var_name.replace("~", "_")
            var_name = var_name.lower()
            override_data[var_name] = value
        return unflatten(override_data, 'dot')


class Config:
    """
    Singleton config wrapper
    """
    __instance__: Optional[Dict] = None
    os_var_prefix = "ROGERENV_"

    def __init__(self, file_name: str):
        if not Config.__instance__:
            Config.__instance__ = Config.read_config_file(file_name=file_name)
            os_var_keys = os.environ.keys()
            keys_of_interest = [x for x in os_var_keys if x.startswith(Config.os_var_prefix)]
            for key in keys_of_interest:
                new_key = key.replace(Config.os_var_prefix, "")
                value = os.environ[key]
                new_dict = Config.os_var_to_dict(new_key, value)
                try:
                    Config.update(new_dict)
                except ValueError as e:
                    warnings.warn(f"{e} encountered trying to assign string from "
                                  f"OS variable `{key}` to a dictionary object."
                                  f"Please specify inner keys.")

    @staticmethod
    def os_var_to_dict(var_name, value):
        var_name = var_name.replace("__", "~")
        var_name = var_name.replace("_", ".")
        var_name = var_name.replace("~", "_")
        var_name = var_name.lower()
        m = {var_name: value}
        result = unflatten(m, "dot")
        return result

    @staticmethod
    def read_config_file(file_name: str):
        return yaml.load(open(file_name), Loader=yaml.FullLoader)

    def __getattr__(self, item):
        """
        Proxies calls to instance dict.
        Note: dict.update is overridden to do partial updates.
        Refer to Config.update method.
        :param item: method called
        :return: proxied method
        """
        if item == 'update':
            # overrides default dict update method
            return self.update
        return getattr(Config.__instance__, item)

    def __getitem__(self, item):
        """
        Makes config object subscriptable
        :param item: key to lookup
        :return: value stored in key
        """
        return self.__instance__.get(item)

    @staticmethod
    def update(new_value: Dict):
        """
        Updates dictionary partially.
        Given a config {'name': {'first': 'name', 'last': 'name'}}
        and a partial update {'name': {'first': 'new name'} }
        result would be {'name': {'first': 'new name', 'last': 'name'}}
        :param new_value: parts to update
        :return: updated dict
        """
        config_flat = flatten(Config.__instance__)
        new_value_flat = flatten(new_value)
        config_flat.update(new_value_flat)
        Config.__instance__ = unflatten(config_flat)
        return Config.__instance__

    def __str__(self):
        flat = flatten(Config.__instance__)
        for k in flat:
            if 'PASSWORD' in k or 'password' in k:
                flat[k] = '******'
        flat = unflatten(flat)
        result = json.dumps(flat)
        return f"""{result}"""


def get_default_config(file_name: str = CONFIG_FILENAME) -> RogerConfig:
    """
    Get config as a dictionary

    Parameters
    ----------
    file_name: str
        The filename with all the configuration

    Returns
    -------
    dict
        A dictionary containing all the entries from the config YAML

    """
    config_instance = RogerConfig.factory(file_name)
    return config_instance


config: RogerConfig = get_default_config()
