ROGER_MAKE_DIR=./roger_graph_build
ANNOTATE_MAKE_DIR=./dug_annotate
INDEXING_MAKE_DIR=./dug_indexing


RM=/bin/rm

DATA_ROOT=${ROGERENV_DATA__ROOT}


clean:
	$(RM) -rf $(DATA_ROOT)


annotate:
	make -C ${ANNOTATE_MAKE_DIR} all

graph:
	make -C ${ROGER_MAKE_DIR} all

index:
	make -C ${INDEXING_MAKE_DIR} all

all: annotate graph index