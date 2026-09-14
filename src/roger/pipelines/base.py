"Base class for implementing a dataset annotate, crawl, and index pipeline"

import os
import random
import threading
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import logging
import re
import hashlib
import traceback
from datetime import datetime, timezone
from functools import reduce
from pathlib import Path
import tarfile
from typing import Union
import jsonpickle
from dug_data_model.v2 import dedupe_and_sort

import requests

from dug.core import get_parser, get_annotator, get_plugin_manager, DugConcept, DugVariable, DugStudy, DugSection
from dug.core.concept_expander import ConceptExpander
from dug.core.crawler import Crawler
from dug.core.factory import DugFactory
from dug.core.parsers import Parser, DugElement
from dug.core.annotators import Annotator
from dug.core.annotators.sapbert_annotator import AnnotateSapbert
from dug.core.async_search import Search
from dug.core.index import Index

from roger.config import RogerConfig
from roger.core import storage
from roger.models.biolink import BiolinkModel
from roger.logger import get_logger

from roger.utils.http_utils import enable_post_caching, harden_session
from roger.utils.batched_annotator import BatchedAnnotator
from roger.utils.s3_utils import S3Utils

log = get_logger()

class PipelineException(Exception):
    "Exception raised from DugPipeline and related classes"

def make_edge(subj,
              obj,
              predicate='biolink:related_to',
              predicate_label='related to',
              relation='biolink:related_to',
              relation_label='related to'
              ):
    """Create an edge between two nodes.

    :param subj: The identifier of the subject.
    :param pred: The predicate linking the subject and object.
    :param obj: The object of the relation.
    :param predicate: Biolink compatible edge type.
    :param predicate_label: Edge label.
    :param relation: Ontological edge type.
    :param relation_label: Ontological edge type label.
    :returns: Returns and edge.
    """
    edge_id = hashlib.md5(
        f'{subj}{predicate}{obj}'.encode('utf-8')).hexdigest()
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

# The six list fields dug's Index.index_element unions when a document id is
# already present. It matters: the same CDE variable id appears in several
# element files (e.g. BRTHDTC in both adult- and pediatric-demographic) with
# different concepts and parents, and search must find it by any of them.
MERGED_LIST_FIELDS = ('search_terms', 'optional_terms', 'parents',
                      'programs', 'identifiers')


def merge_searchable_docs(prior: dict, new: dict) -> dict:
    """Union the list fields of two searchable dicts for the same id.

    Scalars (name, description, data_type, ...) are taken from `new`; dug's
    per-doc update path left them at whatever was written first, which let
    edits upstream go stale.
    """
    merged = dict(new)
    for field in MERGED_LIST_FIELDS:
        merged[field] = dedupe_and_sort(
            (prior.get(field) or []) + (new.get(field) or []))
    tags = (prior.get('tags') or []) + (new.get('tags') or [])
    merged['tags'] = [dict(t) for t in
                      {tuple(sorted(d.items())) for d in tags}]
    return merged


class FileFetcher:
    """A basic remote file fetcher class
    """

    def __init__(
            self,
            remote_host: str,
            remote_dir: Union[str, Path],
            local_dir: Union[str, Path] = "."
    ):
        self.remote_host = remote_host
        if isinstance(remote_dir, str):
            self.remote_dir = remote_dir.rstrip("/")
        else:
            self.remote_dir = str(remote_dir.as_posix())
        self.local_dir = Path(local_dir).resolve()

    def __call__(self, remote_file_path: Union[str, Path]) -> Path:
        remote_path = self.remote_dir + "/" + remote_file_path
        local_path = self.local_dir / remote_file_path
        url = f"{self.remote_host}{remote_path}"
        log.debug("Fetching %s", url)
        try:
            response = requests.get(url, allow_redirects=True, timeout=60)
        except Exception as e:
            log.error("Unexpected %s: %s", e.__class__.__name__, str(e))
            raise RuntimeError(f"Unable to fetch {url}") from e

        log.debug("Response: %d", response.status_code)
        if response.status_code != 200:
            log.debug("Unable to fetch %s: %d", url, response.status_code)
            raise RuntimeError(f"Unable to fetch {url}")

        with local_path.open('wb') as file_obj:
            file_obj.write(response.content)
        return local_path

