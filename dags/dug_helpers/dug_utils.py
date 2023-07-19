import asyncio
import hashlib
import logging
import os
import re
import tarfile
import traceback
from functools import reduce
from io import StringIO
from pathlib import Path
from typing import Union, List

import requests
from dug.core import get_parser, get_plugin_manager, DugConcept
from dug.core.annotate import DugAnnotator, ConceptExpander
from dug.core.crawler import Crawler
from dug.core.factory import DugFactory
from dug.core.parsers import Parser, DugElement
from dug.core.async_search import Search
from dug.core.index import Index

from roger.config import RogerConfig
from roger.core import Util
from roger.roger_util import get_logger
from utils.s3_utils import S3Utils

log = get_logger()



class Dug:

    def __init__(self, config: RogerConfig, to_string=True):
        self.config = config
        dug_conf = config.to_dug_conf()
        self.factory = DugFactory(dug_conf)
        self.cached_session = self.factory.build_http_session()
        self.event_loop = asyncio.new_event_loop()
        if to_string:
            self.log_stream = StringIO()
            self.string_handler = logging.StreamHandler(self.log_stream)
            log.addHandler(self.string_handler)

        self.annotator: DugAnnotator = self.factory.build_annotator()

        self.tranqlizer: ConceptExpander = self.factory.build_tranqlizer()

        graph_name = self.config["redisgraph"]["graph"]
        source = f"redis:{graph_name}"
        self.tranql_queries: dict = self.factory.build_tranql_queries(source)
        self.node_to_element_queries: list = self.factory.build_element_extraction_parameters(source)

        indexing_config = config.indexing
        self.variables_index = indexing_config.get('variables_index')
        self.concepts_index = indexing_config.get('concepts_index')
        self.kg_index = indexing_config.get('kg_index')

        self.search_obj: Search = self.factory.build_search_obj([
            self.variables_index,
            self.concepts_index,
            self.kg_index,
        ])
        self.index_obj: Index = self.factory.build_indexer_obj([
                self.variables_index,
                self.concepts_index,
                self.kg_index,

        ])

    def __enter__(self):
        self.event_loop = asyncio.new_event_loop()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # close elastic search connection
        self.event_loop.run_until_complete(self.search_obj.es.close())
        # close async loop
        if self.event_loop.is_running() and not self.event_loop.is_closed():
            self.event_loop.close()
        if exc_type or exc_val or exc_tb:
            traceback.print_exc()
            log.error(f"{exc_val} {exc_val} {exc_tb}")
            log.exception("Got an exception")

    def annotate_files(self, parser_name, parsable_files):
        """
        Annotates a Data element file using a Dug parser.
        :param parser_name: Name of Dug parser to use.
        :param parsable_files: Files to parse.
        :return: None.
        """
        dug_plugin_manager = get_plugin_manager()
        parser: Parser = get_parser(dug_plugin_manager.hook, parser_name)
        output_base_path = Util.dug_annotation_path('')
        log.info("Parsing files")
        for parse_file in parsable_files:
            log.debug("Creating Dug Crawler object")
            crawler = Crawler(
                crawl_file=parse_file,
                parser=parser,
                annotator=self.annotator,
                tranqlizer='',
                tranql_queries=[],
                http_session=self.cached_session
            )

            # configure output space.
            current_file_name = '.'.join(os.path.basename(parse_file).split('.')[:-1])
            elements_file_path = os.path.join(output_base_path, current_file_name)
            elements_file_name = 'elements.pickle'
            concepts_file_name = 'concepts.pickle'

            # create an empty elements file. This also creates output dir if it doesn't exist.
            log.debug(f"Creating empty file:  {elements_file_path}/element_file.json")
            Util.write_object({}, os.path.join(elements_file_path, 'element_file.json'))
            log.debug(parse_file)
            log.debug(parser)
            elements = parser(parse_file)
            log.debug(elements)
            crawler.elements = elements

            # @TODO propose for Dug to make this a crawler class init parameter(??)
            crawler.crawlspace = elements_file_path
            log.debug(f"Crawler annotator: {crawler.annotator}")
            crawler.annotate_elements()

            # Extract out the concepts gotten out of annotation
            # Extract out the elements
            non_expanded_concepts = crawler.concepts
            elements = crawler.elements

            # Write pickles of objects to file
            log.info(f"Parsed and annotated: {parse_file}")
            elements_out_file = os.path.join(elements_file_path, elements_file_name)
            Util.write_object(elements, elements_out_file)
            log.info(f"Pickled annotated elements to : {elements_file_path}/{elements_file_name}")
            concepts_out_file = os.path.join(elements_file_path, concepts_file_name)
            Util.write_object(non_expanded_concepts, concepts_out_file)
            log.info(f"Pickled annotated concepts to : {elements_file_path}/{concepts_file_name}")

    def make_edge(self,
                  subj,
                  obj,
                  predicate='biolink:related_to',
                  predicate_label='related to',
                  relation='biolink:related_to',
                  relation_label='related to'
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
            "subject": subj,
            "predicate": predicate,
            "predicate_label": predicate_label,
            "id": edge_id,
            "relation": relation,
            "relation_label": relation_label,
            "object": obj,
            "provided_by": "renci.bdc.semanticsearch.annotator"
        }

    def convert_to_kgx_json(self, elements, written_nodes=set()):
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

        for index, element in enumerate(elements):
            # DugElement means a variable (Study variable...)
            if not isinstance(element, DugElement):
                continue
            study_id = element.collection_id
            if study_id not in written_nodes:
                nodes.append({
                    "id": study_id,
                    "category": ["biolink:Study"],
                    "name": study_id
                })
                written_nodes.add(study_id)
            """ connect the study and the variable. """
            edges.append(self.make_edge(
                subj=element.id,
                relation_label='part of',
                relation='BFO:0000050',
                obj=study_id,
                predicate='biolink:part_of',
                predicate_label='part of'))
            edges.append(self.make_edge(
                subj=study_id,
                relation_label='has part',
                relation="BFO:0000051",
                obj=element.id,
                predicate='biolink:has_part',
                predicate_label='has part'))

            """ a node for the variable. Should be BL compatible """
            variable_node = {
                "id": element.id,
                "name": element.name,
                "category": ["biolink:StudyVariable"],
                "description": element.description.replace("'", '`') # bulk loader parsing issue
            }
            if element.id not in written_nodes:
                nodes.append(variable_node)
                written_nodes.add(element.id)

            for identifier, metadata in element.concepts.items():
                identifier_object = metadata.identifiers.get(identifier)
                # This logic is treating DBGap files.
                # First item in current DBGap xml files is a topmed tag,
                # This is treated as a DugConcept Object. But since its not
                # a concept we get from annotation (?) its never added to
                # variable.concepts.items  (Where variable is a DugElement object)
                # The following logic is trying to extract types, and for the
                # aformentioned topmed tag it adds `biolink:InfomrmationContentEntity`
                # Maybe a better solution could be adding types on DugConcept objects
                # More specifically Biolink compatible types (?)
                #
                if identifier_object:
                    category = identifier_object.types
                elif identifier.startswith("TOPMED.TAG:"):
                    category = ["biolink:InformationContentEntity"]
                else:
                    continue
                if identifier not in written_nodes:
                    nodes.append({
                        "id": identifier,
                        "category": category,
                        "name": metadata.name
                    })
                    written_nodes.add(identifier)
                # related to edge
                edges.append(self.make_edge(
                    subj=element.id,
                    obj=identifier
                    ))
                # related to edge
                edges.append(self.make_edge(
                    subj=identifier,
                    obj=element.id))
        return graph

    def make_tagged_kg(self, elements):
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
        # @TODO extract this into config or maybe dug ??
        topmed_tag_concept_type = "TOPMed Phenotype Concept"
        nodes_written = set()
        for tag in elements:
            if not (isinstance(tag, DugConcept) and tag.type == topmed_tag_concept_type):
                continue
            tag_id = tag.id
            tag_map[tag_id] = tag
            nodes.append({
                "id": tag_id,
                "name": tag.name,
                "description": tag.description.replace("'", "`"),
                "category": ["biolink:InformationContentEntity"]
            })
            """ Link ontology identifiers we've found for this tag via nlp. """
            for identifier, metadata in tag.identifiers.items():
                node_types = list(metadata.types) if isinstance(metadata.types, str) else metadata.types
                synonyms = metadata.synonyms if metadata.synonyms else []
                nodes.append({
                    "id": identifier,
                    "name": metadata.label,
                    "category": node_types,
                    "synonyms": synonyms
                })
                nodes_written.add(identifier)
                edges.append(self.make_edge(
                    subj=tag_id,
                    obj=identifier))
                edges.append(self.make_edge(
                    subj=identifier,
                    obj=tag_id))

        concepts_graph = self.convert_to_kgx_json(elements, written_nodes=nodes_written)
        graph['nodes'] += concepts_graph['nodes']
        graph['edges'] += concepts_graph['edges']

        return graph

    def index_elements(self, elements_file):
        log.info(f"Indexing {elements_file}...")
        elements = Util.read_object(elements_file)
        count = 0
        total = len(elements)
        # Index Annotated Elements
        log.info(f"found {len(elements)} from elements files.")
        for element in elements:
            count += 1
            # Only index DugElements as concepts will be indexed differently in next step
            if not isinstance(element, DugConcept):
                self.index_obj.index_element(element, index=self.variables_index)
            percent_complete = (count / total) * 100
            if percent_complete % 10 == 0:
                log.info(f"{percent_complete} %")
        log.info(f"Done indexing {elements_file}.")

    def validate_indexed_elements(self, elements_file):
        elements = [x for x in Util.read_object(elements_file) if not isinstance(x, DugConcept)]
        # Pick ~ 10 %
        sample_size = int(len(elements) * 0.1)
        test_elements = elements[:sample_size]  # random.choices(elements, k=sample_size)
        log.info(f"Picked {len(test_elements)} from {elements_file} for validation.")
        for element in test_elements:
            # Pick a concept
            concepts = [element.concepts[curie] for curie in element.concepts if element.concepts[curie].name]

            if len(concepts):
                # Pick the first concept
                concept = concepts[0]
                curie = concept.id
                search_term = re.sub(r'[^a-zA-Z0-9_\ ]+', '', concept.name)
                log.debug(f"Searching for Concept: {curie} and Search term: {search_term}")
                all_elements_ids = self._search_elements(curie, search_term)
                present = element.id in all_elements_ids
                if not present:
                    log.error(f"Did not find expected variable {element.id} in search result.")
                    log.error(f"Concept id : {concept.id}, Search term: {search_term}")
                    raise Exception(f"Validation exception - did not find variable {element.id} "
                                    f"from {str(elements_file)}"
                                    f"when searching variable index with"
                                    f" Concept ID : {concept.id} using Search Term : {search_term} ")
            else:
                log.info(
                    f"{element.id} has no concepts annotated. Skipping validation for it."
                )

    def _search_elements(self, curie, search_term):
        response = self.event_loop.run_until_complete(self.search_obj.search_vars_unscored(
            concept=curie,
            query=search_term
        ))
        ids_dict = []
        for element_type in response:
            all_elements_ids = [e['id'] for e in
                                reduce(lambda x, y: x + y['elements'], response[element_type], [])]
            ids_dict += all_elements_ids
        return ids_dict

    def crawl_concepts(self, concepts, data_set_name):
        """
        Adds tranql KG to Concepts, terms grabbed from KG are also added as search terms
        :param concepts:
        :param data_set_name:
        :return:
        """
        crawl_dir = Util.dug_crawl_path('crawl_output')
        output_file_name = os.path.join(data_set_name, 'expanded_concepts.pickle')
        extracted_dug_elements_file_name = os.path.join(data_set_name, 'extracted_graph_elements.pickle')
        output_file = Util.dug_expanded_concepts_path(output_file_name)
        extracted_output_file = Util.dug_expanded_concepts_path(extracted_dug_elements_file_name)
        Path(crawl_dir).mkdir(parents=True, exist_ok=True)
        extracted_dug_elements = []
        log.debug("Creating Dug Crawler object")
        crawler = Crawler(
            crawl_file="",
            parser=None,
            annotator=None,
            tranqlizer=self.tranqlizer,
            tranql_queries=self.tranql_queries,
            http_session=self.cached_session,
        )
        crawler.crawlspace = crawl_dir
        counter = 0
        total = len(concepts)
        for concept_id, concept in concepts.items():
            counter += 1
            crawler.expand_concept(concept)
            concept.set_search_terms()
            concept.set_optional_terms()
            for query in self.node_to_element_queries:
                log.info(query)
                casting_config = query['casting_config']
                tranql_source = query['tranql_source']
                dug_element_type = query['output_dug_type']
                extracted_dug_elements += crawler.expand_to_dug_element(
                    concept=concept,
                    casting_config=casting_config,
                    dug_element_type=dug_element_type,
                    tranql_source=tranql_source
                )
            concept.clean()
            percent_complete = int((counter / total) * 100)
            if percent_complete % 10 == 0:
                log.info(f"{percent_complete}%")
        Util.write_object(obj=concepts, path=output_file)
        Util.write_object(obj=extracted_dug_elements, path=extracted_output_file)

    def index_concepts(self, concepts):
        log.info("Indexing Concepts")
        total = len(concepts)
        count = 0
        for concept_id, concept in concepts.items():
            count += 1
            self.index_obj.index_concept(concept, index=self.concepts_index)
            # Index knowledge graph answers for each concept
            for kg_answer_id, kg_answer in concept.kg_answers.items():
                self.index_obj.index_kg_answer(
                    concept_id=concept_id,
                    kg_answer=kg_answer,
                    index=self.kg_index,
                    id_suffix=kg_answer_id
                )
            percent_complete = int((count / total) * 100)
            if percent_complete % 10 == 0:
                log.info(f"{percent_complete} %")
        log.info("Done Indexing concepts")

    def validate_indexed_concepts(self, elements, concepts):
        """
        Validates linked concepts are searchable
        :param elements: Annotated dug elements
        :param concepts: Crawled (expanded) concepts
        :return:
        """
        # 1 . Find concepts with KG <= 10% of all concepts,
        # <= because we might have no results for some concepts from tranql
        sample_concepts = {key: value for key, value in concepts.items() if value.kg_answers}
        if len(concepts) == 0:
            log.info(f"No Concepts found.")
            return
        log.info(
            f"Found only {len(sample_concepts)} Concepts with Knowledge graph out of {len(concepts)}. {(len(sample_concepts) / len(concepts)) * 100} %")
        # 2. pick elements that have concepts in the sample concepts set
        sample_elements = {}
        for element in elements:
            if isinstance(element, DugConcept):
                continue
            for concept in element.concepts:
                # add elements that have kg
                if concept in sample_concepts:
                    sample_elements[concept] = sample_elements.get(concept, set())
                    sample_elements[concept].add(element.id)

        # Time for some validation
        for curie in concepts:
            concept = concepts[curie]
            if not len(concept.kg_answers):
                continue
            search_terms = []
            for key in concept.kg_answers:
                kg_object = concept.kg_answers[key]
                search_terms += kg_object.get_node_names()
                search_terms += kg_object.get_node_synonyms()
                # reduce(lambda x,y: x + y, [[node.get("name")] + node.get("synonyms", [])
                #             for node in concept.kg_answers["knowledge_graph"]["nodes"]], [])
            # validation here is that for any of these nodes we should get back
            # the variable.
            # make unique
            search_terms_cap = 10
            search_terms = list(set(search_terms))[:search_terms_cap]
            log.debug(f"Using {len(search_terms)} Search terms for concept {curie}")
            for search_term in search_terms:
                # avoids elastic failure due to some reserved characters
                # 'search_phase_execution_exception', 'token_mgr_error: Lexical error ...
                search_term = re.sub(r'[^a-zA-Z0-9_\ ]+', '', search_term)

                searched_element_ids = self._search_elements(curie, search_term)

                present = bool(len([x for x in sample_elements[curie] if x in searched_element_ids]))
                if not present:
                    log.error(f"Did not find expected variable {element.id} in search result.")
                    log.error(f"Concept id : {concept.id}, Search term: {search_term}")
                    raise Exception(f"Validation error - Did not find {element.id} for"
                                    f" Concept id : {concept.id}, Search term: {search_term}")

    def clear_index(self, index_id):
        exists = self.search_obj.es.indices.exists(index_id)
        if exists:
            log.info(f"Deleting index {index_id}")
            response = self.search_obj.es.indices.delete(index_id)
            log.info(f"Cleared Elastic : {response}")
        log.info("Re-initializing the indicies")
        self.index_obj.init_indices()

    def clear_variables_index(self):
        self.clear_index(self.variables_index)

    def clear_kg_index(self):
        self.clear_index(self.kg_index)

    def clear_concepts_index(self):
        self.clear_index(self.concepts_index)


