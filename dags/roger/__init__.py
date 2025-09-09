"Roger: an automated graph data curation pipeline."

from roger.core.base import (
    Roger,
    roger_cli,
    get_kgx,
    create_schema,
    create_edges_schema,
    create_nodes_schema,
    merge_nodes,
    create_bulk_load,
    create_bulk_nodes,
    create_bulk_edges,
    bulk_load,
    validate,
    check_tranql,
)

if __name__ == "__main__":
    roger_cli()
