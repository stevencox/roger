"""Batched identifier lookups must match dug's serial path.

dug calls the normalizer and the name resolution service once per
identifier. Both take a list, so this collapses ~2 requests per identifier
into 2 per element. The risk is not speed, it is drifting from dug's
semantics -- greenlist handling, dropped identifiers, synonym keying -- so
these tests use dug's own handle_response parsers.
"""
from unittest import mock

import pytest

from dug.core.annotators._base import (DefaultNormalizer, DefaultSynonymFinder,
                                       DugIdentifier)
from roger.utils.batched_annotator import BatchedAnnotator

NORM_URL = ("http://norm.local:8080/get_normalized_nodes"
            "?conflate=false&description=true&curie=")
SYN_URL = "http://names.local:2433/synonyms"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Answers the two batch endpoints, recording every call."""

    def __init__(self, normalized, synonyms, fail=None):
        self.normalized, self.synonyms, self.fail = normalized, synonyms, fail
        self.calls = []

    def post(self, url, json=None, **kw):
        self.calls.append((url, json))
        if self.fail and self.fail in url:
            raise RuntimeError("service down")
        if "normalized_nodes" in url:
            return FakeResponse({c: self.normalized.get(c)
                                 for c in json["curies"]})
        return FakeResponse({c: self.synonyms.get(c, {"names": []})
                             for c in json["preferred_curies"]})


def _norm_entry(curie, label, typ="biolink:Disease"):
    return {"id": {"identifier": curie, "label": label},
            "equivalent_identifiers": [{"identifier": curie}],
            "type": [typ]}


def make_annotator(greenlist=()):
    """An inner annotator with dug's real parsers, faked network methods."""
    normalizer = object.__new__(DefaultNormalizer)
    normalizer.url = NORM_URL
    synonym_finder = object.__new__(DefaultSynonymFinder)
    synonym_finder.url = SYN_URL

    inner = mock.MagicMock()
    inner.normalizer = normalizer
    inner.synonym_finder = synonym_finder
    inner.ontology_greenlist = list(greenlist)
    inner.bagel_enabled = False
    inner.text_classification.return_value = [{"text": "x", "bl_type": "y"}]
    inner.annotate_classifiers.return_value = {
        "asthma": [DugIdentifier(id="MONDO:1", label="asthma"),
                   DugIdentifier(id="MONDO:2", label="wheeze")],
        "aspirin": [DugIdentifier(id="CHEBI:1", label="aspirin")],
    }
    return inner


def test_one_request_per_service_not_per_identifier():
    inner = make_annotator()
    session = FakeSession(
        normalized={"MONDO:1": _norm_entry("MONDO:1", "Asthma"),
                    "MONDO:2": _norm_entry("MONDO:2", "Wheeze"),
                    "CHEBI:1": _norm_entry("CHEBI:1", "Aspirin")},
        synonyms={"MONDO:1": {"names": ["asthma", "bronchial asthma"]}})

    out = BatchedAnnotator(inner)("some text", session)

    norm_calls = [c for c in session.calls if "normalized_nodes" in c[0]]
    syn_calls = [c for c in session.calls if c[0] == SYN_URL]
    assert len(norm_calls) == 1, "normalization should be a single request"
    assert len(syn_calls) == 1, "synonym lookup should be a single request"
    # 3 identifiers, one request each way
    assert sorted(norm_calls[0][1]["curies"]) == ["CHEBI:1", "MONDO:1", "MONDO:2"]
    body = norm_calls[0][1]
    assert body["conflate"] is False      # from the url
    assert body["description"] is True    # from the url
    # Not in the url, and GET/POST disagree on the default: GET conflates
    # drug/chemical curies, POST does not. Sending it explicitly is what keeps
    # CHEBI:3759 resolving to CHEBI:37941 the way dug's GET does.
    assert body["drug_chemical_conflate"] is True
    assert body["include_taxa"] is True
    assert body["individual_types"] is False

    assert [i.id for i in out] == ["MONDO:1", "MONDO:2", "CHEBI:1"]
    assert [i.label for i in out] == ["Asthma", "Wheeze", "Aspirin"]
    by_id = {i.id: i for i in out}
    assert by_id["MONDO:1"].synonyms == ["asthma", "bronchial asthma"]
    assert by_id["CHEBI:1"].synonyms == []


def test_unnormalizable_identifier_is_dropped_unless_greenlisted():
    inner = make_annotator()
    session = FakeSession(normalized={"MONDO:1": _norm_entry("MONDO:1", "Asthma")},
                          synonyms={})
    out = BatchedAnnotator(inner)("t", session)
    assert [i.id for i in out] == ["MONDO:1"], "unnormalized ids must be dropped"

    inner = make_annotator(greenlist=["CHEBI"])
    session = FakeSession(normalized={"MONDO:1": _norm_entry("MONDO:1", "Asthma")},
                          synonyms={})
    out = BatchedAnnotator(inner)("t", session)
    assert [i.id for i in out] == ["MONDO:1", "CHEBI:1"], "greenlist must survive"


@pytest.mark.parametrize("failing", ["normalized_nodes", "synonyms"])
def test_falls_back_to_dug_when_a_batch_call_fails(failing):
    inner = make_annotator()
    inner.return_value = ["serial result"]
    session = FakeSession(
        normalized={"MONDO:1": _norm_entry("MONDO:1", "Asthma"),
                    "MONDO:2": _norm_entry("MONDO:2", "W"),
                    "CHEBI:1": _norm_entry("CHEBI:1", "A")},
        synonyms={}, fail=failing)

    out = BatchedAnnotator(inner)("some text", session)

    assert out == ["serial result"]
    inner.assert_called_once_with("some text", session)


def test_delegates_unknown_attributes():
    inner = make_annotator()
    inner.score_threshold = 0.8
    assert BatchedAnnotator(inner).score_threshold == 0.8
