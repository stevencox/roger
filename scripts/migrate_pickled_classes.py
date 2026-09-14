#!/usr/bin/env python
"""Bring jsonpickle artifacts written by an older dug up to the current classes.

Dug's data classes moved into the dug_data_model library, and the module they
used to live in (dug.core.parsers._base) no longer imports.  jsonpickle does not
raise on that -- it hands back the raw dict -- so stale files index as dicts and
blow up with "'dict' object has no attribute 'id'".

    python scripts/migrate_pickled_classes.py --scan  <dir>   # what's in there
    python scripts/migrate_pickled_classes.py --fix   <dir>   # rewrite in place
    python scripts/migrate_pickled_classes.py --restamp <dir> # class paths only,
                                                             # for huge trees
    python scripts/migrate_pickled_classes.py --self-check     # no dir needed

Run inside the roger image so the current dug/dug_data_model are importable.
"""

import argparse
import importlib
import os
import json
import re
import sys
import types
from pathlib import Path

import jsonpickle
from pydantic import BaseModel

from dug.core import DugConcept, DugVariable, DugStudy, DugSection
from dug.core.annotators import DugIdentifier
from dug.core.parsers import DugElement

# Class name -> the class as it exists today. Legacy module paths resolve
# against this by name, so a class moving again needs no new mapping here.
CURRENT = {c.__name__: c for c in (
    DugElement, DugConcept, DugVariable, DugStudy, DugSection, DugIdentifier)}

PY_OBJECT = re.compile(r'"py/object":\s*"([^"]+)"')
ARTIFACTS = ('elements.txt', 'concepts.txt', 'expanded_concepts.txt')


def install_alias(module_path):
    """Stand in for a legacy module, resolving class names against CURRENT."""
    shim = types.ModuleType(module_path)
    # PEP 562: unknown attribute lookups on the module land here
    shim.__getattr__ = lambda name: CURRENT[name]
    sys.modules[module_path] = shim


def classes_in(text):
    return set(PY_OBJECT.findall(text))


def broken_modules(class_paths):
    """Of the modules these classes claim to live in, which no longer import."""
    broken = {}
    for path in class_paths:
        module_path, _, class_name = path.rpartition('.')
        if module_path in broken or module_path in sys.modules:
            continue
        try:
            importlib.import_module(module_path)
        except Exception as exc:  # noqa: BLE001 - any import failure counts
            broken[module_path] = f"{type(exc).__name__}: {exc}"
    return broken


def fill_defaults(obj, seen=None):
    """Add fields the current model has that the old state never wrote.

    jsonpickle restores via __setstate__, which assigns __dict__ wholesale, so
    fields added since the file was written are simply absent. model_construct()
    gives us the defaults without running validation over the whole graph.
    """
    if seen is None:
        seen = set()
    if id(obj) in seen:
        return
    seen.add(id(obj))

    if isinstance(obj, BaseModel):
        defaults = type(obj).model_construct().__dict__
        for key, value in defaults.items():
            if key not in obj.__dict__:
                obj.__dict__[key] = value
        for value in list(obj.__dict__.values()):
            fill_defaults(value, seen)
    elif isinstance(obj, dict):
        for value in obj.values():
            fill_defaults(value, seen)
    elif isinstance(obj, (list, tuple, set)):
        for value in obj:
            fill_defaults(value, seen)


def artifact_files(root):
    return sorted(p for p in Path(root).rglob('*.txt') if p.name in ARTIFACTS)


def field_drift(root):
    return field_drift_paths(artifact_files(root))


def field_drift_paths(paths):
    """Per class, which stored fields the current model no longer declares.

    Class names matching is not enough: a renamed field would migrate into a
    model that has no home for it, and the value would quietly vanish.
    """
    drift = {}
    for path in paths:
        obj = jsonpickle.decode(path.read_text())
        stack, seen = [obj], set()
        while stack:
            item = stack.pop()
            if id(item) in seen:
                continue
            seen.add(id(item))
            if isinstance(item, BaseModel):
                name = type(item).__name__
                stored, declared = set(item.__dict__), set(type(item).model_fields)
                counted = drift.setdefault(name, [set(), set(), 0])
                counted[0] |= stored - declared
                counted[1] |= declared - stored
                counted[2] += 1
                stack.extend(item.__dict__.values())
            elif isinstance(item, dict):
                stack.extend(item.values())
            elif isinstance(item, (list, tuple, set)):
                stack.extend(item)
    return drift