class DugUtil():

    @staticmethod
    def clear_annotation_cached(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            annotation_path = Util.dug_annotation_path("")
            Util.clear_dir(annotation_path)
            # Clear http session cache
            if config.annotation.clear_http_cache:
                dug.cached_session.cache.clear()

    @staticmethod
    def annotate_db_gap_files(config=None, to_string=False, files=None):
        with Dug(config, to_string=to_string) as dug:
            if files is None:
                files = Util.dug_dd_xml_objects()
            parser_name = "DbGaP"
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def annotate_anvil_files(config=None, to_string=False, files=None):
        with Dug(config, to_string=to_string) as dug:
            if files is None:
                files = Util.dug_anvil_objects()
            parser_name = "Anvil"
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def annotate_cancer_commons_files(config=None, to_string=False, files=None):
        with Dug(config, to_string=to_string) as dug:
            if files is None:
                files = Util.dug_crdc_objects()
            parser_name = "crdc"
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def annotate_kids_first_files(config=None, to_string=False, files=None):
        with Dug(config, to_string=to_string) as dug:
            if files is None:
                files = Util.dug_kfdrc_objects()
            parser_name = "kfdrc"
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def annotate_nida_files(config=None, to_string=False, files=None):
        with Dug(config, to_string=to_string) as dug:
            if files is None:
                files = Util.dug_nida_objects()
            parser_name = "NIDA"
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def annotate_sparc_files(config=None, to_string=False, files=None):
        with Dug(config, to_string=to_string) as dug:
            if files is None:
                files = Util.dug_sparc_objects()
            parser_name = "SciCrunch"
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def annotate_sprint_files(config=None, to_string=False, files=None):
        with Dug(config, to_string=to_string) as dug:
            if files is None:
                files = Util.dug_sprint_objects()
            parser_name = "SPRINT"
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def annotate_topmed_files(config=None, to_string=False, files=None):
        with Dug(config, to_string=to_string) as dug:
            if files is None:
                files = Util.dug_topmed_objects()
            parser_name = "TOPMedTag"
            log.info(files)
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def annotate_bacpac_files(config=None, to_string=False, files=None):
        with Dug(config, to_string=to_string) as dug:
            if files is None:
                files = Util.dug_bacpac_objects()
            parser_name = "BACPAC"
            log.info(files)
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def make_kg_tagged(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            output_base_path = Util.dug_kgx_path("")
            Util.clear_dir(output_base_path)
            log.info("Starting building KGX files")
            elements_files = Util.dug_elements_objects()
            for file in elements_files:
                elements = Util.read_object(file)
                if "topmed_" in file:
                    kg = dug.make_tagged_kg(elements)
                else:
                    kg = dug.convert_to_kgx_json(elements)
                dug_base_file_name = file.split(os.path.sep)[-2]
                output_file_path = os.path.join(output_base_path, dug_base_file_name + '_kgx.json')
                Util.write_object(kg, output_file_path)
                log.info(f"Wrote {len(kg['nodes'])} nodes and {len(kg['edges'])} edges, to {output_file_path}.")
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def index_variables(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            dug.clear_variables_index()
            elements_object_files = Util.dug_elements_objects()
            for file in elements_object_files:
                dug.index_elements(file)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def index_extracted_elements(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            elements_object_files = Util.dug_extracted_elements_objects()
            for file in elements_object_files:
                dug.index_elements(file)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def index_concepts(config=None, to_string=False):
        with Dug(config=config, to_string=to_string) as dug:
            # These are concepts that have knowledge graphs  from tranql
            # clear out concepts and kg indicies from previous runs
            dug.clear_concepts_index()
            dug.clear_kg_index()
            expanded_concepts_files = Util.dug_expanded_concept_objects()
            for file in expanded_concepts_files:
                concepts = Util.read_object(file)
                dug.index_concepts(concepts=concepts)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def validate_indexed_variables(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            elements_object_files = Util.dug_elements_objects()
            for elements_object_file in elements_object_files:
                log.info(f"Validating {elements_object_file}")
                dug.validate_indexed_elements(elements_object_file)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def crawl_tranql(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            concepts_files = Util.dug_concepts_objects()
            crawl_dir = Util.dug_crawl_path('crawl_output')
            log.info(f'Clearing crawl output dir {crawl_dir}')
            Util.clear_dir(crawl_dir)
            expanded_concepts_dir = Util.dug_expanded_concepts_path("")
            log.info(f'Clearing expanded concepts dir: {expanded_concepts_dir}')
            Util.clear_dir(expanded_concepts_dir)
            log.info(f'Crawling Dug Concepts, found {len(concepts_files)} file(s).')
            for file in concepts_files:
                data_set = Util.read_object(file)
                original_variables_dataset_name = os.path.split(os.path.dirname(file))[-1]
                dug.crawl_concepts(concepts=data_set,
                                   data_set_name=original_variables_dataset_name)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def validate_indexed_concepts(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            get_data_set_name = lambda file: os.path.split(os.path.dirname(file))[-1]
            expanded_concepts_files_dict = {
                get_data_set_name(file): file for file in Util.dug_expanded_concept_objects()
            }
            annotated_elements_files_dict = {
                get_data_set_name(file): file for file in Util.dug_elements_objects()
            }
            try:
                assert len(expanded_concepts_files_dict) == len(annotated_elements_files_dict)
            except:
                log.error("Files Annotated Elements files and Expanded concepts files, should be pairs")
                if len(expanded_concepts_files_dict) > len(annotated_elements_files_dict):
                    log.error("Some Annotated Elements files (from load_and_annotate task) are missing")
                else:
                    log.error("Some Expanded Concepts files (from crawl task) are missing")
                log.error(f"Annotated Datasets : {list(annotated_elements_files_dict.keys())}")
                log.error(f"Expanded Concepts Datasets: {list(expanded_concepts_files_dict.keys())}")
                exit(-1)
            for data_set_name in annotated_elements_files_dict:
                log.debug(f"Reading concepts and elements for dataset {data_set_name}")
                elements_file_path = annotated_elements_files_dict[data_set_name]
                concepts_file_path = expanded_concepts_files_dict[data_set_name]
                dug_elements = Util.read_object(elements_file_path)
                dug_concepts = Util.read_object(concepts_file_path)
                log.debug(f"Read {len(dug_elements)} elements, and {len(dug_concepts)} Concepts")
                log.info(f"Validating {data_set_name}")
                dug.validate_indexed_concepts(elements=dug_elements, concepts=dug_concepts)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log


class FileFetcher:

    def __init__(
            self,
            remote_host: str,
            remote_dir: Union[str, Path],
            local_dir: Union[str, Path] = "."
    ):
        self.remote_host = remote_host
        self.remote_dir = remote_dir.rstrip("/") if isinstance(remote_dir, str) else str(remote_dir.as_posix())
        self.local_dir = Path(local_dir).resolve()

    def __call__(self, remote_file_path: Union[str, Path]) -> Path:
        remote_path = self.remote_dir + "/" + remote_file_path
        local_path = self.local_dir / remote_file_path
        url = f"{self.remote_host}{remote_path}"
        log.debug(f"Fetching {url}")
        try:
            response = requests.get(url, allow_redirects=True)
        except Exception as e:
            log.error(f"Unexpected {e.__class__.__name__}: {e}")
            raise RuntimeError(f"Unable to fetch {url}")
        else:
            log.debug(f"Response: {response.status_code}")
            if response.status_code == 200:
                with local_path.open('wb') as file_obj:
                    file_obj.write(response.content)
                return local_path
            else:
                log.debug(f"Unable to fetch {url}: {response.status_code}")
                raise RuntimeError(f"Unable to fetch {url}")


def get_versioned_files(config: RogerConfig, data_format, output_file_path, data_store="s3", unzip=False):
    """
       Fetches a dug inpu data files to input file directory
    """
    meta_data = Util.read_relative_object("../metadata.yaml")
    output_dir: Path = Util.dug_input_files_path(output_file_path)
    # clear dir
    Util.clear_dir(output_dir)
    data_sets = config.dug_inputs.data_sets
    pulled_files = []
    s3_utils = S3Utils(config.s3_config)
    for data_set in data_sets:
        data_set_name, current_version = data_set.split(':')
        for item in meta_data["dug_inputs"]["versions"]:
            if item["version"] == current_version and item["name"] == data_set_name and item["format"] == data_format:
                if data_store == "s3":
                    for filename in item["files"]["s3"]:
                        log.info(f"Fetching {filename}")
                        output_name = filename.split('/')[-1]
                        output_path = output_dir / output_name
                        s3_utils.get(
                            str(filename),
                            str(output_path),
                        )
                        if unzip:
                            log.info(f"Unzipping {output_path}")
                            tar = tarfile.open(str(output_path))
                            tar.extractall(path=output_dir)
                        pulled_files.append(output_path)
                else:
                    for filename in item["files"]["stars"]:
                        log.info(f"Fetching {filename}")
                        # fetch from stars
                        remote_host = config.annotation_base_data_uri
                        fetch = FileFetcher(
                            remote_host=remote_host,
                            remote_dir=current_version,
                            local_dir=output_dir)
                        output_path = fetch(filename)
                        if unzip:
                            log.info(f"Unzipping {output_path}")
                            tar = tarfile.open(str(output_path))
                            tar.extractall(path=output_dir)
                        pulled_files.append(output_path)
    return [str(filename) for filename in pulled_files]


def get_dbgap_files(config: RogerConfig, to_string=False) -> List[str]:
    return get_versioned_files(config, 'dbGaP', 'db_gap', data_store=config.dug_inputs.data_source, unzip=True)


def get_nida_files(config: RogerConfig, to_string=False) -> List[str]:
    return get_versioned_files(config, "nida", "nida", data_store=config.dug_inputs.data_source, unzip=True)


def get_sparc_files(config: RogerConfig, to_string=False) -> List[str]:
    return get_versioned_files(config, "sparc", "sparc", data_store=config.dug_inputs.data_source, unzip=True)


def get_anvil_files(config: RogerConfig, to_string=False) -> List[str]:
    return get_versioned_files(config, "anvil", "anvil", data_store=config.dug_inputs.data_source, unzip=True)


def get_kids_first_files(config: RogerConfig, to_string=False) -> List[str]:
    return get_versioned_files(config, "kfdrc", "kfdrc", data_store=config.dug_inputs.data_source, unzip=True)


def get_cancer_data_commons_files(config: RogerConfig, to_string=False) -> List[str]:
    return get_versioned_files(config, "crdc", "crdc", data_store=config.dug_inputs.data_source, unzip=True)


def get_sprint_files(config: RogerConfig, to_string=False) -> List[str]:
    return get_versioned_files(config, "sprint", "sprint", data_store=config.dug_inputs.data_source, unzip=True)

def get_bacpac_files(config: RogerConfig, to_string=False) -> List[str]:
    return get_versioned_files(config, "bacpac", "bacpac", data_store=config.dug_inputs.data_source, unzip=True)

def get_topmed_files(config: RogerConfig, to_string=False) -> List[str]:
    return get_versioned_files(config, "topmed", "topmed", data_store=config.dug_inputs.data_source, unzip=False)


