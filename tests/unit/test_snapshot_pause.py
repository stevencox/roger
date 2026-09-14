"""RDB snapshots are paused for the bulk load and restored after.

bgsave forks repeatedly under bulk-load write volume and copy-on-write on a
graph this size can OOMKill the pod. Restoring matters more than pausing: a
load that leaves snapshots off is a silent durability change.
"""
from unittest import mock

import pytest

from roger.config import config
from roger.core.bulkload import BulkLoad


def _loader(save=b'300 100000'):
    bulk = BulkLoad(config)
    client = mock.MagicMock()
    client.config_get.return_value = {b'save': save}
    bulk.get_redisgraph = mock.MagicMock(return_value=mock.MagicMock(r=client))
    return bulk, client


def test_pauses_then_restores():
    bulk, client = _loader()
    with bulk.snapshots_paused():
        client.config_set.assert_called_once_with('save', '')
    assert client.config_set.call_args_list[-1] == mock.call('save', '300 100000')


def test_restores_when_the_load_raises():
    bulk, client = _loader()
    with pytest.raises(RuntimeError):
        with bulk.snapshots_paused():
            raise RuntimeError("loader blew up")
    assert client.config_set.call_args_list[-1] == mock.call('save', '300 100000')


def test_load_still_runs_if_config_is_denied():
    """A redis that refuses CONFIG must not block the load."""
    bulk, client = _loader()
    client.config_get.side_effect = Exception("NOPERM")
    ran = []
    with bulk.snapshots_paused():
        ran.append(True)
    assert ran == [True]
    client.config_set.assert_not_called()   # nothing to restore
