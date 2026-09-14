##########################################################
##
##
##     Annotate files using Dug.
##
##     Operations
##
##         annotate_and_normalize: Annotates Variable files using entity name resolution service with curies.
##
##         create_kgx_files: Creates KGX formatted knowledge graphs from annotation result set.
##
##         clean: Delete all data artifacts.
##
##
##########################################################

# Root
THIS_MAKEFILE_PATH:=$(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
THIS_DIR:=$(shell cd $(dir $(THIS_MAKEFILE_PATH));pwd)

ROGER_HOME=${THIS_DIR}/../..

# Override Roger data dir ENV
INDEXING_DIR=${ROGERENV_DATA__ROOT}/dug/expanded_concepts
CRAWL_DIR=${ROGERENV_DATA__ROOT}/dug/crawl


RM=/bin/rm
TIME=/usr/bin/time

clean:
	$(RM) -rf ${INDEXING_DIR}
	$(RM) -rf ${CRAWL_DIR}

crawl_concepts:
	$(TIME) roger -C

index_concepts: crawl_concepts
	$(TIME) roger -ic

index_variables:
	$(TIME) roger -iv

validate_indexed_concepts: index_concepts
	$(TIME) roger -vc

validate_indexed_variables: index_variables
	$(TIME) roger -vv

all: validate_indexed_concepts validate_indexed_variables


