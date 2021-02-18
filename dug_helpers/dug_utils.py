import json
from dug.annotate import TOPMedStudyAnnotator
from redis import StrictRedis
from dug_helpers.dug_logger import get_logger
from roger.Config import get_default_config as get_config
import os
from pathlib import Path
from roger.core import Util

log = get_logger()


class Dug:
    annotator = None

    def __init__(self, config=None):
        if not config:
            self.config = get_config()
        self.config = config
        if not Dug.annotator:
            annotation_config = self.config.get('annotation')
            annotation_config.update({
                'redis_host': self.config.get('redisgraph', {}).get('host'),
                'redis_port': self.config.get('redisgraph', {}).get('port'),
                'redis_password': self.config.get('redisgraph', {}).get('password')
            })
            Dug.annotator = TOPMedStudyAnnotator(
                config=annotation_config
            )
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

    def create_redis(self):
        redis_params = self.config.get('redisgraph', {})
        redis_conn = StrictRedis(
            host=redis_params['host'],
            password=redis_params['password'],
            port=redis_params['port']
        )
        return redis_conn

    @staticmethod
    def make_tagged_kg(variables, tags):
        """ Make a Translator standard knowledge graph representing
        tagged study variables.
        :param variables: The variables to model.
        :param tags: The tags characterizing the variables.
        :returns: Returns dictionary with nodes and edges modeling a Translator/Biolink KG.
        """
        graph = {
            "nodes": [],
            "edges": []
        }
        edges = graph['edges']
        nodes = graph['nodes']
        studies = {}

        """ Create graph elements to model tags and their
        links to identifiers gathered by semantic tagging. """
        tag_map = {}
        for tag in tags:
            tag_pk = tag['pk']
            tag_id = tag['id']
            tag_map[tag_pk] = tag
            nodes.append({
                "id": tag_id,
                "pk": tag_pk,
                "name": tag['title'],
                "description": tag['description'],
                "instructions": tag['instructions'],
                "category": ["biolink:InformationContentEntity"]
            })
            """ Link ontology identifiers we've found for this tag via nlp. """
            for identifier, metadata in tag['identifiers'].items():
                nodes.append({
                    "id": identifier,
                    "name": metadata['label'],
                    "category": metadata['type']
                })
                edges.append(Dug.annotator.make_edge(
                    subj=tag_id,
                    pred="OBAN:association",
                    obj=identifier,
                    edge_label='biolink:association',
                    category=["biolink:association"]))
                edges.append(Dug.annotator.make_edge(
                    subj=identifier,
                    pred="OBAN:association",
                    obj=tag_id,
                    edge_label='biolink:association',
                    category=["biolink:association"]))

        """ Create nodes and edges to model variables, studies, and their
        relationships to tags. """
        for variable in variables:
            variable_id = variable['element_id']
            variable_name = variable['element_name']

            # Eg. variable['identifiers'] = ['TOPMED.TAG:51']
            variable_tag_pk = variable['identifiers'][0].split(':')[-1]

            study_id = variable['collection_id']
            study_name = variable['collection_name']
            tag_id = tag_map[int(variable_tag_pk)]['id']
            if not study_id in studies:
                nodes.append({
                    "id": study_id,
                    "name": study_name,
                    "category": ["biolink:ClinicalTrial"]
                })
                studies[study_id] = study_id
            nodes.append({
                "id": variable_id,
                "name": variable_name,
                "category": ["biolink:ClinicalModifier"]
            })
            """ Link to its study.  """
            edges.append(Dug.annotator.make_edge(
                subj=variable_id,
                edge_label='biolink:part_of',
                pred="BFO:0000050",
                obj=study_id,
                category=['biolink:part_of']))
            edges.append(Dug.annotator.make_edge(
                subj=study_id,
                edge_label='biolink:has_part',
                pred="BFO:0000051",
                obj=variable_id,
                category=['biolink:has_part']))

            """ Link to its tag. """
            edges.append(Dug.annotator.make_edge(
                subj=variable_id,
                edge_label='biolink:part_of',
                pred="BFO:0000050",
                obj=tag_id,
                category=['biolink:part_of']))
            edges.append(Dug.annotator.make_edge(
                subj=tag_id,
                edge_label='biolink:has_part',
                pred="BFO:0000051",
                obj=variable_id,
                category=['biolink:has_part']))
        return graph


class DugUtil:

    @staticmethod
    def get_multiple_file_path(relative_path, pattern):
        home = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(home, '..', relative_path)
        data_path = Path(file_path)
        data_files = data_path.glob(pattern)
        files = [str(file) for file in data_files]
        return files

    @staticmethod
    def get_annotation_output_path(config):
        output_base_path = os.path.join(config.get('dug_data_root'), 'output', 'annotations')
        return output_base_path

    @staticmethod
    def get_kgx_output_path(config):
        output_base_path = os.path.join(config.get('dug_data_root'), 'output', 'kgx')
        return output_base_path

    @staticmethod
    def load_and_annotate(config=None):
        with Dug(config) as dug:
            topmed_files = DugUtil.get_multiple_file_path(config.get('dug_data_root'), 'topmed_*.csv')
            output_base_path = DugUtil.get_annotation_output_path(config)
            for file in topmed_files:
                """Loading step"""
                variables, tags = dug.load_tagged(file)
                """Annotating step"""
                annotated_tags = dug.annotate(tags)
                output_file_path = os.path.join(output_base_path,
                                                '.'.join(os.path.basename(file).split('.')[:-1]) + '_annotated.json')
                Util.write_object({
                    "variables": variables,
                    "original_tags": tags,
                    "annotated_tags": annotated_tags
                }, output_file_path)
        log.info(f"Load and Annotate complete")

    @staticmethod
    def make_kg_tagged(config=None):
        with Dug(config) as dug:
            output_base_path = DugUtil.get_kgx_output_path(config)
            log.info("Starting building KGX files")
            annotations_output_path = DugUtil.get_annotation_output_path(config)
            annotated_file_names = DugUtil.get_multiple_file_path(annotations_output_path, 'topmed_*.json')
            for annotated_file in annotated_file_names:
                log.info(f"Processing {annotated_file}")
                with open(annotated_file) as f:
                    data_set = json.load(f)
                    graph = dug.make_tagged_kg(data_set['variables'], data_set['original_tags'])
                output_file_path = os.path.join(output_base_path,
                                                '.'.join(os.path.basename(annotated_file).split('.')[:-1]) + '_kgx.json')
                Util.write_object(graph, output_file_path)
                log.info(f"Wrote {len(graph['nodes'])} nodes and {len(graph['edges'])} edges, to {output_file_path}.")

        log.info("Building the graph complete")
        return {"config": {"knowledge_graph": graph}}




