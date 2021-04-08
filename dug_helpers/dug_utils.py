from dug.annotate import DugAnnotator, Annotator, Normalizer, OntologyHelper, Preprocessor, SynonymFinder, ConceptExpander
from dug.parsers import DugConcept, DugElement
from dug.core import Search, get_parser, Crawler
from roger.roger_util import get_logger
from roger.Config import get_default_config as get_config
from requests_cache import CachedSession
import os
import re
from pathlib import Path
from roger.core import Util
from io import StringIO
import hashlib
import logging
import dug.tranql as tql
import redis
from functools import reduce

log = get_logger()


class Dug:
    annotator = None
    search_obj = None
    tranqlizer = None
    tranql_queries = None
    config = None
    cached_session = None
    VARIABLES_INDEX = None
    CONCEPTS_INDEX = None
    KG_INDEX = None

    def __init__(self, config=None, to_string=True):
        if not config:
            Dug.config = get_config()
        if to_string:
            self.log_stream = StringIO()
            self.string_handler = logging.StreamHandler (self.log_stream)
            log.addHandler(self.string_handler)
        Dug.config = config
        if not Dug.annotator:
            annotation_config = self.config.get("annotation")
            preprocessor = Preprocessor(**annotation_config["preprocessor"])
            annotator = Annotator(url=annotation_config["annotator"])
            normalizer = Normalizer(url=annotation_config["normalizer"])
            synonym_finder = SynonymFinder(url=annotation_config["synonym_service"])
            ontology_helper = OntologyHelper(url=annotation_config["ontology_metadata"])

            redis_config = {
                'host': self.config.get('redisgraph', {}).get('host'),
                'port': self.config.get('redisgraph', {}).get('port'),
                'password': self.config.get('redisgraph', {}).get('password')
            }
            Dug.cached_session = CachedSession(cache_name='annotator',
                                                backend='redis',
                                                connection=redis.StrictRedis(**redis_config))

            Dug.annotator = DugAnnotator(
                preprocessor=preprocessor,
                annotator=annotator,
                normalizer=normalizer,
                synonym_finder=synonym_finder,
                ontology_helper=ontology_helper
            )

        if not Dug.tranqlizer:
            graph_name = Dug.config["redisgraph"]["graph"]
            source = f"redis:{graph_name}"
            indexing_config = self.config.get('indexing')
            queries_config = indexing_config["queries"]
            Dug.tranql_queries = {
                key: tql.QueryFactory(queries_config[key], source)
                for key in queries_config
            }
            Dug.tranqlizer = ConceptExpander(**{
                "url": indexing_config["tranql_endpoint"],
                "min_tranql_score": indexing_config["tranql_min_score"]
            })

        if not Dug.search_obj:
            # Dug search expects these to be set as os envrion
            # Elastic config
            elastic_conf = config.get("elastic_search")
            os.environ['ELASTIC_API_HOST'] = elastic_conf.get("host")
            os.environ['ELASTIC_USERNAME'] = elastic_conf.get("username")
            os.environ['ELASTIC_PASSWORD'] = elastic_conf.get("password")
            os.environ['NBOOST_API_HOST'] = elastic_conf.get("nboost_host")
            indexing_config = config.get('indexing')
            Dug.VARIABLES_INDEX = indexing_config.get('variables_index')
            Dug.CONCEPTS_INDEX = indexing_config.get('concepts_index')
            Dug.KG_INDEX = indexing_config.get('kg_index')
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
    def annotate_files(parser_name, parsable_files):
        """
        Annotates a Data element file using a Dug parser.
        :param parser_name: Name of Dug parser to use.
        :param parsable_files: Files to parse.
        :return: None.
        """
        parser = get_parser(parser_name)
        output_base_path = Util.dug_annotation_path('')
        log.info("Parsing files")
        for file in parsable_files:
            log.debug("Creating Dug Crawler object")
            crawler = Crawler(
                crawl_file=file,
                parser=parser,
                annotator=Dug.annotator,
                tranqlizer='',
                tranql_queries=[],
                http_session= Dug.cached_session
            )

            # configure output space.
            current_file_name = '.'.join(os.path.basename(file).split('.')[:-1])
            elements_file_path = os.path.join(output_base_path, current_file_name)
            elements_file_name = 'elements.pickle'
            concepts_file_name = 'concepts.pickle'

            # create an empty elements file. This also creates output dir if it doesn't exist.
            log.debug(f"Creating empty file:  {elements_file_path}/element_file.json")
            Util.write_object({}, os.path.join(elements_file_path, 'element_file.json'))
            crawler.elements = parser.parse(file)

            # @TODO propose for Dug to make this a crawler class init parameter(??)
            crawler.crawlspace = elements_file_path
            crawler.annotate_elements()

            # Extract out the concepts gotten out of annotation
            # Extract out the elements
            non_expanded_concepts = crawler.concepts
            elements = crawler.elements

            # Write pickles of objects to file
            log.info(f"Parsed and annotated: {file}")
            elements_out_file = os.path.join(elements_file_path, elements_file_name)
            Util.write_object(elements, elements_out_file)
            log.info(f"Pickled annotated elements to : {elements_file_path}/{elements_file_name}")
            concepts_out_file = os.path.join(elements_file_path, concepts_file_name)
            Util.write_object(non_expanded_concepts, concepts_out_file)
            log.info(f"Pickled annotated concepts to : {elements_file_path}/{concepts_file_name}")

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
    def convert_to_kgx_json(elements):
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
        written_nodes = set()
        for index, element in enumerate(elements):
            # DugElement means a variable (Study variable...)
            if not isinstance(element, DugElement):
                continue
            study_id = element.collection_id
            if study_id not in written_nodes:
                nodes.append({
                    "id": study_id,
                    "category": ["biolink:ClinicalTrial"],
                    "name": study_id
                })
                written_nodes.add(study_id)
            """ connect the study and the variable. """
            edges.append(Dug.make_edge(
                subj=element.id,
                relation_label='part of',
                relation='BFO:0000050',
                obj=study_id,
                predicate='biolink:part_of',
                predicate_label='part of'))
            edges.append(Dug.make_edge(
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
                "category": ["biolink:ClinicalModifier"],
                "description": element.description
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
                elif identifier.startswith("TOPMED.TAG:") :
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
                edges.append(Dug.make_edge(
                    subj=element.id,
                    relation='OBAN:association',
                    obj=identifier,
                    relation_label='association',
                    predicate='biolink:Association',
                    predicate_label='association'))
                edges.append(Dug.make_edge(
                    subj=identifier,
                    relation='OBAN:association',
                    obj=element.id,
                    relation_label='association',
                    predicate='biolink:Association',
                    predicate_label='association'))
        return graph

    @staticmethod
    def make_tagged_kg(elements):
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
        for tag in elements:
            if not (isinstance(tag, DugConcept) and tag.type == topmed_tag_concept_type):
                continue
            tag_id = tag.id
            tag_map[tag_id] = tag
            nodes.append({
                "id": tag_id,
                "name": tag.name,
                "description": tag.description,
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
                edges.append(Dug.make_edge(
                    subj=tag_id,
                    obj=identifier))
                edges.append(Dug.make_edge(
                    subj=identifier,
                    obj=tag_id))

        """ Create nodes and edges to model variables, studies, and their
        relationships to tags. """
        for variable in elements:
            if not isinstance(variable, DugElement):
                continue
            variable_id = variable.id
            variable_name = variable.name

            # These contain other concepts that the variable is annotate with.
            # These But here we want to link them with topmed tags only
            # The tags are supposed to be linked with the other concepts.
            # So We will filter out the Topmed Tag here.
            tag_ids = [x for x in variable.concepts.keys() if x.startswith('TOPMED.TAG')]
            if len(tag_ids) != 1:
                log.error(f"Topmed tags Tags for element {variable} > 1...")
            study_id = variable.collection_id
            study_name = variable.collection_name
            tag_id = tag_ids[0]
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
    def index_elements(elements_file):
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
                Dug.search_obj.index_element(element, index=Dug.VARIABLES_INDEX)
            percent_complete = (count / total)* 100
            if percent_complete % 10 == 0:
                log.info(f"{percent_complete} %")
        log.info(f"Done indexing {elements_file}.")

    @staticmethod
    def validate_indexed_elements(elements_file):
        elements = [x for x in Util.read_object(elements_file) if not isinstance(x, DugConcept)]
        # Pick ~ 10 %
        sample_size = int(len(elements) * 0.1)
        test_elements = elements[:sample_size] #random.choices(elements, k=sample_size)
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
                all_elements_ids = Dug._search_elements(curie, search_term)
                present = element.id in all_elements_ids
                if not present:
                    log.error(f"Did not find expected variable {element.id} in search result.")
                    log.error(f"Concept id : {concept.id}, Search term: {search_term}")
                    exit(-1)
            else:
                log.info(
                    f"{element.id} has no concepts annotated. Skipping validation for it."
                )

    @staticmethod
    def _search_elements(curie, search_term):
        response = Dug.search_obj.search_variables(
            index=Dug.VARIABLES_INDEX,
            concept=curie,
            query=search_term,
            size=1000
        )
        ids_dict = []
        for element_type in response:
            all_elements_ids = [e['id'] for e in
                                reduce(lambda x, y: x + y['elements'], response[element_type], [])]
            ids_dict += all_elements_ids
        return ids_dict

    @staticmethod
    def crawl_concepts(concepts, data_set_name):
        """
        Adds tranql KG to Concepts, terms grabbed from KG are also added as search terms
        :param concepts:
        :param data_set_name:
        :return:
        """
        crawl_dir = Util.dug_crawl_path('crawl_output')
        output_file_name = os.path.join(data_set_name, 'expanded_concepts.pickle')
        output_file = Util.dug_expanded_concepts_path(output_file_name)
        Path(crawl_dir).mkdir(parents=True, exist_ok=True)

        log.debug("Creating Dug Crawler object")
        crawler = Crawler(
            crawl_file="",
            parser=None,
            annotator=None,
            tranqlizer=Dug.tranqlizer,
            tranql_queries= Dug.tranql_queries,
            http_session= Dug.cached_session
        )
        crawler.crawlspace = crawl_dir
        counter= 0
        total = len(concepts)
        for concept_id, concept in concepts.items():
            counter += 1
            crawler.expand_concept(concept)
            concept.set_search_terms()
            concept.set_optional_terms()
            concept.clean()
            percent_complete = int((counter/total)*100)
            if percent_complete % 10 == 0:
                log.info(f"{percent_complete}%")
        Util.write_object(obj=concepts, path=output_file)

    @staticmethod
    def index_concepts(concepts):
        log.info("Indexing Concepts")
        total = len(concepts)
        count = 0
        for concept_id, concept in concepts.items():
            count += 1
            Dug.search_obj.index_concept(concept, index=Dug.CONCEPTS_INDEX)
            # Index knowledge graph answers for each concept
            for kg_answer_id, kg_answer in concept.kg_answers.items():
                Dug.search_obj.index_kg_answer(concept_id=concept_id,
                                       kg_answer=kg_answer,
                                       index=Dug.KG_INDEX,
                                       id_suffix=kg_answer_id)
            percent_complete = int((count/total) * 100)
            if percent_complete % 10 == 0:
                log.info(f"{percent_complete} %")
        log.info("Done Indexing concepts")

    @staticmethod
    def validate_indexed_concepts(elements, concepts):
        """
        Validates linked concepts are searchable
        :param elements: Annotated dug elements
        :param concepts: Crawled (expanded) concepts
        :return:
        """
        #1 . Find concepts with KG <= 10% of all concepts,
        # <= because we might have no results for some concepts from tranql
        size = int(len(concepts)*0.1)
        sample_concepts = {key: value for key, value in concepts.items() if value.kg_answers }
        log.info(f"Found only {len(sample_concepts)} Concepts with Knowledge graph out of {len(concepts)}. {(len(sample_concepts)/ len(concepts))*100} %")
        # 2. pick elements that have concepts in the sample concepts set
        sample_elements = {}
        for element in elements:
            if isinstance(element, DugConcept):
                continue
            for concept in element.concepts:
                # add elements that have kg
                if concept in sample_concepts:
                    sample_elements[concept] = sample_elements.get(concept,set())
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
            search_terms = set(search_terms)
            log.debug(f"Found {len(search_terms)} Search terms for concept {curie}")
            for search_term in search_terms:
                # avoids elastic failure due to some reserved characters
                # 'search_phase_execution_exception', 'token_mgr_error: Lexical error ...
                try:
                    search_term = re.sub(r'[^a-zA-Z0-9_\ ]+', '', search_term)

                    searched_element_ids = Dug._search_elements(curie, search_term)
                except:
                    print(f'{search_term}')
                present = bool(len([x for x in sample_elements[curie] if x in searched_element_ids]))
                if not present:
                    log.error(f"Did not find expected variable {element.id} in search result.")
                    log.error(f"Concept id : {concept.id}, Search term: {search_term}")
                    exit(-1)


class DugUtil():

    @staticmethod
    def load_and_annotate(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            # This needs to be meta data driven (?)
            # annotation:
            #   - dir: <topmed_dir>
            #     parser: "Dug parser name"
            #     kg_type : <harmonized (Topmed graph) vs non-harmonized (Dbgap graph) > ?
            topmed_files = Util.dug_topmed_objects()
            dd_xml_files = Util.dug_dd_xml_objects()
            # Parse db gap
            parser_name = "DbGaP"
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=dd_xml_files)
            # Parse and annotate Topmed
            parser_name = "TOPMedTag"
            dug.annotate_files(parser_name=parser_name,
                               parsable_files=topmed_files)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def make_kg_tagged(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            output_base_path = Util.dug_kgx_path("")
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
            elements_object_files = Util.dug_elements_objects()
            for file in elements_object_files:
                dug.index_elements(file)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

    @staticmethod
    def index_concepts(config=None, to_string=False):
        with Dug(config=config, to_string=to_string) as dug:
            # These are concepts that have knowledge graphs  from tranql
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
                dug.validate_indexed_elements(elements_object_file)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log


    @staticmethod
    def crawl_tranql(config=None, to_string=False):
        with Dug(config, to_string=to_string) as dug:
            concepts_files = Util.dug_concepts_objects()
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
                log.debug(f"Reading concepts and elements for dataset { data_set_name }")
                elements_file_path = annotated_elements_files_dict[data_set_name]
                concepts_file_path = expanded_concepts_files_dict[data_set_name]
                dug_elements = Util.read_object(elements_file_path)
                dug_concepts = Util.read_object(concepts_file_path)
                log.debug(f"Read {len(dug_elements)} elements, and {len(dug_concepts)} Concepts")
                log.info(f"Validating {data_set_name}")
                dug.validate_indexed_concepts(elements=dug_elements, concepts=dug_concepts)
            output_log = dug.log_stream.getvalue() if to_string else ''
        return output_log

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
