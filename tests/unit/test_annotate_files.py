"""Unit tests for DugPipeline.annotate_files: resume and file-level threading.

Annotation is by far the most expensive step in roger. Measured on the live
bdc-parent run: ~55s per input file, 61,597 files, i.e. 39 days -- and 96% of
that was re-annotating the same 24 dbGaP study descriptions once per
data-dict file, because dug's parsers emit the study element into every file.

These tests need dug/airflow importable (e.g. inside the roger image); they
skip cleanly elsewhere.
"""

import os
import threading
from types import SimpleNamespace

import pytest

base = pytest.importorskip("roger.pipelines.base")


class StubPipeline(base.DugPipeline):
    """A DugPipeline with the heavy __init__ replaced.

    __init__ builds a DugFactory, a BiolinkModel and tranql queries, none of
    which annotate_files touches.
    """

    pipeline_name = "stub"

    def __init__(self, workers=1):
        self.annotation_conf = SimpleNamespace(annotate_workers=workers)
        self._thread_local = threading.local()
        self.annotated = []
        self.threads = set()
        self.lock = threading.Lock()

    def thread_annotation_context(self):
        return ("session", "annotator")

    def get_parser(self):
        return lambda path: []

    def annotate_one_file(self, parse_file, parser, output_data_path,
                          index=0, total=0):
        with self.lock:
            self.annotated.append(parse_file)
            self.threads.add(threading.current_thread().name)
        elements, concepts = self.annotation_output_paths(parse_file,
                                                          output_data_path)
        for path in (elements, concepts):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as handle:
                handle.write("[]")


def source(tmp_path, name):
    path = tmp_path / name
    path.write_text("<xml/>")
    return str(path)


def test_annotates_every_file_when_nothing_is_done(tmp_path):
    files = [source(tmp_path, f"f{n}.xml") for n in range(3)]
    pipeline = StubPipeline()
    pipeline.annotate_files(files, output_data_path=str(tmp_path / "out"))
    assert sorted(pipeline.annotated) == sorted(files)


def test_skips_files_already_fully_annotated(tmp_path):
    """The resume path: outputs hard-linked in from a previous try must not be
    recomputed."""
    out = tmp_path / "out"
    files = [source(tmp_path, f"f{n}.xml") for n in range(3)]
    for name in ("f0", "f1"):
        done = out / name
        done.mkdir(parents=True)
        (done / "elements.txt").write_text("[]")
        (done / "concepts.txt").write_text("[]")

    pipeline = StubPipeline()
    pipeline.annotate_files(files, output_data_path=str(out))
    assert pipeline.annotated == [files[2]]


def test_half_written_output_is_redone(tmp_path):
    """elements.txt is written before concepts.txt, so a task killed between
    the two left a directory that looks started but is unusable."""
    out = tmp_path / "out"
    partial = out / "f0"
    partial.mkdir(parents=True)
    (partial / "elements.txt").write_text("[]")

    files = [source(tmp_path, "f0.xml")]
    pipeline = StubPipeline()
    pipeline.annotate_files(files, output_data_path=str(out))
    assert pipeline.annotated == files


def test_empty_output_file_is_redone(tmp_path):
    "A zero-byte pickle is a failed write, not finished work."
    out = tmp_path / "out"
    done = out / "f0"
    done.mkdir(parents=True)
    (done / "elements.txt").write_text("")
    (done / "concepts.txt").write_text("")

    pipeline = StubPipeline()
    pipeline.annotate_files([source(tmp_path, "f0.xml")],
                            output_data_path=str(out))
    assert len(pipeline.annotated) == 1


def test_files_are_annotated_concurrently(tmp_path):
    """Annotation is almost entirely http wait, so threads scale it despite
    the GIL. Files are independent: own parse, own crawler, own output dir."""
    files = [source(tmp_path, f"f{n}.xml") for n in range(8)]
    pipeline = StubPipeline(workers=4)
    pipeline.annotate_files(files, output_data_path=str(tmp_path / "out"))
    assert sorted(pipeline.annotated) == sorted(files)
    assert len(pipeline.threads) > 1, pipeline.threads


def test_worker_failure_is_not_swallowed(tmp_path):
    """dug's annotate_elements has no per-element error handling, so a raised
    exception means that file produced nothing; the task must fail."""

    class Failing(StubPipeline):
        def annotate_one_file(self, parse_file, *args, **kwargs):
            if parse_file.endswith("f1.xml"):
                raise RuntimeError("annotator exploded")
            return super().annotate_one_file(parse_file, *args, **kwargs)

    files = [source(tmp_path, f"f{n}.xml") for n in range(4)]
    with pytest.raises(RuntimeError, match="annotator exploded"):
        Failing(workers=4).annotate_files(
            files, output_data_path=str(tmp_path / "out"))


def test_worker_count_never_drops_below_one(tmp_path):
    "min(workers, len(pending)) is 0 for an empty list; ThreadPoolExecutor "
    "rejects max_workers=0."
    StubPipeline(workers=4).annotate_files([],
                                           output_data_path=str(tmp_path))