def scan(root):
    files = artifact_files(root)
    print(f"{len(files)} artifact file(s) under {root}")
    found = set()
    for path in files:
        found |= classes_in(path.read_text())
    broken = broken_modules(found)
    for cls in sorted(found):
        module_path = cls.rpartition('.')[0]
        mark = 'STALE' if module_path in broken else 'ok'
        print(f"  [{mark:5}] {cls}")
    for module_path, why in broken.items():
        print(f"\n{module_path} does not import -> {why}")
        missing = [c.rpartition('.')[2] for c in found
                   if c.startswith(module_path + '.')
                   and c.rpartition('.')[2] not in CURRENT]
        if missing:
            print(f"  !! no current class named: {sorted(set(missing))}")
        install_alias(module_path)

    if broken:
        print("\nstored fields vs current models:")
        drift = field_drift(root)
        if not drift:
            print("  !! no model objects decoded -- scan proved nothing")
        for name, (unknown, absent, count) in sorted(drift.items()):
            print(f"  {name}: {count} object(s) inspected")
            if unknown:
                print(f"    !! stored but not declared -> "
                      f"{sorted(unknown)} (renamed? migration drops these)")
            if absent:
                print(f"       new field, will take its default -> "
                      f"{sorted(absent)}")
    return broken



def dead_modules(sample_paths):
    """Which stored modules no longer import, from a sample of files.

    Only the module set comes from the sample -- never the class list. A
    sample of concepts.txt files sees DugConcept and nothing else, and a
    mapping built from that would restamp DugConcept while leaving
    DugVariable pointing at the dead module: a half-migrated file that still
    decodes to plain dicts.
    """
    dead, found = set(), set()
    for path in sample_paths:
        found |= classes_in(path.read_text())
    for cls in found:
        module_path = cls.rpartition('.')[0]
        if module_path in dead or module_path in sys.modules:
            continue
        try:
            importlib.import_module(module_path)
        except Exception:  # noqa: BLE001 - module is gone; restamp it
            dead.add(module_path)
    return dead


def restamp_text(text, dead):
    """Repoint every py/object under a dead module at its current home.

    Resolves by class name, so classes that never appeared in the sample are
    still rewritten. Returns (new_text, unmapped stored paths).
    """
    unmapped = set()

    def repoint(match):
        stored = match.group(1)
        module_path, _, name = stored.rpartition('.')
        if module_path not in dead:
            return match.group(0)
        current = CURRENT.get(name)
        if current is None:
            unmapped.add(stored)
            return match.group(0)
        return match.group(0).replace(
            stored, f"{current.__module__}.{current.__name__}")

    return PY_OBJECT.sub(repoint, text), unmapped


