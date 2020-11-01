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
ROGER_HOME=$(PWD)/..

# Path to Roger executable
ROGER=${ROGER_HOME}/bin/roger

# Location of data
DATA_ROOT=${ROGER_HOME}/roger/data

RM=/bin/rm
TIME=/usr/bin/time

clean:
	$(RM) -rf $(DATA_ROOT)

get:
	$(TIME) $(ROGER) kgx get --data-root $(DATA_ROOT)

merge: get
	$(TIME) $(ROGER) kgx merge --data-root $(DATA_ROOT)

schema: merge
	$(TIME) $(ROGER) kgx schema --data-root $(DATA_ROOT)

tables: schema
	$(TIME) $(ROGER) bulk create --data-root $(DATA_ROOT)

install: tables
	$(TIME) $(ROGER) bulk load --data-root $(DATA_ROOT)

validate:
	$(TIME) $(ROGER) bulk validate --data-root $(DATA_ROOT)

