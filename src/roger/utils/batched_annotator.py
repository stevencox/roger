"""Batch the per-identifier lookups dug makes while annotating an element.

dug resolves identifiers one at a time (`AnnotateSapbert.__call__`):

    for entity, raw_identifiers in raw_identifiers_dict.items():
        for identifier in raw_identifiers:
            norm_id = self.normalizer(identifier, http_session)
            norm_id.synonyms = self.synonym_finder(norm_id.id, http_session)

Both services accept a list and answer it in about the time they take to
answer one. Measured against the deployed translator-dev services, per curie:

    n=1     normalize 10.34 ms   synonyms 25.82 ms
    n=200   normalize  0.13 ms   synonyms  0.13 ms

An element with 150 identifiers spends ~5.4 s in that loop and ~50 ms
batched. The two phases stay serial with respect to each other, because
synonyms are looked up by the *normalized* curie and so normalization has to
finish first -- but that is 2 requests instead of 300.

sapbert is deliberately left alone: the service takes a single `text` and
422s on any list form, and it is called once per classified entity rather
than once per identifier, so it is not what makes the loop expensive.
"""

from urllib.parse import urlsplit, parse_qs

from dug.core.annotators.utils.biolink_purl_util import BioLinkPURLerizer

from roger.logger import get_logger

log = get_logger()

# 200 measured fine on both services; the curve is flat well before this, so
# this is about bounding request size, not about finding an optimum.
BATCH_SIZE = 200

# The node normalizer's GET query defaults. dug builds a GET url and only
# sets some of these, so the rest are whatever GET defaults to -- and GET
# and POST do not agree (drug_chemical_conflate is true on GET, false on
# POST). Sending the full set keeps the batched POST answering exactly what
# dug's GET answers.
GET_DEFAULTS = {
    "conflate": True,
    "drug_chemical_conflate": True,
    "description": False,
    "individual_types": False,
    "include_taxa": True,
}


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


class BatchedAnnotator:
    """Wraps dug's sapbert annotator, batching normalize and synonym lookups.

    Everything except the identifier loop is delegated to the wrapped
    annotator, including response parsing -- `handle_response` on dug's own
    normalizer and synonym finder is reused so the greenlist behaviour, the
    biolink type coercion and the in-place mutation of DugIdentifier stay
    exactly as they are today.

    If either batch call fails the whole element falls back to dug's serial
    path. Classification and sapbert responses are cached by then, so the
    fallback re-runs cheaply.
    """

    def __init__(self, annotator):
        self._inner = annotator

    def __getattr__(self, name):
        # urls, thresholds, bagel config: whatever we do not override is read
        # straight off the wrapped annotator
        return getattr(self._inner, name)

    def __call__(self, text, http_session):
        inner = self._inner
        classifiers = inner.text_classification(text, http_session)
        raw = inner.annotate_classifiers(classifiers, http_session)
        if not raw:
            log.warning("Failed to annotate: %s", text)
            return []

        identifiers = [i for ids in raw.values() for i in ids]
        try:
            normalized = self._normalize_batch(identifiers, http_session)
        except Exception as e:
            log.warning("Batch normalize failed, falling back to dug's "
                        "per-identifier path: %s", e)
            return inner(text, http_session)

        # Phase 1 -- normalize. dug's own handle_response does the parsing, so
        # a curie missing from the batch response yields None exactly as a
        # failed single lookup would.
        kept = {}
        for entity, raw_identifiers in raw.items():
            for identifier in raw_identifiers:
                norm_id = inner.normalizer.handle_response(identifier,
                                                           normalized)
                if norm_id is None:
                    log.warning("Failed to normalize: %s", identifier.id)
                    if identifier.id_type not in inner.ontology_greenlist:
                        continue
                    norm_id = identifier
                norm_id.purl = BioLinkPURLerizer.get_curie_purl(norm_id.id)
                kept.setdefault(entity, []).append(norm_id)

        # Phase 2 -- synonyms, keyed by the normalized curie, which is why
        # this cannot be folded into the pass above.
        wanted = [i.id for ids in kept.values() for i in ids]
        try:
            synonyms = self._synonyms_batch(wanted, http_session)
        except Exception as e:
            log.warning("Batch synonym lookup failed, falling back to dug's "
                        "per-identifier path: %s", e)
            return inner(text, http_session)
        for ids in kept.values():
            for identifier in ids:
                identifier.synonyms = inner.synonym_finder.handle_response(
                    identifier.id, synonyms)

        if inner.bagel_enabled:
            # matches dug: bagel runs per classified entity, including ones
            # where nothing survived normalization
            for entity in raw:
                kept[entity] = inner.bagel(description_text=text,
                                           entity=entity,
                                           ids=kept.get(entity, []),
                                           http_session=http_session)

        return [i for ids in kept.values() for i in ids]

    def _normalizer_endpoint(self):
        """(url, flags) for the normalizer's POST form.

        dug stores the normalizer as a GET url ending in `curie=`. The same
        service answers POST on the same path with {"curies": [...]}, and the
        query flags move into the body.

        The flags have to be sent in full, because the service does not
        default them the same way on both verbs -- notably
        drug_chemical_conflate defaults to true on GET and false on POST.
        Omitting it silently stopped conflating drug/chemical curies:
        CHEBI:3759 came back as itself where dug's GET resolved it to
        CHEBI:37941. So start from the GET defaults, which are what dug
        gets today, and let the url override them.
        """
        split = urlsplit(self._inner.normalizer.url)
        query = parse_qs(split.query)
        flags = dict(GET_DEFAULTS)
        for name in flags:
            if name in query:
                flags[name] = str(query[name][0]).strip().lower() == "true"
        url = f"{split.scheme}://{split.netloc}{split.path}"
        return url, flags

    def _normalize_batch(self, identifiers, http_session):
        curies = list(dict.fromkeys(i.id for i in identifiers))
        url, flags = self._normalizer_endpoint()
        out = {}
        for chunk in _chunks(curies, BATCH_SIZE):
            response = http_session.post(url, json=dict(flags, curies=chunk))
            response.raise_for_status()
            out.update(response.json() or {})
        return out

    def _synonyms_batch(self, curies, http_session):
        url = self._inner.synonym_finder.url
        out = {}
        for chunk in _chunks(list(dict.fromkeys(curies)), BATCH_SIZE):
            response = http_session.post(url,
                                         json={"preferred_curies": chunk})
            response.raise_for_status()
            out.update(response.json() or {})
        return out
