# roger

Roger is an automated graph data curation pipeline.

It transforms Knowledge Graph eXchange (KGX) files into a graph database in phases:
* **get**: Fetch KGX files from a repository.
* **merge**: Merge duplicate nodes accross multiple KGX files.
* **schema**: Infer the schema properties of nodes and edges.
* **bulk create**: Format for bulk load to Redisgraph.
* **bulk load**: Load into Redisgraph
* **validate**: Execute test queries to validate the bulk load.

## Installation

Requires Python 3.7+, Docker, and Make.

```
$ pip install requirements.txt
$ bin/roger all
```

Roger can also be run via a Makefile:
```
cd bin
make clean install
```

## Design

Each phase, in general, reads and writes a set of files.
These are managed beneath a single, configurable, root data directory.
Configuration is at roger/config.yaml.

Roger can load Redisgraph
* By running the RedisgraphTransformer (currently on a fork of KGX)
* By bulk loading Redisgraph

To build a bulk load, we
* Must ensure no duplicate nodes exist
* Preserve all properties present across duplicate nodes
* Ensure all nodes of the same type have exactly the same properties
* Generate a comprehensive header (schema) for all nodes and edges
These constraints are managed in the steps below.

### Get
Fetches KGX files according to a data version selecting the set of files to use.
### Merge
Merges nodes duplicated across files aggregating properties from all nodes
### Schema
Identify and record the schema (properties) of every edge and node type.
### Bulk Create
Create bulk load CSV files conforming to the Redisgraph Bulk Loader's requirements.
### Bulk Load
Use the bulk loader to load Redisgraph logging statistics on each type of loaded object.
### Validate
Runs a configurable list of queries with timing information to quality check the generated graph database.

## Execution

### Redisgraph

Roger uses Redisgraph's new bulk loader which is available in the 'edge' tagged Docker image.

You can run the container normally or with `/bin/bash` at the end to get a shell, like this:
```
docker run -p 6379:6379 -it --rm --name redisgraph redislabs/redisgraph:edge /bin/bash
```
This lets you have a look around inside the container. To start Redis with the graph database plugin:
```
# redis-server --loadmodule /usr/lib/redis/modules/redisgraph.so
```

A clean Roger build looks like this. Times below are on a Macbook Air.

