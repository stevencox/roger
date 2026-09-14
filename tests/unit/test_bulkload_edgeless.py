"""Bulk loading nodes with no edges must fail loudly.

A build whose edge csvs had not been committed yet used to load nodes only
and report success, which is how the graph ended up with 3.9M nodes and zero
relationships.
"""
from unittest import mock
import pytest

from roger.core.bulkload import BulkLoad
from roger.config import config


def _bulk(tmp_path, nodes=(), edges=()):
    for kind, names in (('nodes', nodes), ('edges', edges)):
        d = tmp_path / 'knowledge_graph_build' / f'CreateBulkLoad{kind.title()}' / kind
        d.mkdir(parents=True, exist_ok=True)
        for n in names:
            (d / n).write_text('id\n1\n')
    return tmp_path


def test_nodes_without_edges_raises(tmp_path):
    _bulk(tmp_path, nodes=['biolink~Gene.csv-0-1'])
    with pytest.raises(ValueError, match='edgeless'):
        BulkLoad(config).insert(input_data_path=tmp_path)


def test_nodes_with_edges_passes_the_guard(tmp_path):
    _bulk(tmp_path, nodes=['biolink~Gene.csv-0-1'],
          edges=['biolink~treats.csv-0-1'])
    # Gets past the guard and fails later trying to reach redis, which is
    # enough: the guard is what this test is about.
    with pytest.raises(Exception) as exc:
        BulkLoad(config).insert(input_data_path=tmp_path)
    assert 'edgeless' not in str(exc.value)


def test_index_labels_are_backticked(tmp_path, monkeypatch):
    """Biolink labels contain a dot, so an unquoted one is a Cypher syntax
    error. falkordb interpolates the label straight into the index pattern
    and the loader only *prints* the failure, so this regresses silently."""
    from roger.core import bulkload as bulkload_mod

    _bulk(tmp_path, nodes=['biolink~Gene.csv-0-1'],
          edges=['biolink~treats.csv-0-1'])
    captured = {}
    monkeypatch.setattr(bulkload_mod, 'bulk_insert',
                        lambda args, **kw: captured.setdefault('args', args))
    bulk = BulkLoad(config)
    bulk.get_redisgraph = mock.MagicMock()
    bulk.biolink = mock.MagicMock()
    bulk.biolink.toolkit.get_ancestors.return_value = []
    bulk.insert(input_data_path=tmp_path)

    idx = [a for a in captured['args'] if a.startswith(('-i ', '-f '))]
    assert idx, "no index arguments were built"
    assert [a for a in idx if a.startswith('-f ')], "no fulltext index args"
    for a in idx:
        label = a.split(' ', 1)[1].rsplit(':', 1)[0]
        assert label.startswith('`') and label.endswith('`'), \
            f"label not backticked, falkordb will reject it: {a!r}"
