"Modules for individual datasets"

import pkgutil
from pathlib import Path
import importlib

from .base import DugPipeline, DDM2Pipeline

def get_all_subclasses(cls):
    """Recurse to get all subsubclasses, etc."""
    rval = [cls]
    for sc in cls.__subclasses__():
        rval.extend(get_all_subclasses(sc))
    return rval

def get_pipeline_classes(pipeline_names):
    """Return a list of all defined pipeline classes
    """

    base_path = Path(__file__).resolve().parent

    for (_, mod_name, _) in pkgutil.iter_modules([base_path]):
        if mod_name == 'base':
            continue

        # No need to actuall get the module symbol, once it's imported, it will
        # show up below in __subclasses__.
        importlib.import_module(f"{__name__}.{mod_name}")
    pipeline_list = []

    for subclass in get_all_subclasses(DugPipeline):
        if (getattr(subclass, 'pipeline_name') and
            getattr(subclass, 'pipeline_name') in pipeline_names):
            try:
                subclass.input_version = pipeline_names[
                    getattr(subclass, 'pipeline_name')]
            except TypeError:
                # If someone passed in the list, don't bother with the verison.
                pass
            pipeline_list.append(subclass)
    return pipeline_list
