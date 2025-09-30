MATCH (c{id:'HP:0032316'}) return c

MATCH (disease:`Disease` {`id`: 'MONDO:0004979'}) WITH disease MATCH (disease)-[e1_disease_phenotypic_feature]-(phenotypic_feature:`PhenotypicFeature` {})
WITH disease AS disease, phenotypic_feature AS phenotypic_feature, collect(e1_disease_phenotypic_feature) AS e1_disease_phenotypic_feature
RETURN disease,phenotypic_feature,e1_disease_phenotypic_feature,labels(disease) AS type__disease,labels(phenotypic_feature) AS type__phenotypic_feature,[edge in e1_disease_phenotypic_feature | type(edge)] AS type__e1_disease_phenotypic_feature,[edge in e1_disease_phenotypic_feature | [startNode(edge).id, endNode(edge).id]] AS id_pairs__e1_disease_phenotypic_feature