# roger

Roger is an automated curation pipeline.

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

A full run of Roger will look something like this:

```
$ ../bin/roger all
[roger][core.py][                 get] DEBUG: Wrote                data/kgx/chembio_kgx-v0.1.json: edges:  21637 nodes:    8725 time:    2872
[roger][core.py][                 get] DEBUG: Wrote     data/kgx/chemical_normalization-v0.1.json: edges: 277030 nodes:   72963 time:    8910
[roger][core.py][                 get] DEBUG: Wrote          data/kgx/cord19-phenotypes-v0.1.json: edges:     24 nodes:      25 time:     400
[roger][core.py][                 get] DEBUG: Wrote                        data/kgx/ctd-v0.1.json: edges:  48363 nodes:   24008 time:    4965
[roger][core.py][                 get] DEBUG: Wrote                      data/kgx/foodb-v0.1.json: edges:   5429 nodes:    4536 time:    1105
[roger][core.py][                 get] DEBUG: Wrote                     data/kgx/mychem-v0.1.json: edges: 123119 nodes:    5496 time:    9828
[roger][core.py][                 get] DEBUG: Wrote                     data/kgx/pharos-v0.1.json: edges: 287750 nodes:  224349 time:   30431
[roger][core.py][                 get] DEBUG: Wrote                     data/kgx/topmed-v0.1.json: edges:  63860 nodes:   15870 time:    5183

real	1m7.631s
user	0m47.788s
sys	0m3.647s
[roger][core.py][               merge] INFO: merging data/kgx/chembio_kgx-v0.1.json
[roger][core.py][               merge] DEBUG: merged     data/kgx/chemical_normalization-v0.1.json load: 1050 scope:     46 merge: 28
[roger][core.py][               merge] DEBUG: merged          data/kgx/cord19-phenotypes-v0.1.json load:   71 scope:     35 merge:  0
[roger][core.py][               merge] DEBUG: merged                        data/kgx/ctd-v0.1.json load:  810 scope:     24 merge: 23
[roger][core.py][               merge] DEBUG: merged                      data/kgx/foodb-v0.1.json load:  136 scope:     20 merge:  2
[roger][core.py][               merge] DEBUG: merged                     data/kgx/mychem-v0.1.json load: 1440 scope:      8 merge:  4
[roger][core.py][               merge] DEBUG: merged                     data/kgx/pharos-v0.1.json load: 6672 scope:    178 merge:122
[roger][core.py][               merge] DEBUG: merged                     data/kgx/topmed-v0.1.json load:  816 scope:    144 merge:  3
[roger][core.py][               merge] INFO: data/kgx/chembio_kgx-v0.1.json rewrite: 1005. total merge time: 42025
[roger][core.py][               merge] INFO: merging data/kgx/chemical_normalization-v0.1.json
[roger][core.py][               merge] DEBUG: merged                data/kgx/chembio_kgx-v0.1.json load:  272 scope:     23 merge:  4
[roger][core.py][               merge] DEBUG: merged          data/kgx/cord19-phenotypes-v0.1.json load:   14 scope:     19 merge:  0
[roger][core.py][               merge] DEBUG: merged                        data/kgx/ctd-v0.1.json load:  836 scope:     61 merge: 15
[roger][core.py][               merge] DEBUG: merged                      data/kgx/foodb-v0.1.json load:  144 scope:     33 merge:  4
[roger][core.py][               merge] DEBUG: merged                     data/kgx/mychem-v0.1.json load: 1577 scope:     23 merge:  8
[roger][core.py][               merge] DEBUG: merged                     data/kgx/pharos-v0.1.json load: 6484 scope:    234 merge:159
[roger][core.py][               merge] DEBUG: merged                     data/kgx/topmed-v0.1.json load: 1511 scope:    176 merge:  3
[roger][core.py][               merge] INFO: data/kgx/chemical_normalization-v0.1.json rewrite: 5035. total merge time: 40302
[roger][core.py][               merge] INFO: merging data/kgx/cord19-phenotypes-v0.1.json
[roger][core.py][               merge] DEBUG: merged                data/kgx/chembio_kgx-v0.1.json load:  224 scope:      9 merge:  3
[roger][core.py][               merge] DEBUG: merged     data/kgx/chemical_normalization-v0.1.json load:  794 scope:     55 merge: 24
[roger][core.py][               merge] DEBUG: merged                        data/kgx/ctd-v0.1.json load:  842 scope:     50 merge:  9
[roger][core.py][               merge] DEBUG: merged                      data/kgx/foodb-v0.1.json load:  117 scope:     19 merge:  2
[roger][core.py][               merge] DEBUG: merged                     data/kgx/mychem-v0.1.json load: 1384 scope:      6 merge:  1
[roger][core.py][               merge] DEBUG: merged                     data/kgx/pharos-v0.1.json load: 7843 scope:    344 merge:171
[roger][core.py][               merge] DEBUG: merged                     data/kgx/topmed-v0.1.json load: 2181 scope:    201 merge:  6
[roger][core.py][               merge] INFO: data/kgx/cord19-phenotypes-v0.1.json rewrite: 5. total merge time: 59790
[roger][core.py][               merge] INFO: merging data/kgx/ctd-v0.1.json
[roger][core.py][               merge] DEBUG: merged                data/kgx/chembio_kgx-v0.1.json load:  466 scope:     28 merge: 12
[roger][core.py][               merge] DEBUG: merged     data/kgx/chemical_normalization-v0.1.json load:  997 scope:     72 merge: 38
[roger][core.py][               merge] DEBUG: merged          data/kgx/cord19-phenotypes-v0.1.json load:   56 scope:     34 merge:  0
[roger][core.py][               merge] DEBUG: merged                      data/kgx/foodb-v0.1.json load:   71 scope:     11 merge:  2
[roger][core.py][               merge] DEBUG: merged                     data/kgx/mychem-v0.1.json load: 1651 scope:     15 merge:  8
[roger][core.py][               merge] DEBUG: merged                     data/kgx/pharos-v0.1.json load: 7165 scope:    242 merge:150
[roger][core.py][               merge] DEBUG: merged                     data/kgx/topmed-v0.1.json load: 1497 scope:    169 merge:  3
[roger][core.py][               merge] INFO: data/kgx/ctd-v0.1.json rewrite: 2536. total merge time: 45170
[roger][core.py][               merge] INFO: merging data/kgx/foodb-v0.1.json
[roger][core.py][               merge] DEBUG: merged                data/kgx/chembio_kgx-v0.1.json load:  228 scope:     10 merge:  3
[roger][core.py][               merge] DEBUG: merged     data/kgx/chemical_normalization-v0.1.json load:  861 scope:     57 merge: 30
[roger][core.py][               merge] DEBUG: merged          data/kgx/cord19-phenotypes-v0.1.json load:   68 scope:     31 merge:  0
[roger][core.py][               merge] DEBUG: merged                        data/kgx/ctd-v0.1.json load:  673 scope:     21 merge:  9
[roger][core.py][               merge] DEBUG: merged                     data/kgx/mychem-v0.1.json load: 1485 scope:     19 merge:  2
[roger][core.py][               merge] DEBUG: merged                     data/kgx/pharos-v0.1.json load: 6855 scope:    226 merge:134
[roger][core.py][               merge] DEBUG: merged                     data/kgx/topmed-v0.1.json load: 1624 scope:    171 merge:  5
[roger][core.py][               merge] INFO: data/kgx/foodb-v0.1.json rewrite: 353. total merge time: 46469
[roger][core.py][               merge] INFO: merging data/kgx/mychem-v0.1.json
[roger][core.py][               merge] DEBUG: merged                data/kgx/chembio_kgx-v0.1.json load:  257 scope:     11 merge:  5
[roger][core.py][               merge] DEBUG: merged     data/kgx/chemical_normalization-v0.1.json load: 1420 scope:     53 merge: 30
[roger][core.py][               merge] DEBUG: merged          data/kgx/cord19-phenotypes-v0.1.json load:   66 scope:     35 merge:  0
[roger][core.py][               merge] DEBUG: merged                        data/kgx/ctd-v0.1.json load:  862 scope:     20 merge: 13
[roger][core.py][               merge] DEBUG: merged                      data/kgx/foodb-v0.1.json load:  124 scope:     24 merge:  1
[roger][core.py][               merge] DEBUG: merged                     data/kgx/pharos-v0.1.json load: 6526 scope:    180 merge:119
[roger][core.py][               merge] DEBUG: merged                     data/kgx/topmed-v0.1.json load: 1647 scope:    157 merge:  4
[roger][core.py][               merge] INFO: data/kgx/mychem-v0.1.json rewrite: 5564. total merge time: 39525
[roger][core.py][               merge] INFO: merging data/kgx/pharos-v0.1.json
[roger][core.py][               merge] DEBUG: merged                data/kgx/chembio_kgx-v0.1.json load:  981 scope:     86 merge: 20
[roger][core.py][               merge] DEBUG: merged     data/kgx/chemical_normalization-v0.1.json load:  833 scope:    160 merge: 82
[roger][core.py][               merge] DEBUG: merged          data/kgx/cord19-phenotypes-v0.1.json load:   93 scope:    103 merge:  0
[roger][core.py][               merge] DEBUG: merged                        data/kgx/ctd-v0.1.json load:  537 scope:    112 merge: 45
[roger][core.py][               merge] DEBUG: merged                      data/kgx/foodb-v0.1.json load:  877 scope:    123 merge:  2
[roger][core.py][               merge] DEBUG: merged                     data/kgx/mychem-v0.1.json load: 1094 scope:     81 merge: 13
[roger][core.py][               merge] DEBUG: merged                     data/kgx/topmed-v0.1.json load: 1326 scope:     90 merge:  4
[roger][core.py][               merge] INFO: data/kgx/pharos-v0.1.json rewrite: 25609. total merge time: 22321
[roger][core.py][               merge] INFO: merging data/kgx/topmed-v0.1.json
[roger][core.py][               merge] DEBUG: merged                data/kgx/chembio_kgx-v0.1.json load:  433 scope:     20 merge:  4
[roger][core.py][               merge] DEBUG: merged     data/kgx/chemical_normalization-v0.1.json load: 1557 scope:     64 merge: 28
[roger][core.py][               merge] DEBUG: merged          data/kgx/cord19-phenotypes-v0.1.json load:   60 scope:     35 merge:  0
[roger][core.py][               merge] DEBUG: merged                        data/kgx/ctd-v0.1.json load:  824 scope:     25 merge:  8
[roger][core.py][               merge] DEBUG: merged                      data/kgx/foodb-v0.1.json load:  209 scope:     39 merge:  2
[roger][core.py][               merge] DEBUG: merged                     data/kgx/mychem-v0.1.json load: 1527 scope:      9 merge:  2
[roger][core.py][               merge] DEBUG: merged                     data/kgx/pharos-v0.1.json load: 6308 scope:    189 merge:107
[roger][core.py][               merge] INFO: data/kgx/topmed-v0.1.json rewrite: 2240. total merge time: 43929

real	6m36.105s
user	5m38.324s
sys	0m21.419s
[roger][core.py][       create_schema] DEBUG: analyzing schema of data/kgx/chembio_kgx-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of data/kgx/chemical_normalization-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of data/kgx/cord19-phenotypes-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of data/kgx/ctd-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of data/kgx/foodb-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of data/kgx/mychem-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of data/kgx/pharos-v0.1.json.
[roger][core.py][       create_schema] DEBUG: analyzing schema of data/kgx/topmed-v0.1.json.
[roger][core.py][        write_schema] INFO: writing schema: data/schema/predicate-schema.json
[roger][core.py][        write_schema] INFO: writing schema: data/schema/category-schema.json

real	0m34.596s
user	0m29.899s
sys	0m2.029s
[roger][core.py][              create] INFO: processing data/merge/chembio_kgx-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/chemical_substance.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/gene.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/named_thing.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/directly_interacts_with.csv
[roger][core.py][              create] INFO: processing data/merge/chembio_merge-v0.1.json
[roger][core.py][              create] INFO: processing data/merge/chemical_normalization-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/similar_to.csv
[roger][core.py][              create] INFO: processing data/merge/cord19-phenotypes-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/disease.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/phenotypic_feature.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/has_phenotype.csv
[roger][core.py][              create] INFO: processing data/merge/ctd-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/treats.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/contributes_to.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_activity_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_molecular_interaction.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_activity_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_localization_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_expression_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_response_to.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_molecular_interaction.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_degradation_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_activity_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_localization_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_localization_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_secretion_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_secretion_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_response_to.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_response_to.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_synthesis_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_transport_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_mutation_rate_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_metabolic_processing_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_metabolic_processing_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_metabolic_processing_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_degradation_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_synthesis_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_molecular_modification_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_molecular_modification_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_synthesis_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_expression_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_stability_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/molecularly_interacts_with.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_degradation_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_uptake_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_mutation_rate_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/increases_stability_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_expression_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_secretion_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_uptake_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_transport_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/decreases_transport_of.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/affects_uptake_of.csv
[roger][core.py][              create] INFO: processing data/merge/foodb-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/related_to.csv
[roger][core.py][              create] INFO: processing data/merge/mychem-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/causes_adverse_event.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/causes.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/Unmapped_Relation.csv
[roger][core.py][              create] INFO: processing data/merge/pharos-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/gene_associated_with_condition.csv
[roger][core.py][              create] INFO: processing data/merge/topmed-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/anatomical_entity.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/molecular_activity.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/cellular_component.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/cell.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/biological_process.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/association.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/has_part.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/part_of.csv

real	0m56.816s
user	0m51.642s
sys	0m2.416s
"Graph removed, internal execution time: 0.851200 milliseconds"
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
increases_degradation_of  [####################################]  100%
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
Construction of graph 'test' complete: 310264 nodes created, 826470 relations created in 190.396588 seconds

real	3m11.289s
user	2m16.249s
sys	0m2.753s
1) 1) "count(a)"
2) 1) 1) (integer) 310264
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 0.378800 milliseconds"

real	0m0.071s
user	0m0.003s
sys	0m0.006s
1) 1) "count(e)"
2) 1) 1) (integer) 826470
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 0.462800 milliseconds"

real	0m0.029s
user	0m0.003s
sys	0m0.004s
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
        2) "PATO:0000070"
     6) 1) "[named_thing]"
        2) "ZFA:0000007"
     7) 1) "[named_thing]"
        2) "PATO:0001025"
     8) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128375.v1.p1"
     9) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210289.v1.p1"
    10) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210315.v1.p1"
    11) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210359.v1.p1"
    12) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210336.v1.p1"
    13) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210312.v1.p1"
    14) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210286.v1.p1"
    15) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210283.v1.p1"
    16) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210309.v1.p1"
    17) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210362.v1.p1"
    18) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210339.v1.p1"
    19) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210333.v1.p1"
    20) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128372.v1.p1"
    21) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00226391.v1.p1"
    22) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055290.v5.p10"
    23) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116574.v2.p2"
    24) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007575.v5.p10"
    25) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001572.v1.p10"
    26) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307802.v1.p1"
    27) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008712.v5.p10"
    28) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006608.v1.p10"
    29) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114118.v2.p2"
    30) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307960.v1.p1"
    31) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307736.v1.p1"
    32) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250653.v1.p10"
    33) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210341.v1.p1"
    34) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024462.v5.p10"
    35) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123845.v1.p1"
    36) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118287.v2.p2"
    37) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123848.v1.p1"
    38) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008540.v5.p10"
    39) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009906.v5.p10"
    40) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118279.v2.p2"
    41) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114875.v2.p2"
    42) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056836.v2.p10"
    43) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128374.v1.p1"
    44) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274062.v1.p10"
    45) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116269.v2.p2"
    46) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00259053.v1.p1"
    47) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003247.v1.p10"
    48) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119720.v2.p2"
    49) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006253.v1.p10"
    50) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114871.v2.p2"
    51) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250294.v1.p10"
    52) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010001.v5.p10"
    53) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123851.v1.p1"
    54) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00124247.v1.p1"
    55) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000762.v1.p10"
    56) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00258703.v1.p1"
    57) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254611.v1.p10"
    58) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087030.v2.p3"
    59) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112480.v2.p2"
    60) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00021240.v4.p10"
    61) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116261.v2.p2"
    62) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125877.v1.p1"
    63) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116570.v2.p2"
    64) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00021148.v4.p10"
    65) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087506.v1.p3"
    66) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114134.v2.p2"
    67) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177029.v1.p3"
    68) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002678.v1.p10"
    69) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001568.v1.p10"
    70) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119710.v2.p2"
    71) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003173.v1.p10"
    72) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277670.v1.p1"
    73) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274824.v1.p10"
    74) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00205848.v1.p1"
    75) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125892.v1.p1"
    76) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125887.v1.p1"
    77) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056858.v2.p10"
    78) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009559.v5.p10"
    79) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001198.v1.p10"
    80) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116241.v2.p2"
    81) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277777.v1.p1"
    82) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277521.v1.p1"
    83) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114120.v2.p2"
    84) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114128.v2.p2"
    85) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112482.v2.p2"
    86) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210364.v1.p1"
    87) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00283537.v1.p3"
    88) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307962.v1.p1"
    89) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250562.v1.p10"
    90) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083411.v1.p3"
    91) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00283300.v1.p3"
    92) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116554.v2.p2"
    93) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210361.v1.p1"
    94) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001570.v1.p10"
    95) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125897.v1.p1"
    96) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00079855.v6.p3"
    97) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086708.v2.p3"
    98) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307755.v1.p1"
    99) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277299.v1.p1"
   100) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024866.v1.p10"
   101) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116253.v2.p2"
   102) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009396.v5.p10"
   103) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123871.v1.p1"
   104) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005935.v1.p10"
   105) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277034.v1.p10"
   106) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00084495.v2.p3"
   107) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00105433.v1.p1"
   108) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118281.v2.p2"
   109) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210282.v1.p1"
   110) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00255099.v1.p10"
   111) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210332.v1.p1"
   112) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006681.v1.p10"
   113) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277531.v1.p1"
   114) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003689.v1.p10"
   115) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210358.v1.p1"
   116) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087038.v2.p3"
   117) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00070376.v1.p10"
   118) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118285.v2.p2"
   119) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086721.v2.p3"
   120) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00021093.v4.p10"
   121) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006337.v1.p10"
   122) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210335.v1.p1"
   123) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307976.v1.p1"
   124) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307808.v1.p1"
   125) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000834.v1.p10"
   126) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024779.v5.p10"
   127) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277346.v1.p1"
   128) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115347.v2.p2"
   129) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002213.v1.p10"
   130) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024892.v1.p10"
   131) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00122564.v1.p1"
   132) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115351.v2.p2"
   133) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112495.v2.p2"
   134) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008631.v5.p10"
   135) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000531.v1.p10"
   136) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277773.v1.p1"
   137) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001371.v1.p10"
   138) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003177.v1.p10"
   139) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307751.v1.p1"
   140) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002209.v1.p10"
   141) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115343.v2.p2"
   142) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119708.v2.p2"
   143) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00104021.v1.p1"
   144) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307749.v1.p1"
   145) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024413.v4.p10"
   146) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123855.v1.p1"
   147) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00251071.v1.p10"
   148) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118277.v2.p2"
   149) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175592.v1.p3"
   150) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250916.v1.p10"
   151) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002211.v1.p10"
   152) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006513.v1.p10"
   153) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00108831.v1.p1"
   154) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277781.v1.p1"
   155) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007577.v5.p10"
   156) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00251342.v1.p10"
   157) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116233.v2.p2"
   158) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006251.v1.p10"
   159) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115349.v2.p2"
   160) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085736.v2.p3"
   161) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00283298.v1.p3"
   162) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00079857.v6.p3"
   163) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119239.v2.p2"
   164) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004107.v1.p10"
   165) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112484.v2.p2"
   166) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00099442.v1.p1"
   167) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112478.v2.p2"
   168) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112486.v2.p2"
   169) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112476.v2.p2"
   170) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00110338.v1.p1"
   171) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115335.v2.p2"
   172) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114130.v2.p2"
   173) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00070558.v1.p10"
   174) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118293.v2.p2"
   175) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000923.v1.p10"
   176) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307972.v1.p1"
   177) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277295.v1.p1"
   178) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214089.v1.p1"
   179) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024825.v4.p10"
   180) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024894.v1.p10"
   181) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002676.v1.p10"
   182) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177026.v1.p3"
   183) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086237.v2.p3"
   184) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274553.v1.p10"
   185) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00159583.v4.p2"
   186) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086719.v2.p3"
   187) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123861.v1.p1"
   188) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002432.v1.p10"
   189) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115204.v2.p2"
   190) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006044.v1.p10"
   191) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00102575.v1.p1"
   192) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001812.v1.p10"
   193) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005549.v1.p10"
   194) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00276848.v1.p10"
   195) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00255003.v1.p10"
   196) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116560.v2.p2"
   197) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123002.v1.p1"
   198) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001046.v1.p10"
   199) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307747.v1.p1"
   200) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114114.v2.p2"
   201) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004092.v1.p10"
   202) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000720.v1.p10"
   203) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118283.v2.p2"
   204) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010508.v5.p10"
   205) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00072660.v4.p10"
   206) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000645.v1.p10"
   207) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056854.v2.p10"
   208) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115333.v2.p2"
   209) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005139.v1.p10"
   210) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006042.v1.p10"
   211) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115339.v2.p2"
   212) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001196.v1.p10"
   213) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007359.v1.p10"
   214) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210338.v1.p1"
   215) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116265.v2.p2"
   216) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116257.v2.p2"
   217) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00273970.v1.p10"
   218) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277527.v1.p1"
   219) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214093.v1.p1"
   220) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024480.v5.p10"
   221) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087041.v2.p3"
   222) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114126.v2.p2"
   223) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116562.v2.p2"
   224) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000836.v1.p10"
   225) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00251409.v1.p10"
   226) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274723.v1.p10"
   227) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001810.v1.p10"
   228) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116136.v2.p2"
   229) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128371.v1.p1"
   230) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002029.v1.p10"
   231) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087043.v2.p3"
   232) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085741.v2.p3"
   233) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274408.v1.p10"
   234) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277144.v1.p10"
   235) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114116.v2.p2"
   236) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112492.v2.p2"
   237) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002027.v1.p10"
   238) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003691.v1.p10"
   239) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007686.v5.p10"
   240) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000758.v1.p10"
   241) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003592.v1.p10"
   242) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210288.v1.p1"
   243) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00104698.v1.p1"
   244) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001375.v1.p10"
   245) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00084497.v2.p3"
   246) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007111.v1.p10"
   247) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004549.v1.p10"
   248) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115337.v2.p2"
   249) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004109.v1.p10"
   250) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307738.v1.p1"
   251) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001814.v1.p10"
   252) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00122648.v1.p1"
   253) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003676.v1.p10"
   254) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277141.v1.p10"
   255) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004547.v1.p10"
   256) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007573.v5.p10"
   257) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010434.v5.p10"
   258) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307759.v1.p1"
   259) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000529.v1.p10"
   260) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123858.v1.p1"
   261) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177419.v2.p10"
   262) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002674.v1.p10"
   263) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254769.v1.p10"
   264) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085733.v2.p3"
   265) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307964.v1.p1"
   266) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119722.v2.p2"
   267) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055183.v4.p10"
   268) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000760.v1.p10"
   269) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116237.v2.p2"
   270) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277140.v1.p10"
   271) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175602.v1.p3"
   272) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114879.v2.p2"
   273) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118291.v2.p2"
   274) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002434.v1.p10"
   275) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307763.v1.p1"
   276) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112488.v2.p2"
   277) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00275080.v1.p10"
   278) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003317.v1.p10"
   279) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116556.v2.p2"
   280) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123865.v1.p1"
   281) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085704.v2.p3"
   282) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119724.v2.p2"
   283) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00258704.v1.p1"
   284) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00122562.v1.p1"
   285) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128377.v1.p1"
   286) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000623.v1.p10"
   287) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00101960.v1.p1"
   288) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307812.v1.p1"
   289) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175595.v1.p3"
   290) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00124249.v1.p1"
   291) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307734.v1.p1"
   292) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056856.v2.p10"
   293) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055288.v5.p10"
   294) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307816.v1.p1"
   295) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123868.v1.p1"
   296) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119706.v2.p2"
   297) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210291.v1.p1"
   298) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277142.v1.p10"
   299) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114122.v2.p2"
   300) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277535.v1.p1"
   301) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277143.v1.p10"
   302) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001044.v1.p10"
   303) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214059.v1.p1"
   304) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00275181.v1.p10"
   305) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119718.v2.p2"
   306) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002430.v1.p10"
   307) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177036.v1.p3"
   308) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119714.v2.p2"
   309) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086225.v2.p3"
   310) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114132.v2.p2"
   311) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115345.v2.p2"
   312) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001042.v1.p10"
   313) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007684.v5.p10"
   314) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005767.v1.p10"
   315) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00273915.v1.p10"
   316) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210308.v1.p1"
   317) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274463.v1.p10"
   318) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002025.v1.p10"
   319) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086233.v2.p3"
   320) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008757.v5.p10"
   321) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007042.v1.p10"
   322) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00079865.v6.p3"
   323) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277769.v1.p1"
   324) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010361.v5.p10"
   325) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005856.v1.p10"
   326) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00072213.v4.p10"
   327) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214091.v1.p1"
   328) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116566.v2.p2"
   329) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116249.v2.p2"
   330) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115341.v2.p2"
   331) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000838.v1.p10"
   332) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087510.v1.p3"
   333) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003307.v1.p10"
   334) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277338.v1.p1"
   335) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000643.v1.p10"
   336) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007475.v1.p10"
   337) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055257.v5.p10"
   338) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006922.v1.p10"
   339) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116568.v2.p2"
   340) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083400.v1.p3"
   341) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112490.v2.p2"
   342) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00072139.v4.p10"
   343) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00070501.v1.p10"
   344) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087085.v1.p3"
   345) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125882.v1.p1"
   346) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277138.v1.p10"
   347) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001200.v1.p10"
   348) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010123.v5.p10"
   349) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277785.v1.p1"
   350) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118289.v2.p2"
   351) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086235.v2.p3"
   352) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277139.v1.p10"
   353) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277137.v1.p10"
   354) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118295.v2.p2"
   355) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119704.v2.p2"
   356) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000621.v1.p10"
   357) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115331.v2.p2"
   358) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000625.v1.p10"
   359) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116277.v2.p2"
   360) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210314.v1.p1"
   361) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210285.v1.p1"
   362) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116245.v2.p2"
   363) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116229.v2.p2"
   364) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277771.v1.p1"
   365) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277342.v1.p1"
   366) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085738.v2.p3"
   367) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277035.v1.p10"
   368) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118297.v2.p2"
   369) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000533.v1.p10"
   370) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116273.v2.p2"
   371) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277303.v1.p1"
   372) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114867.v2.p2"
   373) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00252996.v1.p1"
   374) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254156.v1.p10"
   375) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210311.v1.p1"
   376) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000641.v1.p10"
   377) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277519.v1.p1"
   378) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055286.v5.p10"
   379) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254089.v1.p10"
   380) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00124251.v1.p1"
   381) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114124.v2.p2"
   382) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000722.v1.p10"
   383) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177354.v2.p10"
   384) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001373.v1.p10"
   385) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009487.v5.p10"
   386) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086716.v2.p3"
   387) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005229.v1.p10"
   388) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210317.v1.p1"
   389) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177022.v1.p3"
   390) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307968.v1.p1"
   391) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008161.v5.p10"
   392) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007688.v5.p10"
   393) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277523.v1.p1"
   394) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277145.v1.p10"
   395) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00066713.v4.p10"
   396) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307800.v1.p1"
   397) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277665.v1.p1"
   398) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008759.v5.p10"
   399) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087513.v1.p3"
   400) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250995.v1.p10"
   401) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307804.v1.p1"
   402) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083407.v1.p3"
   403) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008771.v5.p10"
   404) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008197.v5.p10"
   405) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116572.v2.p2"
   406) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024457.v5.p10"
   407) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00100436.v1.p1"
   408) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00106795.v1.p1"
   409) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083404.v1.p3"
   410) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119716.v2.p2"
   411) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119712.v2.p2"
   412) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254708.v1.p10"
   413) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00107775.v1.p1"
   414) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125872.v1.p1"
   415) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175588.v1.p3"
   416) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004534.v1.p10"
   417) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002948.v1.p10"
   418) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000919.v1.p10"
   419) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000921.v1.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 553.090800 milliseconds"

real	0m0.607s
user	0m0.009s
sys	0m0.006s
MATCH (a { id : 'TOPMED.VAR:phv00000484.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:64"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 117.137100 milliseconds"

real	0m0.142s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000487.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:30"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 111.524400 milliseconds"

real	0m0.132s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000496.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:74"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 109.366700 milliseconds"

real	0m0.127s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000517.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:26"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 108.431400 milliseconds"

real	0m0.126s
user	0m0.002s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000518.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:40"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 101.857500 milliseconds"

real	0m0.118s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000528.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:7"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 112.201800 milliseconds"

real	0m0.129s
user	0m0.002s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000529.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:8"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 102.648200 milliseconds"

real	0m0.118s
user	0m0.002s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000530.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:7"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 102.786900 milliseconds"

real	0m0.118s
user	0m0.002s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000531.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:8"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 103.365400 milliseconds"

real	0m0.118s
user	0m0.002s
sys	0m0.004s
1) 1) "count(a)"
   2) "count(b)"
2) 1) 1) (integer) 1295945
      2) (integer) 1295945
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 1687.526500 milliseconds"

real	0m1.700s
user	0m0.002s
sys	0m0.004s
```
