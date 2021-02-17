import os
import json
from dug.annotate import TOPMedStudyAnnotator
from redis import StrictRedis
from dug_helpers.dug_logger import get_logger
from roger.Config import get_default_config as get_config

log = get_logger()

def get_annotator_cofig():
    db_url_default = "http://" + os.environ.get('NEO4J_HOST', 'localhost') + ":" + os.environ.get('NEO4J_PORT',
                                                                                                  '7474') + "/db/data"
    config = {
        'annotator': "https://api.monarchinitiative.org/api/nlp/annotate/entities?min_length=4&longest_only=false&include_abbreviation=false&include_acronym=false&include_numbers=false&content=",
        'normalizer': "https://nodenormalization-sri.renci.org/get_normalized_nodes?curie=",
        'synonym_service': "https://onto.renci.org/synonyms/",
        'ontology_metadata': "https://api.monarchinitiative.org/api/ontology/term/",
        'password': os.environ.get('NEO4J_PASSWORD', 'neo4j'),
        'username': 'neo4j',
        'db_url': db_url_default,
        'redis_host': os.environ.get('REDIS_HOST', 'redis-master'),
        'redis_port': os.environ.get('REDIS_PORT', 6379),
        'redis_password': os.environ.get('REDIS_PASSWORD', 'redis'),
    }

    return config


class Dug:
    annotator = TOPMedStudyAnnotator(config=get_annotator_cofig())

    def __init__(self, config=None):
        if not config:
            self.config = get_config()
        self.config = config
        self.conn = self.create_redis()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type or exc_val or exc_tb:
            log.error(f"{exc_val} {exc_val} {exc_tb}")

    @staticmethod
    def load_tagged(file):
        log.info(f"Loading file --> {file}")
        return Dug.annotator.load_tagged_variables(file)

    @staticmethod
    def annotate(tags):
        log.info(f"Annotating")
        return Dug.annotator.annotate(tags)

    @staticmethod
    def make_kg(variables, tags):
        log.info(f"Making Knowledge Graph")
        return Dug.annotator.make_tagged_kg(variables, tags)

    def create_redis(self):
        redis_conn = StrictRedis(
            host="redis-master",
            port=6379,
            password="redis"
        )
        return redis_conn


class DugUtil:

    @staticmethod
    def load_and_annotate(config=None):
        with Dug(config) as dug:
            topmed_files = config.get("topmed_files")
            for file in topmed_files:
                """Loading step"""
                variables, tags = dug.load_tagged(file)
                dug.conn.set("variable", json.dumps(variables))
                """Annotating step"""
                tags = dug.annotate(tags)
                dug.conn.set("tags", json.dumps(tags))
        log.info(f"Load and Annotate complete")


    @staticmethod
    def make_kg_tagged(config=None):
        with Dug(config) as dug:
            graph = dug.make_kg(dug.conn.get("variables"), json.loads(dug.conn.get("tags")))
        log.info("Building the graph complete")
        return {"config": {"knowledge_graph": graph}}


