import json
from dug.annotate import TOPMedStudyAnnotator
from dug.core import Search
from dug_helpers.dug_logger import get_logger
from roger.Config import get_default_config as get_config
import os
from pathlib import Path
from roger.core import Util
from io import StringIO
import hashlib
import logging
import dug.tranql as tql

log = get_logger()


class Dug:
    annotator = None
    search_obj = None
    config = None

    def __init__(self, config=None, to_string=True):
        if not config:
            Dug.config = get_config()
        if to_string:
            self.log_stream = StringIO()
            self.string_handler = logging.StreamHandler (self.log_stream)
            log.addHandler(self.string_handler)
        Dug.config = config
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
        if not Dug.search_obj:
            # Dug search expects these to be set as os envrion
            # Elastic config
            elastic_conf = config.get("elastic_search")
            os.environ['ELASTIC_API_HOST']  =  elastic_conf.get("host")
            os.environ['ELASTIC_USERNAME'] =  elastic_conf.get("username")
            os.environ['ELASTIC_PASSWORD'] = elastic_conf.get("password")
            os.environ['NBOOST_API_HOST'] = elastic_conf.get("nboost_host")
            Dug.search_obj = Search(os.environ['ELASTIC_API_HOST'])

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
    def load_dd_xml(file):
        log.info(f"Loading DD xml file --> {file}")
        return Dug.annotator.load_data_dictionary(file)

    @staticmethod
    def annotate(tags):
        log.info(f"Annotating")
        return Dug.annotator.annotate(tags)

    @staticmethod
    def make_edge (subj,
                   obj,
                   predicate = 'biolink:association',
                   predicate_label= 'association',
                   relation = 'biolink:association',
                   relation_label = 'association'
    ):
        """
        Create an edge between two nodes.

        :param subj: The identifier of the subject.
        :param pred: The predicate linking the subject and object.
        :param obj: The object of the relation.
        :param predicate: Biolink compatible edge type.
        :param predicate_label: Edge label.
        :param relation: Ontological edge type.
        :param relation_label: Ontological edge type label.
        :returns: Returns and edge.
        """
        edge_id = hashlib.md5(f'{subj}{predicate}{obj}'.encode('utf-8')).hexdigest()
        return {
            "subject"     : subj,
            "predicate"   : predicate,
            "predicate_label": predicate_label,
            "id": edge_id,
            "relation"  :  relation,
            "relation_label": relation_label,
            "object"      : obj,
            "provided_by" : "renci.bdc.semanticsearch.annotator"
        }

    @staticmethod
    def convert_to_kgx_json(annotations):
        """
        Given an annotated and normalized set of study variables,
        generate a KGX compliant graph given the normalized annotations.
        Write that grpah to a graph database.
        See BioLink Model for category descriptions. https://biolink.github.io/biolink-model/notes.html
        """
        graph = {
            "nodes": [],
            "edges": []
        }
        edges = graph['edges']
        nodes = graph['nodes']

        for index, variable in enumerate(annotations):
            study_id = variable['collection_id']
            if index == 0:
                """ assumes one study in this set. """
                nodes.append({
                    "id": study_id,
                    "category": ["biolink:ClinicalTrial"]
                })

            """ connect the study and the variable. """
            edges.append(Dug.make_edge(
                subj=variable['element_id'],
                relation_label='part of',
                relation='BFO:0000050',
                obj=study_id,
                predicate='biolink:part_of',
                predicate_label='part of'))
            edges.append(Dug.make_edge(
                subj=study_id,
                relation_label='has part',
                relation="BFO:0000051",
                obj=variable['element_id'],
                predicate='biolink:has_part',
                predicate_label='has part'))

            """ a node for the variable. """
            nodes.append({
                "id": variable['element_id'],
                "name": variable['element_name'],
                "description": variable['element_desc'],
                "category": ["biolink:ClinicalModifier"]
            })
            for identifier, metadata in variable['identifiers'].items():
                edges.append(Dug.make_edge(
                    subj=variable['element_id'],
                    relation='OBAN:association',
                    obj=identifier,
                    relation_label='association',
                    predicate='biolink:Association',
                    predicate_label='association'))
                edges.append(Dug.make_edge(
                    subj=identifier,
                    relation='OBAN:association',
                    obj=variable['element_id'],
                    relation_label='association',
                    predicate='biolink:Association',
                    predicate_label='association'))
                nodes.append({
                    "id": identifier,
                    "name": metadata['label'],
                    "category": metadata['type']
                })
        return graph

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
                node_types = list(metadata['type']) if isinstance(metadata['type'], str) else metadata['type']
                nodes.append({
                    "id": identifier,
                    "name": metadata['label'],
                    "category": node_types
                })
                edges.append(Dug.make_edge(
                    subj=tag_id,
                    obj=identifier))
                edges.append(Dug.make_edge(
                    subj=identifier,
                    obj=tag_id))

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
            edges.append(Dug.make_edge(
                subj=variable_id,
                predicate='biolink:part_of',
                predicate_label='part of',
                relation='BFO:0000050',
                relation_label='part of',
                obj=study_id))
            edges.append(Dug.make_edge(
                subj=study_id,
                predicate='biolink:has_part',
                predicate_label='has part',
                relation='BFO:0000051',
                relation_label='part of',
                obj=variable_id))

            """ Link to its tag. """
            edges.append(Dug.make_edge(
                subj=variable_id,
                predicate='biolink:part_of',
                predicate_label='part of',
                relation='BFO:0000050',
                relation_label='part of',
                obj=tag_id))
            edges.append(Dug.make_edge(
                subj=tag_id,
                predicate='biolink:has_part',
                predicate_label='has part',
                relation='BFO:0000051',
                relation_label='has part',
                obj=variable_id))
        return graph

    @staticmethod
    def index_variables(variables):
        Dug.search_obj.index_variables(variables, "variables_index")

    @staticmethod
    def crawl_concepts(concepts, crawl_dir):
        # This needs to be redisgraph.graphName.
        index_config = Dug.config.get("indexing")
        tranql_url = index_config["tranql_endpoint"]
        graph_name = Dug.config["redisgraph"]["graph"]
        source = f"redis:{graph_name}"
        queries_config = index_config["queries"]
        tranql_queries = {
            key: tql.QueryFactory(queries_config[key], source)
            for key in queries_config
        }

        Dug.search_obj.crawlspace = crawl_dir
        Dug.search_obj.crawl(
            concepts=concepts,
            concept_index=index_config["concepts_index"],
            kg_index=index_config["kg_index"],
            queries=tranql_queries,
            min_score=index_config["tranql_min_score"],
            include_node_keys=["id", "name", "synonyms"],
            include_edge_keys=[],
            query_exclude_identifiers=index_config["excluded_identifiers"],
            tranql_endpoint=tranql_url
        )


