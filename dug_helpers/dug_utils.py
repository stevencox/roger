import json
from dug.annotate import DugAnnotator, Annotator, Normalizer, OntologyHelper, Preprocessor, SynonymFinder
from dug.parsers import DugConcept, DugElement
from dug.core import Search, get_parser, Crawler
from roger.roger_util import get_logger
from roger.Config import get_default_config as get_config
from requests_cache import CachedSession
import os
from pathlib import Path
from roger.core import Util
from io import StringIO
import hashlib
import logging
import dug.tranql as tql
import redis
import pickle

log = get_logger()


class Dug:
    annotator = None
    search_obj = None
    config = None
    cached_session = None

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

        if not Dug.search_obj:
            # Dug search expects these to be set as os envrion
            # Elastic config
            elastic_conf = config.get("elastic_search")
            os.environ['ELASTIC_API_HOST'] = elastic_conf.get("host")
            os.environ['ELASTIC_USERNAME'] = elastic_conf.get("username")
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
            with open(os.path.join(elements_file_path, elements_file_name), 'wb') as f:
                pickle.dump(elements, f)
                log.info(f"Pickled annotated elements to : {elements_file_path}/{elements_file_name}")
            with open(os.path.join(elements_file_path, concepts_file_name), 'wb') as f:
                pickle.dump(non_expanded_concepts, f)
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
    def index_variables(variables):
        pass
        # Dug.search_obj.index_variables(variables, "variables_index")

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
            output_log = dug.log_stream.getvalue()
        return output_log

    @staticmethod
    def make_kg_tagged(config=None, to_string=False):
        with Dug(config) as dug:
            output_base_path = Util.dug_kgx_path("")
            log.info("Starting building KGX files")
            elements_files = Util.dug_elements_objects()
            for file in elements_files:
                with open(file, "rb") as f:
                    elements = pickle.load(f)
                    if "topmed_" in file:
                        kg = dug.make_tagged_kg(elements)
                    else:
                        kg = dug.convert_to_kgx_json(elements)
                    dug_base_file_name = file.split(os.path.sep)[-2]
                    output_file_path = os.path.join(output_base_path, dug_base_file_name + '_kgx.json')
                    Util.write_object(kg, output_file_path)
                    log.info(f"Wrote {len(kg['nodes'])} nodes and {len(kg['edges'])} edges, to {output_file_path}.")


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