def restamp(root, sample=20, dry_run=False):
    """Rewrite stored class paths as text, without decoding.

    --fix decodes and re-encodes every file, which is right when fields have
    to be backfilled but costs seconds per file; at 150k artifacts that is
    days. When the stored and current models declare the same fields, the
    only thing that needs to change is the dotted path in "py/object", so a
    streaming string replace does the whole job at I/O speed.

    Field equivalence is not assumed: a sample is decoded through the shim
    and checked for drift first, and any drift aborts the run.
    """
    files = artifact_files(root)
    print(f"{len(files)} artifact file(s) under {root}")
    if not files:
        return 0

    # stratify: concepts.txt holds only concepts and elements.txt only
    # elements, so an unstratified slice can miss whole classes
    sample_paths = []
    per_kind = max(1, sample // len(ARTIFACTS))
    for kind in ARTIFACTS:
        of_kind = [f for f in files
                   if f.name == kind and f.stat().st_size > 64]
        step = max(1, len(of_kind) // per_kind)
        sample_paths += of_kind[::step][:per_kind]
    if not sample_paths:
        raise SystemExit("no non-empty artifact files to sample")

    dead = dead_modules(sample_paths)
    if not dead:
        print("nothing stale in the sample; already current")
        return 0
    print("dead module(s):", ", ".join(sorted(dead)))
    for module_path in dead:
        install_alias(module_path)
    print(f"\nchecking {len(sample_paths)} sampled file(s) for field drift")
    drift = field_drift_paths(sample_paths)
    blocked = False
    for name, (unknown, absent, count) in sorted(drift.items()):
        print(f"  {name}: {count} object(s) inspected")
        if unknown:
            blocked = True
            print(f"    !! stored but not declared -> {sorted(unknown)}")
        if absent:
            print(f"       new field, NOT backfilled by restamp -> "
                  f"{sorted(absent)}")
    if blocked:
        raise SystemExit(
            "aborting: restamp only rewrites class paths, so renamed or "
            "dropped fields would be silently lost. Use --fix for these.")
    if not drift:
        raise SystemExit("aborting: decoded no model objects from the sample")

    changed = 0
    for i, path in enumerate(files, 1):
        text = path.read_text()
        new_text, unmapped = restamp_text(text, dead)
        if unmapped:
            raise SystemExit(
                f"!! no current class for {sorted(unmapped)} in {path}; "
                f"add an explicit mapping before restamping")
        if new_text == text:
            continue
        changed += 1
        if not dry_run:
            # write-then-rename: a pod killed mid-write must not leave a
            # truncated artifact behind, and there are 150k of them
            tmp = path.with_name(path.name + '.restamp-tmp')
            tmp.write_text(new_text)
            os.replace(tmp, path)
        if changed % 5000 == 0:
            print(f"  {changed} rewritten ({i}/{len(files)} scanned)")
    print(f"{'would rewrite' if dry_run else 'rewrote'} {changed} "
          f"of {len(files)} file(s)")
    return changed


def fix(root, dry_run=False):
    files = artifact_files(root)
    for module_path in broken_modules(
            {c for p in files for c in classes_in(p.read_text())}):
        print(f"aliasing legacy module {module_path}")
        install_alias(module_path)

    changed = 0
    for path in files:
        text = path.read_text()
        obj = jsonpickle.decode(text)
        fill_defaults(obj)
        rewritten = jsonpickle.encode(obj, indent=2)
        if classes_in(rewritten) == classes_in(text):
            continue
        changed += 1
        print(f"{'would rewrite' if dry_run else 'rewrote'} {path}")
        if not dry_run:
            path.write_text(rewritten)
    print(f"{changed} of {len(files)} file(s) needed migration")
    return changed


def self_check():
    "Round-trip a synthetic legacy payload; fails loudly if the shim regresses."
    legacy = json.dumps({"UMLS:C1": {
        "py/object": "dug.core.parsers._base.DugConcept",
        "py/state": {
            "__dict__": {"id": "UMLS:C1", "name": "n", "description": "",
                         "type": "concept", "search_terms": ["s"],
                         "identifiers": {}, "kg_answers": {}},
            "__pydantic_extra__": None,
            "__pydantic_fields_set__": {"py/set": ["id", "name"]},
            "__pydantic_private__": None}}})

    assert isinstance(jsonpickle.decode(legacy)["UMLS:C1"], dict), \
        "legacy payload decoded without the shim -- test no longer meaningful"

    install_alias("dug.core.parsers._base")
    concept = jsonpickle.decode(legacy)["UMLS:C1"]
    assert isinstance(concept, DugConcept), type(concept)
    assert concept.id == "UMLS:C1"

    fill_defaults(concept)
    reencoded = jsonpickle.encode(concept)
    assert "dug.core.parsers._base" not in reencoded, reencoded[:200]
    assert isinstance(jsonpickle.decode(reencoded), DugConcept)
    print("self-check ok")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan', metavar='DIR')
    parser.add_argument('--fix', metavar='DIR')
    parser.add_argument('--restamp', metavar='DIR',
                        help='rewrite class paths as text (fast path for\n'
                             'very large trees); verifies a sample first')
    parser.add_argument('--sample', type=int, default=20,
                        help='files to decode for the drift check')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()

    if args.self_check:
        self_check()
    elif args.scan:
        scan(args.scan)
    elif args.restamp:
        restamp(args.restamp, sample=args.sample, dry_run=args.dry_run)
    elif args.fix:
        fix(args.fix, dry_run=args.dry_run)
    else:
        parser.error("one of --scan, --restamp, --fix, --self-check is required")


if __name__ == '__main__':
    main()
