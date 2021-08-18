import tempfile

from pathlib import Path

import pytest

from dug_helpers.dug_utils import FileFetcher, get_topmed_files, get_dbgap_files
from roger.Config import config


def test_fetch_network_file():
    filename = "README.md"
    with tempfile.TemporaryDirectory() as tmp_dir:
        fetch1 = FileFetcher(
            "https://github.com",
            "/helxplatform/roger/blob/main/",
            tmp_dir,
        )
        expected_path = Path(tmp_dir) / filename
        assert not expected_path.exists()
        fetch1(filename)
        assert expected_path.exists()

    with tempfile.TemporaryDirectory() as tmp_dir:
        fetch2 = FileFetcher(
            "https://github.com",
            Path("/helxplatform/roger/blob/main/"),
            Path(tmp_dir),
        )

        expected_path = Path(tmp_dir) / filename
        assert not expected_path.exists()
        fetch2(filename)
        assert expected_path.exists()


def test_fetcher_errors():

    filename = "DOES NOT EXIST.md"

    with tempfile.TemporaryDirectory() as tmp_dir:
        fetch = FileFetcher(
            "https://github.com",
            Path("/helxplatform/roger/blob/main/"),
            Path(tmp_dir),
        )
        with pytest.raises(RuntimeError):
            fetch(filename)


def test_get_topmed_files():
    file_names = get_topmed_files(config=config)
    for file_name in file_names:
        assert Path(file_name).exists()


def test_get_dbgap_files():
    file_names = get_dbgap_files(config=config)
    for file_name in file_names:
        assert Path(file_name).exists()