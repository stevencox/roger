# roger


```
$ ../bin/roger all
[roger][core.py][                 get] DEBUG: {
  "versions": [
    {
      "edgeFiles": [
        "chembio_kgx-edge-v0.1.json",
        "chemical_normalization-edge-v0.1.json",
        "cord19-phenotypes-edge-v0.1.json",
        "ctd-edge-v0.1.json",
        "foodb-edge-v0.1.json",
        "mychem-edge-v0.1.json",
        "pharos-edge-v0.1.json",
        "topmed-edge-v0.1.json"
      ],
      "nodeFiles": [
        "biolink_kgx-node-v0.1.json",
        "chembio_kgx-node-v0.1.json",
        "chemical_normalization-node-v0.1.json",
        "cord19-phenotypes-node-v0.1.json",
        "cord19-scibite-node-v0.1.json",
        "cord19-scigraph-node-v0.1.json",
        "ctd-node-v0.1.json",
        "foodb-node-v0.1.json",
        "mychem-node-v0.1.json",
        "panther-node-v0.1.json",
        "pharos-node-v0.1.json",
        "topmed-node-v0.1.json"
      ],
      "version": "v0.1"
    },
    {
      "version": "test",
      "edgeFiles": [
        "cord19-phenotypes-edge-v0.1.json",
        "chembio_kgx-edge-v0.1.json"
      ],
      "nodeFiles": [
        "cord19-phenotypes-node-v0.1.json",
        "chembio_kgx-node-v0.1.json"
      ]
    }
  ]
}
[roger][core.py][                 get] DEBUG: Wrote data/kgx/chembio_kgx-v0.1.json: edges:21637, nodes: 8725 time:2179
[roger][core.py][                 get] DEBUG: Wrote data/kgx/chemical_normalization-v0.1.json: edges:277030, nodes: 72963 time:8215
[roger][core.py][                 get] DEBUG: Wrote data/kgx/cord19-phenotypes-v0.1.json: edges:24, nodes: 25 time:375
[roger][core.py][                 get] DEBUG: Wrote data/kgx/ctd-v0.1.json: edges:48363, nodes: 24008 time:4817
[roger][core.py][                 get] DEBUG: Wrote data/kgx/foodb-v0.1.json: edges:5429, nodes: 4536 time:1205
[roger][core.py][                 get] DEBUG: Wrote data/kgx/mychem-v0.1.json: edges:123119, nodes: 5496 time:9947
[roger][core.py][                 get] DEBUG: Wrote data/kgx/pharos-v0.1.json: edges:287750, nodes: 224349 time:31632
[roger][core.py][                 get] DEBUG: Wrote data/kgx/topmed-v0.1.json: edges:63860, nodes: 15870 time:5076

real	1m5.569s
user	0m47.474s
sys	0m3.452s
[roger][core.py][               merge] INFO: merging data/kgx/chembio_kgx-v0.1.json
[roger][core.py][               merge] DEBUG: merged     data/kgx/chemical_normalization-v0.1.json load:  997 scope:     47 merge: 32
[roger][core.py][               merge] DEBUG: merged          data/kgx/cord19-phenotypes-v0.1.json load:   89 scope:     28 merge:  0
[roger][core.py][               merge] DEBUG: merged                        data/kgx/ctd-v0.1.json load:  779 scope:     20 merge: 17
[roger][core.py][               merge] DEBUG: merged                      data/kgx/foodb-v0.1.json load:  124 scope:     20 merge:  1
[roger][core.py][               merge] DEBUG: merged                     data/kgx/mychem-v0.1.json load: 1357 scope:      9 merge:  4
[roger][core.py][               merge] DEBUG: merged                     data/kgx/pharos-v0.1.json load: 6233 scope:    169 merge:133
[roger][core.py][               merge] DEBUG: merged                     data/kgx/topmed-v0.1.json load:  755 scope:    146 merge:  3
Traceback (most recent call last):
  File "/Users/scox/dev/roger/roger/core.py", line 481, in <module>
    kgx.merge ()
  File "/Users/scox/dev/roger/roger/core.py", line 300, in merge
    Util.write_object (graph, new_path)
  File "/Users/scox/dev/roger/roger/core.py", line 114, in write_object
    os.makedirs (dirname, exist_ok=True)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/os.py", line 223, in makedirs
    mkdir(name, mode)
FileNotFoundError: [Errno 2] No such file or directory: ''
(rg) scox@morgancreek ~/dev/roger/roger$ ls data/
kgx/           merge/         metadata.yaml  
(rg) scox@morgancreek ~/dev/roger/roger$ ls data/me
merge/         metadata.yaml  
(rg) scox@morgancreek ~/dev/roger/roger$ ls data/merge/
chemical_normalization-v0.1.json  ctd-v0.1.json                     mychem-v0.1.json                  topmed-v0.1.json                  
cord19-phenotypes-v0.1.json       foodb-v0.1.json                   pharos-v0.1.json                  
(rg) scox@morgancreek ~/dev/roger/roger$ ../bin/roger all
[roger][core.py][                 get] DEBUG: {
  "versions": [
    {
      "edgeFiles": [
        "chembio_kgx-edge-v0.1.json",
        "chemical_normalization-edge-v0.1.json",
        "cord19-phenotypes-edge-v0.1.json",
        "ctd-edge-v0.1.json",
        "foodb-edge-v0.1.json",
        "mychem-edge-v0.1.json",
        "pharos-edge-v0.1.json",
        "topmed-edge-v0.1.json"
      ],
      "nodeFiles": [
        "biolink_kgx-node-v0.1.json",
        "chembio_kgx-node-v0.1.json",
        "chemical_normalization-node-v0.1.json",
        "cord19-phenotypes-node-v0.1.json",
        "cord19-scibite-node-v0.1.json",
        "cord19-scigraph-node-v0.1.json",
        "ctd-node-v0.1.json",
        "foodb-node-v0.1.json",
        "mychem-node-v0.1.json",
        "panther-node-v0.1.json",
        "pharos-node-v0.1.json",
        "topmed-node-v0.1.json"
      ],
      "version": "v0.1"
    },
    {
      "version": "test",
      "edgeFiles": [
        "cord19-phenotypes-edge-v0.1.json",
        "chembio_kgx-edge-v0.1.json"
      ],
      "nodeFiles": [
        "cord19-phenotypes-node-v0.1.json",
        "chembio_kgx-node-v0.1.json"
      ]
    }
  ]
}
[roger][core.py][                 get] DEBUG: Wrote                data/kgx/chembio_kgx-v0.1.json: edges:  21637, nodes:    8725 time:    2590
[roger][core.py][                 get] DEBUG: Wrote     data/kgx/chemical_normalization-v0.1.json: edges: 277030, nodes:   72963 time:    8358
[roger][core.py][                 get] DEBUG: Wrote          data/kgx/cord19-phenotypes-v0.1.json: edges:     24, nodes:      25 time:     332
[roger][core.py][                 get] DEBUG: Wrote                        data/kgx/ctd-v0.1.json: edges:  48363, nodes:   24008 time:    4710
[roger][core.py][                 get] DEBUG: Wrote                      data/kgx/foodb-v0.1.json: edges:   5429, nodes:    4536 time:    1074
[roger][core.py][                 get] DEBUG: Wrote                     data/kgx/mychem-v0.1.json: edges: 123119, nodes:    5496 time:    9276
[roger][core.py][                 get] DEBUG: Wrote                     data/kgx/pharos-v0.1.json: edges: 287750, nodes:  224349 time:   30312
[roger][core.py][                 get] DEBUG: Wrote                     data/kgx/topmed-v0.1.json: edges:  63860, nodes:   15870 time:    4996

real	1m5.000s
user	0m46.778s
sys	0m3.455s
[roger][core.py][               merge] INFO: merging data/kgx/chembio_kgx-v0.1.json
[roger][core.py][               merge] DEBUG: merged     data/kgx/chemical_normalization-v0.1.json load:  977 scope:     44 merge: 26
[roger][core.py][               merge] DEBUG: merged          data/kgx/cord19-phenotypes-v0.1.json load:   69 scope:     30 merge:  0
[roger][core.py][               merge] DEBUG: merged                        data/kgx/ctd-v0.1.json load:  765 scope:     21 merge: 18
[roger][core.py][               merge] DEBUG: merged                      data/kgx/foodb-v0.1.json load:  130 scope:     25 merge:  1
[roger][core.py][               merge] DEBUG: merged                     data/kgx/mychem-v0.1.json load: 1413 scope:      9 merge:  3
[roger][core.py][               merge] DEBUG: merged                     data/kgx/pharos-v0.1.json load: 5963 scope:    182 merge:117
[roger][core.py][               merge] DEBUG: merged                     data/kgx/topmed-v0.1.json load:  716 scope:    145 merge:  3
[roger][core.py][               merge] INFO: data/kgx/chembio_kgx-v0.1.json rewrite: 982. total merge time: 40393
[roger][core.py][               merge] INFO: using cached merge: data/merge/chemical_normalization-v0.1.json
[roger][core.py][               merge] INFO: using cached merge: data/merge/cord19-phenotypes-v0.1.json
[roger][core.py][               merge] INFO: using cached merge: data/merge/ctd-v0.1.json
[roger][core.py][               merge] INFO: using cached merge: data/merge/foodb-v0.1.json
[roger][core.py][               merge] INFO: using cached merge: data/merge/mychem-v0.1.json
[roger][core.py][               merge] INFO: using cached merge: data/merge/pharos-v0.1.json
[roger][core.py][               merge] INFO: using cached merge: data/merge/topmed-v0.1.json

real	0m45.119s
user	0m40.319s
sys	0m2.677s
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

real	0m31.917s
user	0m28.378s
sys	0m1.788s
[roger][core.py][              create] INFO: processing data/merge/chembio_kgx-v0.1.json
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/chemical_substance.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/gene.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/named_thing.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/directly_interacts_with.csv
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
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/molecular_activity.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/anatomical_entity.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/cell.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/biological_process.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/nodes/cellular_component.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/association.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/has_part.csv
[roger][core.py][          write_bulk] INFO:   --creating data/bulk/edges/part_of.csv

real	0m54.960s
user	0m48.775s
sys	0m2.611s
"Graph removed, internal execution time: 0.072000 milliseconds"
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
decreases_activity_of  [##################################--]   96%  00:00:01
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
Construction of graph 'test' complete: 310264 nodes created, 826470 relations created in 219.576044 seconds

real	3m40.549s
user	2m25.485s
sys	0m3.590s
1) 1) "count(a)"
2) 1) 1) (integer) 310264
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 21.570300 milliseconds"

real	0m0.055s
user	0m0.002s
sys	0m0.003s
1) 1) "count(e)"
2) 1) 1) (integer) 826470
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 7.373500 milliseconds"

real	0m0.036s
user	0m0.003s
sys	0m0.005s
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
        2) "TOPMED.VAR:phv00112492.v2.p2"
     6) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00107775.v1.p1"
     7) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210338.v1.p1"
     8) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250916.v1.p10"
     9) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277137.v1.p10"
    10) 1) "[named_thing]"
        2) "ZFA:0000007"
    11) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177026.v1.p3"
    12) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119714.v2.p2"
    13) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006922.v1.p10"
    14) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115333.v2.p2"
    15) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125892.v1.p1"
    16) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009906.v5.p10"
    17) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009559.v5.p10"
    18) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116574.v2.p2"
    19) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001375.v1.p10"
    20) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114134.v2.p2"
    21) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087043.v2.p3"
    22) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00079865.v6.p3"
    23) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001570.v1.p10"
    24) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277139.v1.p10"
    25) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00251409.v1.p10"
    26) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00226391.v1.p1"
    27) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277145.v1.p10"
    28) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125877.v1.p1"
    29) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00255099.v1.p10"
    30) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116556.v2.p2"
    31) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116273.v2.p2"
    32) 1) "[named_thing]"
        2) "PATO:0001025"
    33) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007577.v5.p10"
    34) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128374.v1.p1"
    35) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277346.v1.p1"
    36) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116572.v2.p2"
    37) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112490.v2.p2"
    38) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277519.v1.p1"
    39) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119239.v2.p2"
    40) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119708.v2.p2"
    41) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307964.v1.p1"
    42) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005549.v1.p10"
    43) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116136.v2.p2"
    44) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274553.v1.p10"
    45) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175602.v1.p3"
    46) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085736.v2.p3"
    47) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210308.v1.p1"
    48) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00079855.v6.p3"
    49) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177029.v1.p3"
    50) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119706.v2.p2"
    51) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010508.v5.p10"
    52) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086721.v2.p3"
    53) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005935.v1.p10"
    54) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00283300.v1.p3"
    55) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000923.v1.p10"
    56) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002432.v1.p10"
    57) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001042.v1.p10"
    58) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001373.v1.p10"
    59) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123865.v1.p1"
    60) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006513.v1.p10"
    61) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114118.v2.p2"
    62) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114124.v2.p2"
    63) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00258703.v1.p1"
    64) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00122648.v1.p1"
    65) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00104698.v1.p1"
    66) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001046.v1.p10"
    67) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210288.v1.p1"
    68) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274062.v1.p10"
    69) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00273970.v1.p10"
    70) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128371.v1.p1"
    71) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001814.v1.p10"
    72) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00283537.v1.p3"
    73) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000838.v1.p10"
    74) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210309.v1.p1"
    75) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002678.v1.p10"
    76) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00084495.v2.p3"
    77) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00275181.v1.p10"
    78) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007111.v1.p10"
    79) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000641.v1.p10"
    80) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307960.v1.p1"
    81) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00276848.v1.p10"
    82) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004549.v1.p10"
    83) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119704.v2.p2"
    84) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114120.v2.p2"
    85) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210358.v1.p1"
    86) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00066713.v4.p10"
    87) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307802.v1.p1"
    88) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214059.v1.p1"
    89) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002029.v1.p10"
    90) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307812.v1.p1"
    91) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116245.v2.p2"
    92) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002211.v1.p10"
    93) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307738.v1.p1"
    94) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115341.v2.p2"
    95) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277771.v1.p1"
    96) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008759.v5.p10"
    97) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00283298.v1.p3"
    98) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083404.v1.p3"
    99) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004109.v1.p10"
   100) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112482.v2.p2"
   101) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010361.v5.p10"
   102) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087510.v1.p3"
   103) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00021093.v4.p10"
   104) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119710.v2.p2"
   105) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277142.v1.p10"
   106) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116566.v2.p2"
   107) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277521.v1.p1"
   108) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277342.v1.p1"
   109) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210315.v1.p1"
   110) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177036.v1.p3"
   111) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254156.v1.p10"
   112) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116261.v2.p2"
   113) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086716.v2.p3"
   114) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254089.v1.p10"
   115) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024480.v5.p10"
   116) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086225.v2.p3"
   117) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177022.v1.p3"
   118) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116233.v2.p2"
   119) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010001.v5.p10"
   120) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307800.v1.p1"
   121) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006681.v1.p10"
   122) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024413.v4.p10"
   123) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00079857.v6.p3"
   124) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210339.v1.p1"
   125) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007573.v5.p10"
   126) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008771.v5.p10"
   127) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277144.v1.p10"
   128) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277535.v1.p1"
   129) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115347.v2.p2"
   130) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112495.v2.p2"
   131) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128372.v1.p1"
   132) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177354.v2.p10"
   133) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000919.v1.p10"
   134) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118279.v2.p2"
   135) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00177419.v2.p10"
   136) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006253.v1.p10"
   137) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001200.v1.p10"
   138) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119724.v2.p2"
   139) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000921.v1.p10"
   140) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114114.v2.p2"
   141) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006042.v1.p10"
   142) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00273915.v1.p10"
   143) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210359.v1.p1"
   144) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210332.v1.p1"
   145) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006044.v1.p10"
   146) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118293.v2.p2"
   147) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001196.v1.p10"
   148) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307816.v1.p1"
   149) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307808.v1.p1"
   150) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003317.v1.p10"
   151) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010123.v5.p10"
   152) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085741.v2.p3"
   153) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114132.v2.p2"
   154) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115204.v2.p2"
   155) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307763.v1.p1"
   156) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119720.v2.p2"
   157) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277777.v1.p1"
   158) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274824.v1.p10"
   159) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307968.v1.p1"
   160) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000643.v1.p10"
   161) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277143.v1.p10"
   162) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000834.v1.p10"
   163) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115339.v2.p2"
   164) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083400.v1.p3"
   165) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116269.v2.p2"
   166) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008631.v5.p10"
   167) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003691.v1.p10"
   168) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008712.v5.p10"
   169) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114116.v2.p2"
   170) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125872.v1.p1"
   171) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007359.v1.p10"
   172) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006337.v1.p10"
   173) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118291.v2.p2"
   174) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00124249.v1.p1"
   175) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055290.v5.p10"
   176) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115337.v2.p2"
   177) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307972.v1.p1"
   178) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277034.v1.p10"
   179) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116241.v2.p2"
   180) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277299.v1.p1"
   181) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214093.v1.p1"
   182) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114128.v2.p2"
   183) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307759.v1.p1"
   184) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085738.v2.p3"
   185) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123851.v1.p1"
   186) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175592.v1.p3"
   187) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003173.v1.p10"
   188) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008197.v5.p10"
   189) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307736.v1.p1"
   190) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123871.v1.p1"
   191) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210312.v1.p1"
   192) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307976.v1.p1"
   193) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307749.v1.p1"
   194) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175588.v1.p3"
   195) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123848.v1.p1"
   196) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112486.v2.p2"
   197) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277670.v1.p1"
   198) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000722.v1.p10"
   199) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112476.v2.p2"
   200) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000760.v1.p10"
   201) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00110338.v1.p1"
   202) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000623.v1.p10"
   203) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118277.v2.p2"
   204) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116568.v2.p2"
   205) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277303.v1.p1"
   206) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118285.v2.p2"
   207) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210361.v1.p1"
   208) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210333.v1.p1"
   209) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024892.v1.p10"
   210) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000533.v1.p10"
   211) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085704.v2.p3"
   212) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210286.v1.p1"
   213) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024462.v5.p10"
   214) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055257.v5.p10"
   215) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116570.v2.p2"
   216) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00102575.v1.p1"
   217) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277785.v1.p1"
   218) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116554.v2.p2"
   219) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004092.v1.p10"
   220) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123868.v1.p1"
   221) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024457.v5.p10"
   222) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210317.v1.p1"
   223) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003676.v1.p10"
   224) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277531.v1.p1"
   225) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001371.v1.p10"
   226) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008161.v5.p10"
   227) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001812.v1.p10"
   228) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307962.v1.p1"
   229) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254708.v1.p10"
   230) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277338.v1.p1"
   231) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087041.v2.p3"
   232) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210364.v1.p1"
   233) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004107.v1.p10"
   234) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115335.v2.p2"
   235) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083407.v1.p3"
   236) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125882.v1.p1"
   237) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210362.v1.p1"
   238) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005856.v1.p10"
   239) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00122564.v1.p1"
   240) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002209.v1.p10"
   241) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000645.v1.p10"
   242) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000758.v1.p10"
   243) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00070558.v1.p10"
   244) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087038.v2.p3"
   245) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115345.v2.p2"
   246) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119722.v2.p2"
   247) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112488.v2.p2"
   248) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115349.v2.p2"
   249) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00021240.v4.p10"
   250) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003307.v1.p10"
   251) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277769.v1.p1"
   252) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118297.v2.p2"
   253) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009487.v5.p10"
   254) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119718.v2.p2"
   255) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116562.v2.p2"
   256) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00070501.v1.p10"
   257) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116277.v2.p2"
   258) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112478.v2.p2"
   259) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274463.v1.p10"
   260) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00009396.v5.p10"
   261) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210311.v1.p1"
   262) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114867.v2.p2"
   263) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086233.v2.p3"
   264) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118287.v2.p2"
   265) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00099442.v1.p1"
   266) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003247.v1.p10"
   267) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277138.v1.p10"
   268) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254611.v1.p10"
   269) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210335.v1.p1"
   270) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123855.v1.p1"
   271) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005139.v1.p10"
   272) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116237.v2.p2"
   273) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00085733.v2.p3"
   274) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000762.v1.p10"
   275) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002676.v1.p10"
   276) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006251.v1.p10"
   277) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024866.v1.p10"
   278) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114122.v2.p2"
   279) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00254769.v1.p10"
   280) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277781.v1.p1"
   281) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210289.v1.p1"
   282) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128377.v1.p1"
   283) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001810.v1.p10"
   284) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086235.v2.p3"
   285) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277527.v1.p1"
   286) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250995.v1.p10"
   287) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003177.v1.p10"
   288) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024779.v5.p10"
   289) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002027.v1.p10"
   290) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086708.v2.p3"
   291) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114875.v2.p2"
   292) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024894.v1.p10"
   293) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007686.v5.p10"
   294) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00104021.v1.p1"
   295) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307751.v1.p1"
   296) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277773.v1.p1"
   297) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123845.v1.p1"
   298) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277295.v1.p1"
   299) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00072139.v4.p10"
   300) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114871.v2.p2"
   301) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002674.v1.p10"
   302) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00010434.v5.p10"
   303) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00083411.v1.p3"
   304) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00024825.v4.p10"
   305) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116560.v2.p2"
   306) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274723.v1.p10"
   307) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114126.v2.p2"
   308) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087030.v2.p3"
   309) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003592.v1.p10"
   310) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125887.v1.p1"
   311) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056836.v2.p10"
   312) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119712.v2.p2"
   313) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056854.v2.p10"
   314) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112484.v2.p2"
   315) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210285.v1.p1"
   316) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087085.v1.p3"
   317) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277665.v1.p1"
   318) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116265.v2.p2"
   319) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00108831.v1.p1"
   320) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00119716.v2.p2"
   321) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214089.v1.p1"
   322) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087513.v1.p3"
   323) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210283.v1.p1"
   324) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007042.v1.p10"
   325) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114130.v2.p2"
   326) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00003689.v1.p10"
   327) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00105433.v1.p1"
   328) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007684.v5.p10"
   329) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004534.v1.p10"
   330) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001572.v1.p10"
   331) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001568.v1.p10"
   332) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277035.v1.p10"
   333) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123002.v1.p1"
   334) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001198.v1.p10"
   335) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055288.v5.p10"
   336) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005767.v1.p10"
   337) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055286.v5.p10"
   338) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00004547.v1.p10"
   339) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00021148.v4.p10"
   340) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00122562.v1.p1"
   341) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086237.v2.p3"
   342) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002948.v1.p10"
   343) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210314.v1.p1"
   344) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000529.v1.p10"
   345) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007688.v5.p10"
   346) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00084497.v2.p3"
   347) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00128375.v1.p1"
   348) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000836.v1.p10"
   349) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000531.v1.p10"
   350) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00258704.v1.p1"
   351) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00125897.v1.p1"
   352) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008540.v5.p10"
   353) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007475.v1.p10"
   354) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307804.v1.p1"
   355) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000625.v1.p10"
   356) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210282.v1.p1"
   357) 1) "[named_thing]"
        2) "PATO:0000070"
   358) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00106795.v1.p1"
   359) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118281.v2.p2"
   360) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00072660.v4.p10"
   361) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118295.v2.p2"
   362) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116253.v2.p2"
   363) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116249.v2.p2"
   364) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00001044.v1.p10"
   365) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116229.v2.p2"
   366) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00101960.v1.p1"
   367) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115343.v2.p2"
   368) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00114879.v2.p2"
   369) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00055183.v4.p10"
   370) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00006608.v1.p10"
   371) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118289.v2.p2"
   372) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00205848.v1.p1"
   373) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00255003.v1.p10"
   374) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00118283.v2.p2"
   375) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056858.v2.p10"
   376) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210291.v1.p1"
   377) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00124251.v1.p1"
   378) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00070376.v1.p10"
   379) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00007575.v5.p10"
   380) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00124247.v1.p1"
   381) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307747.v1.p1"
   382) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277140.v1.p10"
   383) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307755.v1.p1"
   384) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002213.v1.p10"
   385) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00056856.v2.p10"
   386) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000720.v1.p10"
   387) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00251071.v1.p10"
   388) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115351.v2.p2"
   389) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00008757.v5.p10"
   390) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00307734.v1.p1"
   391) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00259053.v1.p1"
   392) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00159583.v4.p2"
   393) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00072213.v4.p10"
   394) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00275080.v1.p10"
   395) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277141.v1.p10"
   396) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250294.v1.p10"
   397) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00087506.v1.p3"
   398) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002434.v1.p10"
   399) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00277523.v1.p1"
   400) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00175595.v1.p3"
   401) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00274408.v1.p10"
   402) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00251342.v1.p10"
   403) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00252996.v1.p1"
   404) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210341.v1.p1"
   405) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00116257.v2.p2"
   406) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00210336.v1.p1"
   407) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250653.v1.p10"
   408) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00214091.v1.p1"
   409) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00115331.v2.p2"
   410) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002025.v1.p10"
   411) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00005229.v1.p10"
   412) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00112480.v2.p2"
   413) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00100436.v1.p1"
   414) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00000621.v1.p10"
   415) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00086719.v2.p3"
   416) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123858.v1.p1"
   417) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00002430.v1.p10"
   418) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00250562.v1.p10"
   419) 1) "[named_thing]"
        2) "TOPMED.VAR:phv00123861.v1.p1"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 695.919300 milliseconds"

real	0m0.732s
user	0m0.007s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000484.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
   2) 1) "[named_thing]"
      2) "TOPMED.TAG:64"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 106.934500 milliseconds"

real	0m0.122s
user	0m0.002s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000487.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:30"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 111.694800 milliseconds"

real	0m0.131s
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
   2) "Query internal execution time: 137.026900 milliseconds"

real	0m0.157s
user	0m0.002s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000517.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:26"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 116.563500 milliseconds"

real	0m0.134s
user	0m0.003s
sys	0m0.004s
MATCH (a { id : 'TOPMED.VAR:phv00000518.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:40"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 102.652600 milliseconds"

real	0m0.116s
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
   2) "Query internal execution time: 103.262900 milliseconds"

real	0m0.119s
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
   2) "Query internal execution time: 107.025700 milliseconds"

real	0m0.120s
user	0m0.002s
sys	0m0.003s
MATCH (a { id : 'TOPMED.VAR:phv00000530.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:7"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 106.251400 milliseconds"

real	0m0.124s
user	0m0.002s
sys	0m0.003s
MATCH (a { id : 'TOPMED.VAR:phv00000531.v1.p10' })--(b) RETURN a.category, b.id
1) 1) "a.category"
   2) "b.id"
2) 1) 1) "[named_thing]"
      2) "TOPMED.TAG:8"
   2) 1) "[named_thing]"
      2) "TOPMED.STUDY:phs000007.v29.p10"
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 102.045000 milliseconds"

real	0m0.117s
user	0m0.002s
sys	0m0.004s
1) 1) "count(a)"
   2) "count(b)"
2) 1) 1) (integer) 1295945
      2) (integer) 1295945
3) 1) "Cached execution: 0"
   2) "Query internal execution time: 1542.060800 milliseconds"

real	0m1.557s
user	0m0.002s
sys	0m0.004s
```