class DugUtil():

    @staticmethod
    def make_output_file_path(base, file):
        return os.path.join(base, '.'.join(os.path.basename(file).split('.')[:-1]) + '_annotated.json')

    @staticmethod
    def load_and_annotate(config=None, to_string=False):
        with Dug(config) as dug:
            topmed_files = Util.dug_topmed_objects()
            dd_xml_files = Util.dug_dd_xml_objects()
            output_base_path = Util.dug_annotation_path('')
            for file in topmed_files:
                """Loading step"""
                variables, tags = dug.load_tagged(file)
                """Annotating step"""
                # dug.annotate modifies the tags in place. It adds
                # a new attribute `identifiers` on each tag.
                # That is used in make kg downstream to build associciations
                # between Variable Tags and other Concepts.

                annotated_tags = dug.annotate(tags)

                # annotated_tags is an expanded format of the tags. Basically
                # all the Nodes we have. This expansion makes it difficult to
                # preserve the `edges` / `links` between the Tags and the concepts
                # derived from their descriptions.
                # Using the inplace modified `tags` makes sense for make_tagged_kg. since concepts are
                # binned within each tag.
                output_file_path = DugUtil.make_output_file_path(output_base_path, file)
                Util.write_object({
                    "variables": variables,
                    "original_tags": tags,
                    "concepts": annotated_tags
                }, output_file_path)

            for file in dd_xml_files:
                """Loading XML step"""
                variables = dug.load_dd_xml(file)
                """Annotating XML step"""
                annotated_tags = dug.annotate(variables)
                # The annotated tags are not needed.
                output_file_path = DugUtil.make_output_file_path(output_base_path, file)
                Util.write_object({
                    "variables": variables,
                    "concepts": annotated_tags
                }, output_file_path)
            log.info(f"Load and Annotate complete")
            output_log = dug.log_stream.getvalue()
        return output_log

    @staticmethod
    def make_kg_tagged(config=None, to_string=False):
        with Dug(config) as dug:
            output_base_path = Util.dug_kgx_path("")
            log.info("Starting building KGX files")
            annotated_file_names = Util.dug_annotation_objects()
            for annotated_file in annotated_file_names:
                if "topmed" in annotated_file:
                    log.info(f"Processing {annotated_file}")
                    with open(annotated_file) as f:
                        data_set = json.load(f)
                        graph = dug.make_tagged_kg(data_set['variables'], data_set['original_tags'])
                    output_file_path = os.path.join(output_base_path,
                                                '.'.join(os.path.basename(annotated_file).split('.')[:-1]) + '_kgx.json')
                    Util.write_object(graph, output_file_path)
                    log.info(f"Wrote {len(graph['nodes'])} nodes and {len(graph['edges'])} edges, to {output_file_path}.")
                else:
                    log.info(f"Processing {annotated_file}")
                    with open(annotated_file) as f:
                        data_set = json.load(f)
                        graph = dug.convert_to_kgx_json(data_set['variables'])
                    output_file_path = os.path.join(output_base_path,
                                                '.'.join(os.path.basename(annotated_file).split('.')[:-1]) + '_kgx.json')
                    Util.write_object(graph, output_file_path)
                    log.info(f"Wrote {len(graph['nodes'])} nodes and {len(graph['edges'])} edges, to {output_file_path}.")
            log.info("Building the graph complete")
            output_log = dug.log_stream.getvalue()
        return output_log

    @staticmethod
    def index_variables(config=None, to_string=False):
        with Dug(config) as dug:
            annotated_file_names = Util.dug_annotation_objects()
            log.info(f'Indexing Dug variables, found {len(annotated_file_names)} file(s).' )
            for file in annotated_file_names:
                with open(file) as f:
                    data_set = json.load(f)
                    variables = data_set['variables']
                    annotated_tags = data_set['concepts']
                    log.info(f'Indexing {f}... found {len(variables)}')
                    ## This has to do with
                    # https://github.com/helxplatform/dug/blob/75eb62584f75eb9d6e66ce82ab54077a5d35c45e/dug/core.py#L550
                    # @TODO maybe annotate should do such normalization from dict to list in variable identifiers.
                    for variable in variables:
                        for identifier in variable['identifiers']:
                            if identifier.startswith("TOPMED:"):  # expand
                                new_vars = list(annotated_tags[identifier]['identifiers'].keys())
                                variable['identifiers'].extend(new_vars)
                        variable["identifiers"] = list(set(list(variable["identifiers"])))
                    dug.index_variables(variables)
            output_log = dug.log_stream.getvalue()
            log.info('Done.')
            return output_log

    @staticmethod
    def crawl_tranql(config=None, to_string=False):
        with Dug(config) as dug:
            annotated_file_names = Util.dug_annotation_objects()
            log.info(f'Crawling Dug Concepts, found {len(annotated_file_names)} file(s).')
            for file in annotated_file_names:
                with open(file) as f:
                    data_set = json.load(f)
                    crawl_dir = Util.dug_crawl_path('')
                    dug.crawl_concepts(concepts=data_set["concepts"],crawl_dir=crawl_dir)

    @staticmethod
    def is_topmed_data_available(config=None, to_string=False):
        if not config:
            config = get_config()
        home = os.path.join(os.path.dirname(os.path.join(os.path.abspath(__file__))), '..')
        file_path = os.path.join(home, get_config()['dug_data_root'])
        data_path = Path(file_path)
        data_files = data_path.glob('topmed_*.csv')
        files = [str(file) for file in data_files]
        if not files:
            log.error("No topmed files were found.")
            raise FileNotFoundError("Error could not find topmed files")
        return len(files)
