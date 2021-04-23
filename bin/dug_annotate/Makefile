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
CLI_WRAPPER=${ROGER_HOME}/cli.py

# Override Roger data dir ENV
ANNOTATE_DIR=${ROGERENV_DATA__ROOT}/dug/annotations
KGX_DIR=${ROGERENV_DATA__ROOT}/dug/kgx

RM=/bin/rm
TIME=/usr/bin/time

clean:
	$(RM) -rf ${ANNOTATE_DIR}
	$(RM) -rf ${KGX_DIR}

get_input_files:
	$(TIME) python ${CLI_WRAPPER} -gd

annotate_and_normalize:
	$(TIME) python ${CLI_WRAPPER} -l

create_kgx_files:
	$(TIME) python ${CLI_WRAPPER} -t

all: get_input_files annotate_and_normalize create_kgx_files
