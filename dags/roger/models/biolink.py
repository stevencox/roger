"Biolink data model for Roger"

from bmt import Toolkit
from roger.logger import get_logger

log = get_logger()

class BiolinkModel:
    "Biolink data model for Roger"
    root_type = 'biolink:NamedThing'

    def __init__(self, bl_version='v3.1.2'):
        self.bl_url = (f'https://raw.githubusercontent.com/biolink'
                       f'/biolink-model/{bl_version}/biolink-model.yaml')
        log.info("bl_url is %s", self.bl_url)
        self.toolkit = Toolkit()

    def find_biolink_leaves(self, biolink_concepts):
        """Given list of  concepts, returns leaves minus any parent concepts
        :param biolink_concepts: list of biolink concepts
        :return: leave concepts.
        """
        ancestry_set = set()
        all_concepts = set(biolink_concepts)
        unknown_elements = set()

        for x in all_concepts:
            current_element = self.toolkit.get_element(x)
            if not current_element:
                unknown_elements.add(x)
            ancestors = set(self.toolkit.get_ancestors(
                x, mixin=True, reflexive=False, formatted=True))
            ancestry_set = ancestry_set.union(ancestors)
        leaf_set = all_concepts - ancestry_set - unknown_elements
        return leaf_set

    def get_leaf_class (self, names):
        """ Return the leaf classes in the provided list of names. """
        leaves = list(self.find_biolink_leaves(names))
        return leaves[0]

    def get_label(self, class_name):
        "Return the label for the given class name"
        element = self.toolkit.get_element(class_name)
        if element:
            name = element.name
            return name
        return class_name.replace("biolink:", "").replace("_", " ")
