# roger

Roger is an automated graph data curation pipeline.

It transforms Knowledge Graph eXchange (KGX) files into a graph database:

Phases include:
* **get**: Fetch KGX files from a repository.
* **merge**: Merge duplicate nodes accross multiple KGX files.
* **schema**: Infer the schema properties of nodes and edges.
* **bulk format**: Format for bulk load to Redisgraph.
* **bulk load**: Load into Redisgraph
* **validate**: Execute test queries to validate the bulk load.

## Installation
Python 3.6+
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
* Preserve all node properties present in dupliates in input files
* Ensure all nodes have exactly the same properties
* Produce an header (schema) for all nodes and edges
Some of the steps below are necessary to fit the above constaints.

### Get
Fetches KGX files. A version can be specified to select a set of files to download.
### Merge
Merges nodes duplicated across files. It aggregates properties from all nodes
### Schema
Identify and record the schema (properties) of every edge and node type.
### Bulk Create
Create bulk load CSV files conforming to the Redisgraph Bulk Loader's requirements.
### Bulk Load
Use the bulk loader to load a Redisgraph instance. This logs statistics on each type of loaded object.
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

A full run of Roger will look something like this. Times below are on a Macbook Air.

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
     8) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024825.v4.p10"
     9) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007359.v1.p10"
    10) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116233.v2.p2"
    11) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00084495.v2.p3"
    12) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254089.v1.p10"
    13) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085704.v2.p3"
    14) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119239.v2.p2"
    15) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003676.v1.p10"
    16) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210288.v1.p1"
    17) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116560.v2.p2"
    18) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210358.v1.p1"
    19) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115341.v2.p2"
    20) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115331.v2.p2"
    21) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002211.v1.p10"
    22) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006681.v1.p10"
    23) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007573.v5.p10"
    24) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085741.v2.p3"
    25) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210314.v1.p1"
    26) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210315.v1.p1"
    27) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277034.v1.p10"
    28) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003247.v1.p10"
    29) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114867.v2.p2"
    30) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003689.v1.p10"
    31) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210317.v1.p1"
    32) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085733.v2.p3"
    33) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118283.v2.p2"
    34) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000643.v1.p10"
    35) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00273915.v1.p10"
    36) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00251342.v1.p10"
    37) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123855.v1.p1"
    38) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114132.v2.p2"
    39) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056836.v2.p10"
    40) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00122648.v1.p1"
    41) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210361.v1.p1"
    42) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002678.v1.p10"
    43) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254708.v1.p10"
    44) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055286.v5.p10"
    45) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010361.v5.p10"
    46) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277342.v1.p1"
    47) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214093.v1.p1"
    48) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119708.v2.p2"
    49) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277143.v1.p10"
    50) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307749.v1.p1"
    51) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002025.v1.p10"
    52) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277299.v1.p1"
    53) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00101960.v1.p1"
    54) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210341.v1.p1"
    55) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006044.v1.p10"
    56) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000645.v1.p10"
    57) 1) "[named_thing]"
        2) "PATO:0000070"
    58) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307808.v1.p1"
    59) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086708.v2.p3"
    60) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000621.v1.p10"
    61) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277781.v1.p1"
    62) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009559.v5.p10"
    63) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086235.v2.p3"
    64) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277140.v1.p10"
    65) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001044.v1.p10"
    66) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210359.v1.p1"
    67) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210333.v1.p1"
    68) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001198.v1.p10"
    69) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000919.v1.p10"
    70) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00072660.v4.p10"
    71) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024462.v5.p10"
    72) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114116.v2.p2"
    73) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004534.v1.p10"
    74) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008540.v5.p10"
    75) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112488.v2.p2"
    76) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210336.v1.p1"
    77) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000533.v1.p10"
    78) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116253.v2.p2"
    79) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00275181.v1.p10"
    80) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116245.v2.p2"
    81) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116136.v2.p2"
    82) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00255003.v1.p10"
    83) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277142.v1.p10"
    84) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307962.v1.p1"
    85) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114875.v2.p2"
    86) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005549.v1.p10"
    87) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250916.v1.p10"
    88) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001196.v1.p10"
    89) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119718.v2.p2"
    90) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000834.v1.p10"
    91) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00110338.v1.p1"
    92) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175588.v1.p3"
    93) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086719.v2.p3"
    94) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274553.v1.p10"
    95) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000529.v1.p10"
    96) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024457.v5.p10"
    97) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177029.v1.p3"
    98) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115204.v2.p2"
    99) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00276848.v1.p10"
   100) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010001.v5.p10"
   101) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055183.v4.p10"
   102) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128372.v1.p1"
   103) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210362.v1.p1"
   104) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00251071.v1.p10"
   105) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00259053.v1.p1"
   106) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00079855.v6.p3"
   107) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116241.v2.p2"
   108) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001046.v1.p10"
   109) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007688.v5.p10"
   110) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086233.v2.p3"
   111) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277138.v1.p10"
   112) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277035.v1.p10"
   113) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006513.v1.p10"
   114) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010508.v5.p10"
   115) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00084497.v2.p3"
   116) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00255099.v1.p10"
   117) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116237.v2.p2"
   118) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008712.v5.p10"
   119) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274408.v1.p10"
   120) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083411.v1.p3"
   121) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009906.v5.p10"
   122) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277137.v1.p10"
   123) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307972.v1.p1"
   124) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005139.v1.p10"
   125) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277521.v1.p1"
   126) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024892.v1.p10"
   127) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118285.v2.p2"
   128) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00273970.v1.p10"
   129) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004547.v1.p10"
   130) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000625.v1.p10"
   131) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010123.v5.p10"
   132) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00100436.v1.p1"
   133) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007575.v5.p10"
   134) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214059.v1.p1"
   135) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210312.v1.p1"
   136) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00104021.v1.p1"
   137) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254769.v1.p10"
   138) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002209.v1.p10"
   139) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112478.v2.p2"
   140) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128371.v1.p1"
   141) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114124.v2.p2"
   142) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112492.v2.p2"
   143) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307755.v1.p1"
   144) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116229.v2.p2"
   145) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001568.v1.p10"
   146) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00108831.v1.p1"
   147) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007684.v5.p10"
   148) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177354.v2.p10"
   149) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128374.v1.p1"
   150) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087513.v1.p3"
   151) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123845.v1.p1"
   152) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00070558.v1.p10"
   153) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210291.v1.p1"
   154) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307804.v1.p1"
   155) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087043.v2.p3"
   156) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277338.v1.p1"
   157) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116265.v2.p2"
   158) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00124247.v1.p1"
   159) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116572.v2.p2"
   160) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006922.v1.p10"
   161) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00066713.v4.p10"
   162) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125877.v1.p1"
   163) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000760.v1.p10"
   164) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114134.v2.p2"
   165) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274062.v1.p10"
   166) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210364.v1.p1"
   167) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115351.v2.p2"
   168) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250995.v1.p10"
   169) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118297.v2.p2"
   170) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114130.v2.p2"
   171) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125897.v1.p1"
   172) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210286.v1.p1"
   173) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087510.v1.p3"
   174) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085736.v2.p3"
   175) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010434.v5.p10"
   176) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112490.v2.p2"
   177) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004092.v1.p10"
   178) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277295.v1.p1"
   179) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00283537.v1.p3"
   180) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006608.v1.p10"
   181) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024866.v1.p10"
   182) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007111.v1.p10"
   183) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00105433.v1.p1"
   184) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00122562.v1.p1"
   185) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115339.v2.p2"
   186) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177419.v2.p10"
   187) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00072213.v4.p10"
   188) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307800.v1.p1"
   189) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210289.v1.p1"
   190) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274723.v1.p10"
   191) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114120.v2.p2"
   192) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002676.v1.p10"
   193) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00099442.v1.p1"
   194) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002434.v1.p10"
   195) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119706.v2.p2"
   196) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177036.v1.p3"
   197) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009487.v5.p10"
   198) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00251409.v1.p10"
   199) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008631.v5.p10"
   200) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307736.v1.p1"
   201) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007042.v1.p10"
   202) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210308.v1.p1"
   203) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277527.v1.p1"
   204) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123868.v1.p1"
   205) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116556.v2.p2"
   206) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116277.v2.p2"
   207) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123002.v1.p1"
   208) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003317.v1.p10"
   209) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005856.v1.p10"
   210) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00102575.v1.p1"
   211) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083407.v1.p3"
   212) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115337.v2.p2"
   213) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116574.v2.p2"
   214) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277535.v1.p1"
   215) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118289.v2.p2"
   216) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277519.v1.p1"
   217) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277144.v1.p10"
   218) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277773.v1.p1"
   219) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277523.v1.p1"
   220) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114128.v2.p2"
   221) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00252996.v1.p1"
   222) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00159583.v4.p2"
   223) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086721.v2.p3"
   224) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003691.v1.p10"
   225) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128377.v1.p1"
   226) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001371.v1.p10"
   227) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001042.v1.p10"
   228) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210283.v1.p1"
   229) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004549.v1.p10"
   230) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00124249.v1.p1"
   231) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001810.v1.p10"
   232) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307751.v1.p1"
   233) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006251.v1.p10"
   234) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277670.v1.p1"
   235) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125892.v1.p1"
   236) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116269.v2.p2"
   237) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116566.v2.p2"
   238) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250294.v1.p10"
   239) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087030.v2.p3"
   240) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116257.v2.p2"
   241) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119710.v2.p2"
   242) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00070376.v1.p10"
   243) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055257.v5.p10"
   244) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277141.v1.p10"
   245) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00258704.v1.p1"
   246) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119712.v2.p2"
   247) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307759.v1.p1"
   248) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086716.v2.p3"
   249) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000838.v1.p10"
   250) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118281.v2.p2"
   251) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087038.v2.p3"
   252) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118295.v2.p2"
   253) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00021093.v4.p10"
   254) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00079857.v6.p3"
   255) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00070501.v1.p10"
   256) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307734.v1.p1"
   257) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277303.v1.p1"
   258) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000722.v1.p10"
   259) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210282.v1.p1"
   260) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003173.v1.p10"
   261) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086237.v2.p3"
   262) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008161.v5.p10"
   263) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001373.v1.p10"
   264) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00124251.v1.p1"
   265) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087041.v2.p3"
   266) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112495.v2.p2"
   267) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003177.v1.p10"
   268) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002029.v1.p10"
   269) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002432.v1.p10"
   270) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00283298.v1.p3"
   271) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116568.v2.p2"
   272) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005767.v1.p10"
   273) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000623.v1.p10"
   274) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307976.v1.p1"
   275) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119704.v2.p2"
   276) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112480.v2.p2"
   277) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008197.v5.p10"
   278) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000923.v1.p10"
   279) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00122564.v1.p1"
   280) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006042.v1.p10"
   281) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00072139.v4.p10"
   282) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128375.v1.p1"
   283) 1) "[named_thing]"
        2) "ZFA:0000007"
   284) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00021240.v4.p10"
   285) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024480.v5.p10"
   286) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250653.v1.p10"
   287) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003307.v1.p10"
   288) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002430.v1.p10"
   289) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274824.v1.p10"
   290) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214089.v1.p1"
   291) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277346.v1.p1"
   292) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116554.v2.p2"
   293) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024894.v1.p10"
   294) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056858.v2.p10"
   295) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119716.v2.p2"
   296) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307747.v1.p1"
   297) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009396.v5.p10"
   298) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005935.v1.p10"
   299) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114118.v2.p2"
   300) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115345.v2.p2"
   301) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119722.v2.p2"
   302) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210311.v1.p1"
   303) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125887.v1.p1"
   304) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112476.v2.p2"
   305) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085738.v2.p3"
   306) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002027.v1.p10"
   307) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277771.v1.p1"
   308) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123848.v1.p1"
   309) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277139.v1.p10"
   310) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083400.v1.p3"
   311) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086225.v2.p3"
   312) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024779.v5.p10"
   313) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175592.v1.p3"
   314) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210338.v1.p1"
   315) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115335.v2.p2"
   316) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118279.v2.p2"
   317) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307968.v1.p1"
   318) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307960.v1.p1"
   319) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00107775.v1.p1"
   320) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177022.v1.p3"
   321) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307802.v1.p1"
   322) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002948.v1.p10"
   323) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114122.v2.p2"
   324) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000762.v1.p10"
   325) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175595.v1.p3"
   326) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000641.v1.p10"
   327) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114871.v2.p2"
   328) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123871.v1.p1"
   329) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002213.v1.p10"
   330) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00205848.v1.p1"
   331) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00106795.v1.p1"
   332) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112482.v2.p2"
   333) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210335.v1.p1"
   334) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115349.v2.p2"
   335) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008759.v5.p10"
   336) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000531.v1.p10"
   337) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277785.v1.p1"
   338) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307763.v1.p1"
   339) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055288.v5.p10"
   340) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006337.v1.p10"
   341) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115343.v2.p2"
   342) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254156.v1.p10"
   343) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001570.v1.p10"
   344) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277531.v1.p1"
   345) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00104698.v1.p1"
   346) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210339.v1.p1"
   347) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00079865.v6.p3"
   348) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250562.v1.p10"
   349) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307816.v1.p1"
   350) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056856.v2.p10"
   351) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000836.v1.p10"
   352) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118291.v2.p2"
   353) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00283300.v1.p3"
   354) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277665.v1.p1"
   355) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254611.v1.p10"
   356) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277145.v1.p10"
   357) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118277.v2.p2"
   358) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175602.v1.p3"
   359) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307738.v1.p1"
   360) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123858.v1.p1"
   361) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210309.v1.p1"
   362) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007475.v1.p10"
   363) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001572.v1.p10"
   364) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00258703.v1.p1"
   365) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083404.v1.p3"
   366) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005229.v1.p10"
   367) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307964.v1.p1"
   368) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274463.v1.p10"
   369) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116570.v2.p2"
   370) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118287.v2.p2"
   371) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125882.v1.p1"
   372) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214091.v1.p1"
   373) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210285.v1.p1"
   374) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307812.v1.p1"
   375) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002674.v1.p10"
   376) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277769.v1.p1"
   377) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000921.v1.p10"
   378) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116273.v2.p2"
   379) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00226391.v1.p1"
   380) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112484.v2.p2"
   381) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116249.v2.p2"
   382) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123851.v1.p1"
   383) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008757.v5.p10"
   384) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119720.v2.p2"
   385) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087506.v1.p3"
   386) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024413.v4.p10"
   387) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007686.v5.p10"
   388) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125872.v1.p1"
   389) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114126.v2.p2"
   390) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001375.v1.p10"
   391) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112486.v2.p2"
   392) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277777.v1.p1"
   393) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006253.v1.p10"
   394) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001200.v1.p10"
   395) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055290.v5.p10"
   396) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116562.v2.p2"
   397) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115347.v2.p2"
   398) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087085.v1.p3"
   399) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123865.v1.p1"
   400) 1) "[named_thing]"
        2) "PATO:0001025"
   401) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114879.v2.p2"
   402) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119714.v2.p2"
   403) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114114.v2.p2"
   404) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116261.v2.p2"
   405) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056854.v2.p10"
   406) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119724.v2.p2"
   407) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00021148.v4.p10"
   408) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001814.v1.p10"
   409) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123861.v1.p1"
   410) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007577.v5.p10"
   411) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00275080.v1.p10"
   412) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003592.v1.p10"
   413) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118293.v2.p2"
   414) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008771.v5.p10"
   415) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115333.v2.p2"
   416) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000758.v1.p10"
   417) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001812.v1.p10"
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