class DugPipeline():
    "Base class for dataset pipelines"

    pipeline_name = None
    unzip_source = True
    input_version = ""

    def __init__(self, config: RogerConfig, to_string=False):
        "Set instance variables and check to make sure we're overriden"
        if not self.pipeline_name:
            raise PipelineException(
                "Subclass must at least define pipeline_name as class var")
        self.config = config
        self.bl_toolkit = BiolinkModel()
        dug_conf = config.to_dug_conf()
        self.element_mapping = config.indexing.element_mapping
        self.factory = DugFactory(dug_conf)
        # dug builds this session with no timeout, so bound it here before
        # handing it to the Crawler. This is the session every annotation
        # call goes through.
        self.annotation_conf = config.annotation
        self.cached_session = self.build_annotation_session()
        # one session and annotator per worker thread; requests.Session is
        # not documented as thread safe and a silently corrupted annotation
        # run costs weeks
        self._thread_local = threading.local()
        self.event_loop = asyncio.new_event_loop()
        self.log_stream = StringIO()
        if to_string:
            self.string_handler = logging.StreamHandler(self.log_stream)
            log.addHandler(self.string_handler)
        self.s3_utils = S3Utils(self.config.s3_config)

        self.tranqlizer: ConceptExpander = self.factory.build_tranqlizer()

        graph_name = self.config["redisgraph"]["graph"]
        source = f"redis:{graph_name}"
        self.tranql_queries: dict = self.factory.build_tranql_queries(source)
        self.node_to_element_queries: list = (
            self.factory.build_element_extraction_parameters(source))

        indexing_config = config.indexing
        self.variables_index = indexing_config.get('variables_index')
        self.studies_index = indexing_config.get('studies_index')
        self.concepts_index = indexing_config.get('concepts_index')
        self.sections_index = indexing_config.get('sections_index')
        self.kg_index = indexing_config.get('kg_index')

        self.search_obj = None 
        self.index_obj = None 


    def build_annotation_session(self):
        """A hardened, POST-caching http session for annotation calls.

        Built per call rather than shared so each annotate worker thread can
        hold its own.
        """
        session = harden_session(
            self.factory.build_http_session(),
            connect_timeout=self.annotation_conf.http_connect_timeout,
            read_timeout=self.annotation_conf.http_read_timeout,
            retries=self.annotation_conf.http_retries,
            backoff_factor=self.annotation_conf.http_retry_backoff,
        )
        if self.annotation_conf.cache_post_requests:
            enable_post_caching(
                session,
                expire_seconds=self.annotation_conf.http_cache_expire_seconds)
        return session

    def thread_annotation_context(self):
        """(session, annotator) owned by the calling thread.

        The redis-backed response cache is shared, so worker threads still
        see each other's annotations; only the client objects are private.
        """
        local = self._thread_local
        if getattr(local, 'session', None) is None:
            local.session = self.build_annotation_session()
            local.annotator = self.init_annotator()
        return local.session, local.annotator

    def __enter__(self):
        self.event_loop = asyncio.new_event_loop()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.search_obj:
        # close elastic search connection
            self.event_loop.run_until_complete(self.search_obj.es.close())
            # close async loop
            if self.event_loop.is_running() and not self.event_loop.is_closed():
                self.event_loop.close()
            if exc_type or exc_val or exc_tb:
                traceback.print_exc()
                log.error("%s %s %s", exc_val, exc_val, exc_tb)
                log.exception("Got an exception")

    def get_data_format(self):
        """Access method for data_format parameter

        Defaults to pipeline_name unless self.data_format is set. This method
        can also be overriden
        """
        return getattr(self, 'data_format', self.pipeline_name)

    def get_files_dir(self):
        """Access method for files_dir parameter

        Defaults to pipeline_name unless self.files_dir is set. This method can
        also be overriden.
        """
        return getattr(self, 'files_dir', self.pipeline_name)

    def get_parser_name(self):
        """Access method for parser_name

        Defaults to pipeline_name unless self.parser_name is set. This method
        can also be overriden.
        """
        return getattr(self, 'parser_name', self.pipeline_name)

    def get_annotator_name(self):
        """ Access method for annotator_name

        Defaults to annotator_monarch unless specified using
        annotation.annotator_type in the configuration file.
        """
        return self.config.annotation.annotator_type

    def get_parser(self):
        dug_plugin_manager = get_plugin_manager()
        parser: Parser = get_parser(dug_plugin_manager.hook,
                                         self.get_parser_name())
        return parser

    def get_annotator(self):
        dug_plugin_manager = get_plugin_manager()
        annotator: Annotator = get_annotator(
            dug_plugin_manager.hook,
            self.get_annotator_name(),
            self.config.to_dug_conf()
        )
        return annotator

    def clear_annotation_cached(self, to_string=False, output_data_path=None):
        if not output_data_path:
            output_data_path = storage.dug_annotation_path("")
        storage.clear_dir(output_data_path)
        # Clear http session cache
        if self.config.annotation.clear_http_cache:
            self.cached_session.cache.clear()

    def init_annotator(self, max_retries=5, base_delay=1, max_delay=10):
        attempt = 0
        while attempt < max_retries:
            try:
                log.info("Initializing annotator")
                annotator = self.get_annotator()
                # Only sapbert: the batching wrapper drives
                # text_classification/annotate_classifiers, which the
                # monarch annotator does not have.
                if (self.annotation_conf.batch_identifier_lookups
                        and isinstance(annotator, AnnotateSapbert)):
                    annotator = BatchedAnnotator(annotator)
                    log.info("Batching identifier lookups")
                return annotator  # success
            except Exception as e:
                attempt += 1
                if attempt == max_retries:
                    log.error("Max retries reached when creating annotator. "
                              "Failing with error: %s", e)
                    raise
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                delay += random.uniform(0, 1)  # add jitter
                log.warning("Error occurred: %s. Retrying in %.2f seconds...",
                            e, delay)
                time.sleep(delay)

    def annotate_files(self, parsable_files, output_data_path=None):
        """
        Annotates a Data element file using a Dug parser.
        :param parsable_files: Files to parse.
        :param output_data_path: Where to write elements.txt/concepts.txt.
        :return: None.
        """
        if not output_data_path:
            output_data_path = storage.dug_annotation_path('')
        log.info("Intializing parser")
        parser = self.get_parser()
        log.info("Done intializing parser")

        pending = [f for f in parsable_files
                   if not self.annotation_is_complete(f, output_data_path)]
        skipped = len(parsable_files) - len(pending)
        if skipped:
            log.info("Resuming: %d of %d files already annotated, %d to go",
                     skipped, len(parsable_files), len(pending))

        workers = max(1, int(self.annotation_conf.annotate_workers))
        # A thread per file, not per element: files are wholly independent
        # (own parse, own crawler, own output dir) and the work is nearly all
        # http wait, so threads scale it despite the GIL. Element-level
        # concurrency would have to live in dug's Crawler.
        workers = min(workers, len(pending)) or 1
        log.info("Annotating %d files with %d worker(s)", len(pending),
                 workers)

        if workers == 1:
            for ct, parse_file in enumerate(pending):
                self.annotate_one_file(parse_file, parser, output_data_path,
                                       ct, len(pending))
            return

        with ThreadPoolExecutor(max_workers=workers,
                                thread_name_prefix='annotate') as pool:
            futures = [
                pool.submit(self.annotate_one_file, parse_file, parser,
                            output_data_path, ct, len(pending))
                for ct, parse_file in enumerate(pending)
            ]
            # surface the first failure rather than letting the pool swallow
            # it; dug's annotate_elements has no per-element error handling,
            # so a raised exception means that file produced nothing
            for future in futures:
                future.result()

    @staticmethod
    def annotation_output_paths(parse_file, output_data_path):
        "The (elements, concepts) files annotate_one_file writes for a source file"
        stem = '.'.join(os.path.basename(parse_file).split('.')[:-1])
        element_dir = os.path.join(output_data_path, stem)
        return (os.path.join(element_dir, 'elements.txt'),
                os.path.join(element_dir, 'concepts.txt'))

    @classmethod
    def annotation_is_complete(cls, parse_file, output_data_path):
        """True if this file's annotation output is already fully written.

        Both files are required: they are written in sequence, so a task
        killed between the two leaves a half-annotated directory that must be
        redone. Annotation is the most expensive step in the pipeline -- tens
        of seconds per file, weeks for a large dbGaP study -- so a retry that
        started from scratch threw away everything the previous try paid for.
        """
        return all(os.path.isfile(path) and os.path.getsize(path) > 0
                   for path in cls.annotation_output_paths(parse_file,
                                                           output_data_path))

    def annotate_one_file(self, parse_file, parser, output_data_path,
                          index=0, total=0):
        "Parse and annotate a single input file, writing pickles for it"
        session, annotator = self.thread_annotation_context()
        log.info("Annotating %s (%d of %d)", parse_file, index + 1, total)
        elements_file, concepts_file = self.annotation_output_paths(
            parse_file, output_data_path)
        crawler = Crawler(
            crawl_file=parse_file,
            parser=parser,
            annotator=annotator,
            tranqlizer='',
            tranql_queries=[],
            http_session=session
        )

        # Use the specified parser to parse the parse_file into elements.
        elements = parser(parse_file)
        log.debug("Parsed elements: %s", str(elements))

        # This inserts the list of elements into the crawler where
        # annotate_elements expects to find it. Maybe in some future version
        # of Dug this could be a parameter instead of an attribute?
        crawler.elements = elements

        # @TODO propose for Dug to make this a crawler class init param(??)
        crawler.crawlspace = os.path.dirname(elements_file)
        crawler.annotate_elements()

        # Extract out the concepts gotten out of annotation
        # Extract out the elements
        non_expanded_concepts = crawler.concepts
        # The elements object will have been modified by annotate_elements,
        # so we want to make sure to catch those modifications.
        elements = crawler.elements

        # Write pickles of objects to file. elements first, then concepts;
        # annotation_is_complete requires both, so a crash between them is
        # correctly treated as unfinished on the next try.
        log.info("Parsed and annotated: %s", parse_file)
        storage.write_object(jsonpickle.encode(elements, indent=2),
                             elements_file)
        storage.write_object(
            jsonpickle.encode(non_expanded_concepts, indent=2),
            concepts_file)
        log.info("Serialized annotated elements and concepts to %s",
                 os.path.dirname(elements_file))

    def convert_to_kgx_json(self, elements, written_nodes=None):
        """
        Given an annotated and normalized set of study variables,
        generate a KGX compliant graph given the normalized annotations.
        Write that grpah to a graph database.
        See BioLink Model for category descriptions.
        https://biolink.github.io/biolink-model/notes.html
        """
        if written_nodes is None:
            written_nodes = set()
        graph = {
            "nodes": [],
            "edges": []
        }
        edges = graph['edges']
        nodes = graph['nodes']

        for _, element in enumerate(elements):
            # DugElement means a variable (Study variable...)
            if not isinstance(element, DugElement):
                continue
            study_id = element.id
            study_link = element.action
            study_desc = element.description
            study_name = element.name or element.id


            if study_id not in written_nodes:
                nodes.append({
                    "id": study_id,
                    "category": ["biolink:Study"],
                    "name": study_name,
                    "url": study_link,
                    "description": study_desc
                })
                written_nodes.add(study_id)

            # connect the study and the variable.
            edges.append(make_edge(
                subj=element.id,
                relation_label='part of',
                relation='BFO:0000050',
                obj=study_id,
                predicate='biolink:part_of',
                predicate_label='part of'))
            edges.append(make_edge(
                subj=study_id,
                relation_label='has part',
                relation="BFO:0000051",
                obj=element.id,
                predicate='biolink:has_part',
                predicate_label='has part'))

            # a node for the variable. Should be BL compatible
            variable_node = {
                "id": element.id,
                "name": element.name,
                "category": ["biolink:StudyVariable"],
                # bulk loader parsing issue
                "description": (
                    element.description.replace("'", '`').replace('\n', ' '))
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
                # variable.concepts.items (Where variable is a DugElement obj)
                # The following logic is trying to extract types, and for the
                # aformentioned topmed tag it adds
                # `biolink:InfomrmationContentEntity`
                # Maybe a better solution could be adding types on
                # DugConcept objects
                # More specifically Biolink compatible types (?)
                #
                if identifier_object:
                    category = identifier_object.types
                elif identifier.startswith("TOPMED.TAG:"):
                    category = ["biolink:InformationContentEntity"]
                else:
                    continue
                if identifier not in written_nodes:
                    if isinstance(category, str):
                        bl_element = self.bl_toolkit.toolkit.get_element(
                            category)
                        category = [bl_element.class_uri or bl_element.slot_uri]
                    nodes.append({
                        "id": identifier,
                        "category": category,
                        "name": metadata.name
                    })
                    written_nodes.add(identifier)
                # related to edge
                edges.append(make_edge(
                    subj=element.id,
                    obj=identifier
                    ))
                # related to edge
                edges.append(make_edge(
                    subj=identifier,
                    obj=element.id))
        return graph

    def make_tagged_kg(self, elements):
        """ Make a Translator standard knowledge graph representing
        tagged study variables.
        :param variables: The variables to model.
        :param tags: The tags characterizing the variables.
        :returns: dict with nodes and edges modeling a Translator/Biolink KG.
        """
        graph = {
            "nodes": [],
            "edges": []
        }
        edges = graph['edges']
        nodes = graph['nodes']

        # Create graph elements to model tags and their
        # links to identifiers gathered by semantic tagging
        tag_map = {}
        # @TODO extract this into config or maybe dug ??
        topmed_tag_concept_type = "TOPMed Phenotype Concept"
        nodes_written = set()
        for tag in elements:
            if not (isinstance(tag, DugConcept)
                    and tag.type == topmed_tag_concept_type):
                continue
            tag_id = tag.id
            tag_map[tag_id] = tag
            nodes.append({
                "id": tag_id,
                "name": tag.name,
                "description": tag.description.replace("'", "`"),
                "category": ["biolink:InformationContentEntity"]
            })

            # Link ontology identifiers we've found for this tag via nlp.
            for identifier, metadata in tag.identifiers.items():
                if isinstance(metadata.types, str):
                    bl_element = self.bl_toolkit.toolkit.get_element(
                        metadata.types)
                    category = [bl_element.class_uri or bl_element.slot_uri]
                else:
                    category = metadata.types
                synonyms = metadata.synonyms if metadata.synonyms else []
                nodes.append({
                    "id": identifier,
                    "name": metadata.label,
                    "category": category,
                    "synonyms": synonyms
                })
                nodes_written.add(identifier)
                edges.append(make_edge(
                    subj=tag_id,
                    obj=identifier))
                edges.append(make_edge(
                    subj=identifier,
                    obj=tag_id))

        concepts_graph = self.convert_to_kgx_json(elements,
                                                  written_nodes=nodes_written)
        graph['nodes'] += concepts_graph['nodes']
        graph['edges'] += concepts_graph['edges']

        return graph

    def record_ingest_date(self, *indices):
        if self.index_obj is None:
            self.index_obj: Index = self.factory.build_indexer_obj()
        timestamp = datetime.now(timezone.utc).isoformat()
        for index in indices:
            log.info("Recording ingest date %s on %s", timestamp, index)
            self.index_obj.set_ingest_date(index, timestamp)

    def index_elements(self, elements_file):
        """Submit one elements file to ElasticSearch, routed by element type.

        Bulk, for the same reason as _index_concepts: dug's index_element
        costs 2 requests for a new document and 3 for an existing one
        (exists + get + update), which on a 127k-document index is hours of
        sequential round trips.

        Union semantics are preserved -- ids repeat across element files and
        each occurrence can carry different concepts and parents -- but the
        reads are batched: one mget per 1000 ids instead of two requests per
        document.
        """
        from elasticsearch.helpers import bulk

        if self.index_obj is None:
            self.index_obj: Index = self.factory.build_indexer_obj()

        log.info("Indexing %s...", str(elements_file))
        elements = jsonpickle.decode(storage.read_object(elements_file))
        log.info("found %d from elements files.", len(elements))

        # isinstance, not type(): pipelines may subclass these
        index_for = ((DugVariable, self.variables_index),
                     (DugStudy, self.studies_index),
                     (DugSection, self.sections_index))

        by_index = {}
        for element in elements:
            # concepts are indexed separately by _index_concepts
            if isinstance(element, DugConcept) or not element.id:
                continue
            index = next((idx for cls, idx in index_for
                          if isinstance(element, cls)), None)
            if index is None:
                continue
            # override data-type with mapping values
            if element.type.lower() in self.element_mapping:
                element.type = self.element_mapping[element.type.lower()]
            docs = by_index.setdefault(index, {})
            doc_id = element.get_id()
            doc = element.get_searchable_dict()
            # same id twice inside one file
            docs[doc_id] = (merge_searchable_docs(docs[doc_id], doc)
                            if doc_id in docs else doc)

        # fold in what earlier files (or datasets) already indexed
        for index, docs in by_index.items():
            ids = list(docs)
            for i in range(0, len(ids), 1000):
                chunk = ids[i:i + 1000]
                found = self.index_obj.es.mget(
                    index=index, body={'ids': chunk})
                for entry in found.get('docs', []):
                    if entry.get('found'):
                        doc_id = entry['_id']
                        docs[doc_id] = merge_searchable_docs(
                            entry['_source'], docs[doc_id])

        actions = [{'_op_type': 'index', '_index': index,
                    '_id': doc_id, '_source': doc}
                   for index, docs in by_index.items()
                   for doc_id, doc in docs.items()]
        indexed, errors = bulk(self.index_obj.es, actions,
                               chunk_size=1000, raise_on_error=False,
                               request_timeout=120)
        if errors:
            log.error("%d document(s) failed to index; first: %s",
                      len(errors), errors[0])
            raise PipelineException(
                f"Bulk indexing failed for {len(errors)} document(s) "
                f"from {elements_file}")
        log.info("Done indexing %s: %d document(s).", elements_file, indexed)

    def validate_indexed_element_file(self, elements_file):        
        "After submitting elements for indexing, verify that they're available"
        elements = [x for x in jsonpickle.decode(
            storage.read_object(elements_file))
                    if not isinstance(x, DugConcept)]
        # Pick ~ 10 %
        sample_size = int(len(elements) * 0.1)

        # random.choices(elements, k=sample_size)
        test_elements = elements[:sample_size]
        log.info("Picked %d from %s for validation.", len(test_elements),
                 elements_file)
        for element in test_elements:
            # Pick a concept
            concepts = [element.concepts[curie] for curie in element.concepts
                        if element.concepts[curie].name]

            if len(concepts):
                # Pick the first concept
                concept = concepts[0]
                curie = concept.id
                search_term = re.sub(r'-', ' ', concept.name)
                search_term = re.sub(r'[^a-zA-Z0-9/\.<>_:\ ]+', '', search_term)
                if len(search_term) < 3:
                    # anything less than 3 chars won't return hits
                    continue
                log.debug("Searching for Concept: %s and Search term: %s",
                          str(curie), search_term)
                all_elements_ids = self._search_elements(curie, search_term)
                present = element.id in all_elements_ids
                if not present:
                    log.error("Did not find expected variable %s in search "
                              "result.", str(element.id))
                    log.error("Concept id : %s, Search term: %s",
                              str(concept.id), search_term)
                    raise PipelineException(
                        f"Validation exception - did not find variable "
                        f"{element.id} from {str(elements_file)}"
                        f"when searching variable index with Concept ID : "
                        f"{concept.id} using Search Term : {search_term} ")
            else:
                log.info(
                    "%s has no concepts annotated. Skipping validation for it.",
                    str(element.id))

    def _search_elements(self, curie, search_term):
        "Asynchronously call a search on the curie and search term"
        if self.search_obj == None : 
            self.search_obj: Search = self.factory.build_search_obj()
            
        page_size = 10000
        offset = 0
        hits, total_items, _ = self.event_loop.run_until_complete(
            self.search_obj.search_elements(
                self.variables_index,
                concept=curie,
                query=search_term,
                size=page_size,
                offset=offset
        ))
        if total_items == 0:
            log.error(f"No search elements returned for variable search: "
                        f"{self.variables_index}.")
            log.error(f"Concept id : {curie}, Search term: {search_term}")
            raise Exception(f"Validation error - Did not find {curie} for"
                            f"Search term: {search_term}")

        while len(hits) < total_items:
            offset += page_size
            new_hits, _, _ = self.event_loop.run_until_complete(
                self.search_obj.search_elements(
                    self.variables_index,
                    concept=curie,
                    query=search_term,
                    size=page_size,
                    offset=offset
            ))
            hits += new_hits
        id_list = [e['_source']['id'] for e in hits]
        return id_list

    def crawl_concepts(self, concepts, data_set_name, output_path=None):
        """Adds tranql KG to Concepts

        Terms grabbed from KG are also added as search terms
        :param concepts:
        :param data_set_name:
        :return:
        """
        # TODO crawl dir seems to be storaing crawling info to avoid
        # re-crawling, but is that consting us much? , it was when tranql was
        # slow, but might right to consider getting rid of it.
        crawl_dir = storage.dug_crawl_path('crawl_output')
        output_file_name = os.path.join(data_set_name,
                                        'expanded_concepts.txt')
        extracted_dug_elements_file_name = os.path.join(
            data_set_name, 'extracted_graph_elements.txt')
        if not output_path:
            output_file = storage.dug_expanded_concepts_path(output_file_name)
            extracted_output_file = storage.dug_expanded_concepts_path(
                extracted_dug_elements_file_name
                )
        else:
            output_file = os.path.join(output_path, output_file_name)
            extracted_output_file = os.path.join(
                output_path, extracted_dug_elements_file_name)

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
        for concept in concepts.values():
            counter += 1
            try:
                crawler.expand_concept(concept)
                concept.set_search_terms()
                concept.set_optional_terms()
            except Exception as e:
                log.error(concept)
                raise e
            # for query in self.node_to_element_queries:
            #     log.info(query)
            #     casting_config = query['casting_config']
            #     tranql_source = query['tranql_source']
            #     dug_element_type = query['output_dug_type']
            #     extracted_dug_elements += crawler.expand_to_dug_element(
            #         concept=concept,
            #         casting_config=casting_config,
            #         dug_element_type=dug_element_type,
            #         tranql_source=tranql_source
            #     )
            concept.clean()
            percent_complete = int((counter / total) * 100)
            if percent_complete % 10 == 0:
                log.info("%d%%", percent_complete)
        log.info("Crawling %s done", data_set_name)
        storage.write_object(obj=jsonpickle.encode(concepts, indent=2),
                             path=output_file)
        log.info ("Concepts serialized to %s", output_file)
        # storage.write_object(obj=jsonpickle.encode(extracted_dug_elements,
        #                                            indent=2),
        #                      path=extracted_output_file)
        # log.info("Extracted elements serialized to %s", extracted_output_file)

    def _index_concepts(self, concepts):
        """Submit concepts and their KG answers to ElasticSearch.

        Uses the bulk API rather than dug's per-doc index_concept /
        index_kg_answer: those issue an exists check plus a write per
        document, so a 60k-concept dataset became ~150k sequential round
        trips and ran for an hour. Bulk sends 1000 docs per request.

        Dropping the exists check is deliberate. index_concept skips
        documents already present, which silently keeps stale copies; these
        tasks always rebuild the indexes wholesale, so an id-keyed upsert is
        both correct and what we want.
        """
        from elasticsearch.helpers import bulk

        if self.index_obj is None:
            self.index_obj: Index = self.factory.build_indexer_obj()

        log.info("Indexing %d concepts", len(concepts))

        def actions():
            for concept_id, concept in concepts.items():
                yield {'_op_type': 'index',
                       '_index': self.concepts_index,
                       '_id': concept_id,
                       '_source': concept.get_searchable_dict()}
                for kg_answer_id, kg_answer in concept.kg_answers.items():
                    targets = (kg_answer.get_node_names(include_curie=False)
                               + kg_answer.get_node_synonyms(
                                   include_curie=False))
                    yield {'_op_type': 'index',
                           '_index': self.kg_index,
                           '_id': f"{concept_id}_{kg_answer_id}",
                           '_source': {
                               'concept_id': concept_id,
                               'search_targets': dedupe_and_sort(targets),
                               'knowledge_graph': kg_answer.get_kg()}}

        indexed, errors = bulk(self.index_obj.es, actions(),
                               chunk_size=1000, raise_on_error=False,
                               request_timeout=120)
        if errors:
            log.error("%d document(s) failed to index; first: %s",
                      len(errors), errors[0])
            raise PipelineException(
                f"Bulk indexing failed for {len(errors)} document(s)")
        log.info("Done Indexing concepts: %d document(s)", indexed)

    def _validate_indexed_concepts(self, elements, concepts):
        """
        Validates linked concepts are searchable
        :param elements: Annotated dug elements
        :param concepts: Crawled (expanded) concepts
        :return:
        """
        # 1 . Find concepts with KG <= 10% of all concepts,
        # <= because we might have no results for some concepts from tranql
        sample_concepts = {key: value for key, value
                           in concepts.items() if value.kg_answers}
        if len(concepts) == 0:
            log.info("No Concepts found.")
            return
        log.info("Found only %d Concepts with Knowledge graph out of %d. %d%%",
                 len(sample_concepts), len(concepts),
                 (len(sample_concepts) / len(concepts)) * 100)
        # 2. pick variables that have concepts in the sample concepts set
        sample_elements = {}
        for element in elements:
            if not isinstance(element, DugVariable):
                continue
            for concept in element.concepts:
                # add elements that have kg
                if concept in sample_concepts:
                    sample_elements[concept] = sample_elements.get(
                        concept, set())
                    sample_elements[concept].add(element.id)

        # Time for some validation
        for curie in concepts:
            concept = concepts[curie]
            if not concept.kg_answers:
                continue
            if curie not in sample_elements:
                # Concept had no variable elements associated
                continue
            search_terms = []
            for key in concept.kg_answers:
                kg_object = concept.kg_answers[key]
                search_terms += kg_object.get_node_names()
                search_terms += kg_object.get_node_synonyms()
                # reduce(lambda x,y: x + y, [[node.get("name")]
                #                            + node.get("synonyms", [])
                #             for node in concept.kg_answers[
                #                 "knowledge_graph"]["nodes"]], [])
            # validation here is that for any of these nodes we should get back
            # the variable.
            # make unique
            search_terms_cap = 10
            search_terms = list(set(search_terms))[:search_terms_cap]
            log.debug("Using %d Search terms for concept %s", len(search_terms),
                      str(curie))
            for search_term in search_terms:
                # avoids elastic failure due to some reserved characters
                # 'search_phase_execution_exception',
                # 'token_mgr_error: Lexical error ...
                search_term = re.sub(r'-', ' ', search_term)
                search_term = re.sub(r'[^a-zA-Z0-9/\.<>_:\ ]+', '', search_term)

                searched_element_ids = self._search_elements(curie, search_term)

                present = bool([x for x in sample_elements[curie]
                                if x in searched_element_ids])
                if not present:
                    log.error("Did not find expected variable %s "
                              "in search result.",
                              str(curie))
                    log.error("Concept id : %s, Search term: %s",
                              str(concept.id), search_term)
                    import json
                    log.error("search_element_ids: %s", json.dumps(searched_element_ids))
                    log.error("sample_elements: %s", json.dumps({k: list(v) for k,v in sample_elements.items()}))
                    raise PipelineException(
                        f"Validation error - Did not find {curie} for"
                        f" Concept id : {concept.id}, "
                        f"Search term: {search_term}")

    def clear_index(self, index_id):
        "Delete the index specified by index_id from ES"
        # lazy init: clearing can run as the first ES touch of a task
        if self.search_obj is None:
            self.search_obj: Search = self.factory.build_search_obj()
        if self.index_obj is None:
            self.index_obj: Index = self.factory.build_indexer_obj()
        exists = self.event_loop.run_until_complete(
            self.search_obj.es.indices.exists(index=index_id))
        if exists:
            log.info("Deleting index %s", str(index_id))
            response = self.event_loop.run_until_complete(
                self.search_obj.es.indices.delete(index=index_id))
            log.info("Cleared Elastic : %s", str(response))
        log.info("Re-initializing the indicies")
        self.index_obj.init_indices()

    def clear_variables_index(self):
        "Delete the variables index from ES"
        self.clear_index(self.variables_index)

    def clear_kg_index(self):
        "Delete the KG index from ES"
        self.clear_index(self.kg_index)

    def clear_concepts_index(self):
        "Delete the concepts index from ES"
        self.clear_index(self.concepts_index)

    def clear_all_es_indexes(self, to_string=False, input_data_path=None,
                             output_data_path=None):
        """Wipe every ES index ahead of a full rebuild from the files
        remaining in lakefs. Callable as an Airflow task method."""
        for index_id in (self.variables_index, self.studies_index,
                         self.sections_index, self.concepts_index,
                         self.kg_index):
            self.clear_index(index_id)
        return self.log_stream.getvalue() if to_string else ''

    ####
    # Methods above this are directly from what used to be
    # dug_helpers.dug_utils.Dug. Methods below are consolidated from what used
    # to be dug_helpers.dug_utils.DugUtil. These are intented to be the "top
    # level" interface to Roger, which Airflow DAGs or other orchestrators can
    # call directly.

    def _fetch_s3_file(self, filename, output_dir):
        "Fetch a file from s3 to output_dir"
        log.info("Fetching %s", filename)
        output_name = filename.split('/')[-1]
        output_path = output_dir / output_name
        self.s3_utils.get(
            str(filename),
            str(output_path),
        )
        if self.unzip_source:
            log.info("Unzipping %s", str(output_path))
            with tarfile.open(str(output_path)) as tar:
                tar.extractall(path=output_dir)
        return output_path

    def _fetch_remote_file(self, filename, output_dir, current_version):
        "Fetch a file from a location using FileFetcher"
        log.info("Fetching %s", filename)
        # fetch from stars
        remote_host = self.config.annotation_base_data_uri
        fetch = FileFetcher(
            remote_host=remote_host,
            remote_dir=current_version,
            local_dir=output_dir)
        output_path = fetch(filename)
        if self.unzip_source:
            log.info("Unzipping %s", str(output_path))
            with tarfile.open(str(output_path)) as tar:
                tar.extractall(path=output_dir)
        return output_path

    def get_versioned_files(self):
        """ Fetches a dug input data files to input file directory
        """
        meta_data = storage.read_relative_object("../../metadata.yaml")
        output_dir: Path = storage.dug_input_files_path(
            self.get_files_dir())
        data_store = self.config.dug_inputs.data_source

        # clear dir
        storage.clear_dir(output_dir)
        data_sets = self.config.dug_inputs.data_sets
        log.info("dataset: %s", data_sets)
        pulled_files = []
        for data_set in data_sets:
            data_set_name, current_version = data_set.split(':')
            for item in meta_data["dug_inputs"]["versions"]:
                if (item["version"] == current_version and
                    item["name"] == data_set_name and
                    item["format"] == self.get_data_format()):
                    if data_store == "s3":
                        for filename in item["files"]["s3"]:
                            pulled_files.append(
                                self._fetch_s3_file(filename, output_dir))
                    else:
                        for filename in item["files"]["stars"]:
                            pulled_files.append(
                                self.fetch_remote_file(filename, output_dir,
                                                       current_version))
        return [str(filename) for filename in pulled_files]

    @staticmethod
    def input_file_filter(file_name):
        """Default filter for """
        return file_name.endswith('.xml')

    def get_objects(self, input_data_path=None):
        """Retrieve initial source objects for parsing

        This is a default method that will be overridden by subclasses
        frequently, it is expected.
        """
        if not input_data_path:
            input_data_path = storage.dug_input_files_path(
                self.get_files_dir())
        files = storage.get_files_recursive(
            self.input_file_filter,
            input_data_path)
        return sorted([str(f) for f in files])

    def annotate(self, to_string=False, files=None, input_data_path=None,
                 output_data_path=None):
        "Annotate files with the appropriate parsers and crawlers"
        log.debug("annotate called with files %s, input path %s, "
                  "output path $s", files, str(input_data_path),
                  str(output_data_path))
        if files is None:
            files = self.get_objects(input_data_path=input_data_path)
        self.annotate_files(parsable_files=files,
                            output_data_path=output_data_path)
        output_log = self.log_stream.getvalue() if to_string else ''
        return output_log

    def index_variables(self, to_string=False, element_object_files=None,
                        input_data_path=None, output_data_path=None):
        """Index variables from element object files for pipeline

        if element_object_files is specified, only those files are
        indexed. Otherwise, if the input_data_path is supplied, elements files
        under that path are indexed. If neither is supplied, the expanded
        concepts directory is searched for elements files that have been
        updated with KG-derived optional terms from the crawl step.
        """
        # self.clear_variables_index()
        if element_object_files is None:
            element_object_files = storage.dug_expanded_elements_objects(
                input_data_path, format='txt')
        for file_ in element_object_files:
            self.index_elements(file_)
        self.record_ingest_date(self.variables_index, self.studies_index,
                                self.sections_index)
        output_log = self.log_stream.getvalue() if to_string else ''
        return output_log

    def validate_indexed_variables(self, to_string=None,
                                   element_object_files=None,
                                   input_data_path=None,
                                   output_data_path=None):
        "Validate output from index variables task for pipeline"
        if not element_object_files:
            element_object_files = storage.dug_expanded_elements_objects(
                input_data_path, format='txt')
        for file_ in element_object_files:
            log.info("Validating %s", str(file_))
            self.validate_indexed_element_file(file_)
        output_log = self.log_stream.getvalue() if to_string else ''
        return output_log

    def validate_indexed_concepts(self, config=None, to_string=None,
                                  input_data_path=None, output_data_path=None):
        """
        Entry for validate concepts
        """
        get_data_set_name = lambda file: (
            os.path.split(os.path.dirname(file))[-1])
        expanded_concepts_files_dict = {
            get_data_set_name(file): file for file in
            storage.dug_expanded_concept_objects(data_path=input_data_path,
                                                 format='txt')
        }
        annotated_elements_files_dict = {
            get_data_set_name(file): file for file in
            storage.dug_expanded_elements_objects(data_path=input_data_path,
                                                  format='txt')
        }
        try:
            assert (len(expanded_concepts_files_dict) ==
                    len(annotated_elements_files_dict))
        except:
            log.error("Files Annotated Elements files and "
                      "expanded concepts files, should be pairs")
            if len(expanded_concepts_files_dict) > len(annotated_elements_files_dict):
                log.error("Some Annotated Elements files "
                          "(from load_and_annotate task) are missing")
            else:
                log.error("Some Expanded Concepts files (from crawl task) are missing")
            log.error(f"Annotated Datasets : {list(annotated_elements_files_dict.keys())}")
            log.error(f"Expanded Concepts Datasets: {list(expanded_concepts_files_dict.keys())}")
            exit(-1)
        for data_set_name in annotated_elements_files_dict:
            log.debug(f"Reading concepts and elements for dataset {data_set_name}")
            elements_file_path = annotated_elements_files_dict[data_set_name]
            concepts_file_path = expanded_concepts_files_dict[data_set_name]
            dug_elements = jsonpickle.decode(storage.read_object(elements_file_path))
            dug_concepts = jsonpickle.decode(storage.read_object(concepts_file_path))
            log.debug(f"Read {len(dug_elements)} elements, and {len(dug_concepts)} Concepts")
            log.info(f"Validating {data_set_name}")
            self._validate_indexed_concepts(elements=dug_elements, concepts=dug_concepts)
        output_log = self.log_stream.getvalue() if to_string else ''
        return output_log

    def make_kg_tagged(self, to_string=False, elements_files=None,
                       input_data_path=None, output_data_path=None):
        "Create tagged knowledge graphs from elements"
        if not output_data_path:
            output_data_path = storage.dug_kgx_path("")
        storage.clear_dir(output_data_path)
        log.info("Starting building KGX files")

        if not elements_files:
            elements_files = storage.dug_elements_objects(input_data_path, format='txt')
        log.info(f"found {len(elements_files)} files : {elements_files}")
        for file_ in elements_files:
            elements = jsonpickle.decode(storage.read_object(file_))
            if "topmed_" in file_:
                kg = self.make_tagged_kg(elements)
            else:
                kg = self.convert_to_kgx_json(elements)
            dug_base_file_name = file_.split(os.path.sep)[-2]
            output_file_path = os.path.join(output_data_path,
                                            dug_base_file_name + '_kgx.json')
            storage.write_object(kg, output_file_path)
            log.info("Wrote %d and %d edges, to %s", len(kg['nodes']),
                     len(kg['edges']), output_file_path)
        output_log = self.log_stream.getvalue() if to_string else ''
        return output_log

    def crawl_tranql(self, to_string=False, concept_files=None,
                     input_data_path=None, output_data_path=None):
        "Perform the tranql crawl"
        if not concept_files:
            concept_files = storage.dug_concepts_objects(
                input_data_path, format='txt')

        if output_data_path:
            crawl_dir = os.path.join(output_data_path, 'crawl_output')
            expanded_concepts_dir = os.path.join(output_data_path,
                                                 'expanded_concepts')
        else:
            crawl_dir = storage.dug_crawl_path('crawl_output')
            expanded_concepts_dir = storage.dug_expanded_concepts_path("")
        log.info("Clearing crawl output dir %s", crawl_dir)
        storage.clear_dir(crawl_dir)

        log.info("Clearing expanded concepts dir: %s", expanded_concepts_dir)
        storage.clear_dir(expanded_concepts_dir)

        log.info("Crawling Dug Concepts, found %d file(s).",
                 len(concept_files))
        for file_ in concept_files:
            objects = storage.read_object(file_)
            objects = objects or {}
            if not objects:
                log.info(f'no concepts in {file_}')
            data_set =  jsonpickle.decode(objects)
            original_variables_dataset_name = os.path.split(
                os.path.dirname(file_))[-1]
            self.crawl_concepts(concepts=data_set,
                                data_set_name=original_variables_dataset_name,
                                output_path= output_data_path)

            # After expanding concepts with KG answers, update the
            # corresponding elements' optional_terms so that KG-derived
            # search terms are present when elements are later indexed.
            # This mirrors what Crawler.crawl() does after concept expansion.
            # The updated elements are written to the expanded concepts
            # directory (alongside expanded_concepts.txt) rather than
            # mutating the annotate step's output.
            annotation_elements_file = os.path.join(
                os.path.dirname(file_), 'elements.txt')
            expanded_elements_file_name = os.path.join(
                original_variables_dataset_name, 'elements.txt')
            if not output_data_path:
                expanded_elements_file = (
                    storage.dug_expanded_concepts_path(
                        expanded_elements_file_name))
            else:
                expanded_elements_file = os.path.join(
                    output_data_path, expanded_elements_file_name)
            if os.path.exists(annotation_elements_file):
                log.info("Updating element optional terms from expanded "
                         "concepts for %s", original_variables_dataset_name)
                elements = jsonpickle.decode(
                    storage.read_object(annotation_elements_file))
                for element in elements:
                    if isinstance(element, DugConcept):
                        continue
                    # Replace each element's concept references with
                    # the expanded versions that now carry kg_answers.
                    for concept_id in list(element.concepts.keys()):
                        if concept_id in data_set:
                            element.concepts[concept_id] = data_set[
                                concept_id]
                    element.set_optional_terms()
                storage.write_object(
                    jsonpickle.encode(elements, indent=2),
                    expanded_elements_file)
                log.info("Updated elements serialized to %s",
                         expanded_elements_file)
            else:
                log.warning("Elements file not found at %s, skipping "
                            "optional terms update",
                            annotation_elements_file)

        output_log = self.log_stream.getvalue() if to_string else ''
        return output_log

    def index_concepts(self, to_string=False,
                       input_data_path=None, output_data_path=None):
        "Index concepts from expanded concept files"
        # These are concepts that have knowledge graphs  from tranql
        # clear out concepts and kg indicies from previous runs
        # self.clear_concepts_index()
        # self.clear_kg_index()
        expanded_concepts_files = storage.dug_expanded_concept_objects(
            input_data_path, format="txt")
        for file_ in expanded_concepts_files:
            concepts = jsonpickle.decode(storage.read_object(file_))
            self._index_concepts(concepts=concepts)

        if self.config.indexing.node_to_element_queries:
            log.info("*******************")

            extracted_elements_files = storage.dug_extracted_elements_objects(
                data_path=input_data_path)
            log.info(f"{extracted_elements_files}")
            for file_ in extracted_elements_files:
                log.info(f"reading file {file_}")
                self.index_elements(file_)
            self.record_ingest_date(self.variables_index, self.studies_index,
                                    self.sections_index)
        self.record_ingest_date(self.concepts_index, self.kg_index)
        output_log = self.log_stream.getvalue() if to_string else ''
        return output_log

class DDM2Pipeline(DugPipeline):
    """Base class for pipelines working on Dug Data Model v2"""

    @staticmethod
    def input_file_filter(file_name):
        """Retrieve initial source objects for parsing in .dug.json format

        This ideally removes the need for specialized get_objects methods in
        DDM2 pipelines.
        """
        return file_name.endswith('.dug.json'),