```
(rg) scox@morgancreek ~/dev/roger/bin$ make clean install validate
/bin/rm -rf /Users/scox/dev/roger/bin/../roger/data
/usr/bin/time /Users/scox/dev/roger/bin/../bin/roger kgx get --data-root /Users/scox/dev/roger/bin/../roger/data
[roger][core.py][            <module>] INFO: data root:/Users/scox/dev/roger/bin/../roger/data
[roger][core.py][                 get] DEBUG: wrote ..ger/bin/../roger/data/kgx/chembio_kgx-v0.1.json: edges:  21637 nodes:    8725 time:    2614
[roger][core.py][                 get] DEBUG: wrote ..roger/data/kgx/chemical_normalization-v0.1.json: edges: 277030 nodes:   72963 time:    8865
[roger][core.py][                 get] DEBUG: wrote ..n/../roger/data/kgx/cord19-phenotypes-v0.1.json: edges:     24 nodes:      25 time:     404
[roger][core.py][                 get] DEBUG: wrote ..x/dev/roger/bin/../roger/data/kgx/ctd-v0.1.json: edges:  48363 nodes:   24008 time:    5079
[roger][core.py][                 get] DEBUG: wrote ..dev/roger/bin/../roger/data/kgx/foodb-v0.1.json: edges:   5429 nodes:    4536 time:    1160
[roger][core.py][                 get] DEBUG: wrote ..ev/roger/bin/../roger/data/kgx/mychem-v0.1.json: edges: 123119 nodes:    5496 time:    9447
[roger][core.py][                 get] DEBUG: wrote ..ev/roger/bin/../roger/data/kgx/pharos-v0.1.json: edges: 287750 nodes:  224349 time:   30141
[roger][core.py][                 get] DEBUG: wrote ..ev/roger/bin/../roger/data/kgx/topmed-v0.1.json: edges:  63860 nodes:   15870 time:    5135

real	1m6.632s
user	0m47.908s
sys	0m3.747s
       66.65 real        47.91 user         3.75 sys
/usr/bin/time /Users/scox/dev/roger/bin/../bin/roger kgx merge --data-root /Users/scox/dev/roger/bin/../roger/data
[roger][core.py][            <module>] INFO: data root:/Users/scox/dev/roger/bin/../roger/data
[roger][core.py][               merge] INFO: merging /Users/scox/dev/roger/bin/../roger/data/kgx/chembio_kgx-v0.1.json
[roger][core.py][               merge] DEBUG: merged ..roger/data/kgx/chemical_normalization-v0.1.json load: 1058 scope:     50 merge: 32
[roger][core.py][               merge] DEBUG: merged ..n/../roger/data/kgx/cord19-phenotypes-v0.1.json load:   73 scope:     32 merge:  0
[roger][core.py][               merge] DEBUG: merged ..x/dev/roger/bin/../roger/data/kgx/ctd-v0.1.json load:  860 scope:     24 merge: 20
[roger][core.py][               merge] DEBUG: merged ..dev/roger/bin/../roger/data/kgx/foodb-v0.1.json load:  135 scope:     21 merge:  1
[roger][core.py][               merge] DEBUG: merged ..ev/roger/bin/../roger/data/kgx/mychem-v0.1.json load: 1471 scope:      9 merge:  5
[roger][core.py][               merge] DEBUG: merged ..ev/roger/bin/../roger/data/kgx/pharos-v0.1.json load: 6557 scope:    177 merge:122
[roger][core.py][               merge] DEBUG: merged ..ev/roger/bin/../roger/data/kgx/topmed-v0.1.json load:  806 scope:    153 merge:  4
[roger][core.py][               merge] INFO: /Users/scox/dev/roger/bin/../roger/data/kgx/chembio_kgx-v0.1.json rewrite: 959. total merge time: 41687
[roger][core.py][               merge] INFO: merge /Users/scox/dev/roger/bin/../roger/data/merge/chemical_normalization-v0.1.json is up to date.
[roger][core.py][               merge] INFO: merge /Users/scox/dev/roger/bin/../roger/data/merge/cord19-phenotypes-v0.1.json is up to date.
[roger][core.py][               merge] INFO: merge /Users/scox/dev/roger/bin/../roger/data/merge/ctd-v0.1.json is up to date.
[roger][core.py][               merge] INFO: merge /Users/scox/dev/roger/bin/../roger/data/merge/foodb-v0.1.json is up to date.
[roger][core.py][               merge] INFO: merge /Users/scox/dev/roger/bin/../roger/data/merge/mychem-v0.1.json is up to date.
[roger][core.py][               merge] INFO: merge /Users/scox/dev/roger/bin/../roger/data/merge/pharos-v0.1.json is up to date.
[roger][core.py][               merge] INFO: merge /Users/scox/dev/roger/bin/../roger/data/merge/topmed-v0.1.json is up to date.

real	0m46.310s
user	0m40.726s
sys	0m2.898s
       46.33 real        40.73 user         2.91 sys
/usr/bin/time /Users/scox/dev/roger/bin/../bin/roger kgx schema --data-root /Users/scox/dev/roger/bin/../roger/data
[roger][core.py][            <module>] INFO: data root:/Users/scox/dev/roger/bin/../roger/data
[roger][core.py][       is_up_to_date] DEBUG: no targets found
[roger][core.py][       create_schema] DEBUG: analyzing schema of /Users/scox/dev/roger/bin/../roger/data/kgx/chembio_kgx-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of /Users/scox/dev/roger/bin/../roger/data/kgx/chemical_normalization-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of /Users/scox/dev/roger/bin/../roger/data/kgx/cord19-phenotypes-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of /Users/scox/dev/roger/bin/../roger/data/kgx/ctd-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of /Users/scox/dev/roger/bin/../roger/data/kgx/foodb-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of /Users/scox/dev/roger/bin/../roger/data/kgx/mychem-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of /Users/scox/dev/roger/bin/../roger/data/kgx/pharos-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of /Users/scox/dev/roger/bin/../roger/data/kgx/topmed-v0.1.json.
[roger][core.py][        write_schema] INFO: writing schema: /Users/scox/dev/roger/bin/../roger/data/schema/predicate-schema.json
[roger][core.py][        write_schema] INFO: writing schema: /Users/scox/dev/roger/bin/../roger/data/schema/category-schema.json

real	0m32.128s
user	0m28.518s
sys	0m1.997s
       32.15 real        28.52 user         2.01 sys
/usr/bin/time /Users/scox/dev/roger/bin/../bin/roger bulk create --data-root /Users/scox/dev/roger/bin/../roger/data
[roger][core.py][            <module>] INFO: data root:/Users/scox/dev/roger/bin/../roger/data
[roger][core.py][       is_up_to_date] DEBUG: no targets found
[roger][core.py][              create] INFO: processing /Users/scox/dev/roger/bin/../roger/data/merge/chembio_kgx-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/chemical_substance.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/gene.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/named_thing.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/directly_interacts_with.csv
[roger][core.py][              create] INFO: processing /Users/scox/dev/roger/bin/../roger/data/merge/chemical_normalization-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/similar_to.csv
[roger][core.py][              create] INFO: processing /Users/scox/dev/roger/bin/../roger/data/merge/cord19-phenotypes-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/phenotypic_feature.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/disease.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/has_phenotype.csv
[roger][core.py][              create] INFO: processing /Users/scox/dev/roger/bin/../roger/data/merge/ctd-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/treats.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/contributes_to.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_activity_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_molecular_interaction.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_activity_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_localization_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_expression_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_response_to.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_molecular_interaction.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_degradation_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_activity_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_localization_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_localization_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_secretion_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_secretion_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_response_to.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_response_to.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_synthesis_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_transport_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_mutation_rate_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_metabolic_processing_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_metabolic_processing_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_metabolic_processing_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_degradation_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_synthesis_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_molecular_modification_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_molecular_modification_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_synthesis_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_expression_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_stability_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/molecularly_interacts_with.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_degradation_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_uptake_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_mutation_rate_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/increases_stability_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_expression_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_secretion_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_uptake_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_transport_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/decreases_transport_of.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/affects_uptake_of.csv
[roger][core.py][              create] INFO: processing /Users/scox/dev/roger/bin/../roger/data/merge/foodb-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/related_to.csv
[roger][core.py][              create] INFO: processing /Users/scox/dev/roger/bin/../roger/data/merge/mychem-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/causes_adverse_event.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/causes.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/Unmapped_Relation.csv
[roger][core.py][              create] INFO: processing /Users/scox/dev/roger/bin/../roger/data/merge/pharos-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/gene_associated_with_condition.csv
[roger][core.py][              create] INFO: processing /Users/scox/dev/roger/bin/../roger/data/merge/topmed-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/anatomical_entity.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/cell.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/cellular_component.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/molecular_activity.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/nodes/biological_process.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/association.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/has_part.csv
[roger][core.py][          write_bulk] INFO:   --creating /Users/scox/dev/roger/bin/../roger/data/bulk/edges/part_of.csv

real	0m53.671s
user	0m47.698s
sys	0m2.653s
       53.69 real        47.70 user         2.66 sys
/usr/bin/time /Users/scox/dev/roger/bin/../bin/roger bulk load --data-root /Users/scox/dev/roger/bin/../roger/data
"Graph removed, internal execution time: 5.296400 milliseconds"
deleting existing graph...
(error) ERR Invalid graph operation on empty key
running bulk load...
12 nodes created with label 'anatomical_entity'
2 nodes created with label 'biological_process'
8 nodes created with label 'cell'
2 nodes created with label 'cellular_component'
chemical_substance  [####################################]  100%          
252966 nodes created with label 'chemical_substance'
disease  [####################################]  100%          
9777 nodes created with label 'disease'
gene  [####################################]  100%          
17868 nodes created with label 'gene'
3 nodes created with label 'molecular_activity'
named_thing  [####################################]  100%          
25903 nodes created with label 'named_thing'
phenotypic_feature  [####################################]  100%
3723 nodes created with label 'phenotypic_feature'
28 relations created for type 'Unmapped_Relation'
116 relations created for type 'affects'
307 relations created for type 'affects_activity_of'
24 relations created for type 'affects_degradation_of'
259 relations created for type 'affects_expression_of'
506 relations created for type 'affects_localization_of'
337 relations created for type 'affects_metabolic_processing_of'
1804 relations created for type 'affects_response_to'
242 relations created for type 'affects_secretion_of'
42 relations created for type 'affects_synthesis_of'
91 relations created for type 'affects_transport_of'
19 relations created for type 'affects_uptake_of'
796 relations created for type 'association'
causes  [####################################]  100%          
46277 relations created for type 'causes'
causes_adverse_event  [####################################]  100%          
66461 relations created for type 'causes_adverse_event'
contributes_to  [####################################]  100%          
16172 relations created for type 'contributes_to'
decreases_activity_of  [####################################]  100%          
240317 relations created for type 'decreases_activity_of'
69 relations created for type 'decreases_degradation_of'
decreases_expression_of  [####################################]  100%
2791 relations created for type 'decreases_expression_of'
39 relations created for type 'decreases_localization_of'
24 relations created for type 'decreases_metabolic_processing_of'
513 relations created for type 'decreases_molecular_interaction'
13 relations created for type 'decreases_molecular_modification_of'
1 relations created for type 'decreases_mutation_rate_of'
904 relations created for type 'decreases_response_to'
192 relations created for type 'decreases_secretion_of'
12 relations created for type 'decreases_stability_of'
21 relations created for type 'decreases_synthesis_of'
17 relations created for type 'decreases_transport_of'
26 relations created for type 'decreases_uptake_of'
directly_interacts_with  [####################################]  100%          
30826 relations created for type 'directly_interacts_with'
gene_associated_with_condition  [####################################]  100%          
36017 relations created for type 'gene_associated_with_condition'
has_part  [####################################]  100%          
31532 relations created for type 'has_part'
24 relations created for type 'has_phenotype'
increases_activity_of  [####################################]  100%          
12061 relations created for type 'increases_activity_of'
3394 relations created for type 'increases_degradation_of'
increases_expression_of  [####################################]  100%
4178 relations created for type 'increases_expression_of'
119 relations created for type 'increases_localization_of'
467 relations created for type 'increases_metabolic_processing_of'
1495 relations created for type 'increases_molecular_interaction'
54 relations created for type 'increases_molecular_modification_of'
564 relations created for type 'increases_mutation_rate_of'
762 relations created for type 'increases_response_to'
527 relations created for type 'increases_secretion_of'
48 relations created for type 'increases_stability_of'
186 relations created for type 'increases_synthesis_of'
153 relations created for type 'increases_transport_of'
118 relations created for type 'increases_uptake_of'
49 relations created for type 'molecularly_interacts_with'
part_of  [####################################]  100%          
31532 relations created for type 'part_of'
related_to  [####################################]  100%
5429 relations created for type 'related_to'
similar_to  [####################################]  100%          
277030 relations created for type 'similar_to'
treats  [####################################]  100%          
11485 relations created for type 'treats'
Construction of graph 'test' complete: 310264 nodes created, 826470 relations created in 258.791499 seconds

real	4m19.752s
user	2m40.688s
sys	0m4.397s
      260.01 real       160.70 user         4.43 sys
/usr/bin/time /Users/scox/dev/roger/bin/../bin/roger validate --data-root /Users/scox/dev/roger/bin/../roger/data
MATCH (a) RETURN count(a)
1) 1) "count(a)"
2) 1) 1) (integer) 310264
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 8.837900 milliseconds"

real	0m0.037s
user	0m0.002s
sys	0m0.003s
MATCH (a)-[e]-(b) RETURN count(e)
1) 1) "count(e)"
2) 1) 1) (integer) 826470
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 43.389900 milliseconds"

real	0m0.109s
user	0m0.002s
sys	0m0.004s
MATCH (a { id : 'TOPMED.TAG:8' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.TAG:8' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2)   1) 1) "[named_thing]"
        2) "UBERON:0000178"
     2) 1) "[named_thing]"
        2) "CHEBI:24433"
     3) 1) "[named_thing]"
        2) "NCBIGene:5978"
     4) 1) "[named_thing]"
        2) "GO:0043336"
     5) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177026.v1.p3"
     6) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210332.v1.p1"
     7) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004107.v1.p10"
        
        << -- a few hundred lines of repetitive output elided here. -- >> 
        
   418) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004109.v1.p10"
   419) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000720.v1.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 658.065600 milliseconds"

real	0m0.710s
user	0m0.009s
sys	0m0.005s
MATCH (a { id : 'TOPMED.VAR:phv00000484.v1.p10' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.VAR:phv00000484.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
   2) 1) "[named_thing]"
      2) "TOPMED.TAG:64"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 128.350600 milliseconds"

real	0m0.148s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000487.v1.p10' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.VAR:phv00000487.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:30"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 145.227400 milliseconds"

real	0m0.165s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000496.v1.p10' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.VAR:phv00000496.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
   2) 1) "[named_thing]"
      2) "TOPMED.TAG:74"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 133.761300 milliseconds"

real	0m0.153s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000517.v1.p10' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.VAR:phv00000517.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
   2) 1) "[named_thing]"
      2) "TOPMED.TAG:26"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 125.908500 milliseconds"

real	0m0.141s
user	0m0.002s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000518.v1.p10' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.VAR:phv00000518.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
   2) 1) "[named_thing]"
      2) "TOPMED.TAG:40"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 136.909400 milliseconds"

real	0m0.155s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000528.v1.p10' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.VAR:phv00000528.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:7"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 151.945000 milliseconds"

real	0m0.173s
user	0m0.002s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000529.v1.p10' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.VAR:phv00000529.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:8"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 106.798700 milliseconds"

real	0m0.126s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000530.v1.p10' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.VAR:phv00000530.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:7"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 164.553900 milliseconds"

real	0m0.186s
user	0m0.002s
sys	0m0.003s
MATCH (a { id : 'TOPMED.VAR:phv00000531.v1.p10' })--(b) RETURN a.category, b.id
MATCH (a { id : 'TOPMED.VAR:phv00000531.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:8"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 128.471900 milliseconds"

real	0m0.144s
user	0m0.002s
sys	0m0.004s
MATCH (a)-[e]-(b) RETURN count(a), count(b)
1) 1) "count(a)"
   2) "count(b)"
2) 1) 1) (integer) 1295945
      2) (integer) 1295945
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 2112.949600 milliseconds"

real	0m2.131s
user	0m0.003s
sys	0m0.004s
MATCH (a:gene)-[e]-(b) WHERE 'chemical_substance' IN b.category RETURN count(distinct(a)), count(distinct(b))
1) 1) "count(distinct(a))"
   2) "count(distinct(b))"
2) 1) 1) (integer) 12156
      2) (integer) 196144
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 2183.923200 milliseconds"

real	0m2.200s
user	0m0.002s
sys	0m0.004s
        6.60 real         0.04 user         0.07 sys
(rg) scox@morgancreek ~/dev/roger/bin$ 
```

## Airflow

This is Roger in Airflow. This is a local run. Next steps: Kubernetes.

![image](https://user-images.githubusercontent.com/306971/97787836-e9fc6080-1b8a-11eb-9d75-141498ebe447.png)

