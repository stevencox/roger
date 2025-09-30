##########################################################
##
##
##     Make the Roger database in phases.
##  
##     Opertions
##
##         get: Fetch versioned knowledge graph exchange
##              (KGX) formatted data files.
##
##         merge: Merge nodes, consolidating duplicates
##                and preserving fields. 
##
##         schema: Identify the all properties in each
##                 predicate and node type. 
##
##         tables: Write tabular formatted data for all
##                 edges and nodes.
## 
##         install: Bulk load a Redisgraph instance.
##
##         validate: Validate database contents.
##
##         clean: Delete all data artifacts.
##
##
##########################################################

# Root of Roger
# Root
THIS_MAKEFILE_PATH:=$(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
THIS_DIR:=$(shell cd $(dir $(THIS_MAKEFILE_PATH));pwd)

ROGER_HOME=${THIS_DIR}/../..

# Path to Roger executable
CLI_WRAPPER=${ROGER_HOME}/cli.py

# Location of data
DATA_ROOT=${ROGER_HOME}/roger/data

RM=/bin/rm
TIME=/usr/bin/time

clean:
	$(RM) -rf $(DATA_ROOT)

get:
	$(TIME) python ${CLI_WRAPPER} -g

merge: get
	$(TIME) python ${CLI_WRAPPER} -m

schema: merge
	$(TIME) python ${CLI_WRAPPER} -s

tables: schema
	$(TIME) python ${CLI_WRAPPER} -b

install: tables
	$(TIME) python ${CLI_WRAPPER} -i

validate:
	$(TIME) python ${CLI_WRAPPER} -a

all: install validate