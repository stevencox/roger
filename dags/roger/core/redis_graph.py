import copy

import redis
# from redisgraph import Node, Edge, Graph
# https://redis-py.readthedocs.io/en/v4.5.1/redismodules.html#redisgraph-commands
from redis.commands.graph.node import Node
from redis.commands.graph.edge import Edge

from roger.logger import get_logger

logger = get_logger ()

class RedisGraph:
    """ Graph abstraction over RedisGraph. A thin wrapper but provides us some options. """
    
    def __init__(self, host='localhost', port=6379, graph='default', password=''):
        """ Construct a connection to Redis Graph. """
        self.r = redis.Redis(host=host, port=port, password=password)
        self.redis_graph = self.r.graph(graph)

    def add_node (self, identifier=None, label=None, properties=None):
        """ Add a node with the given label and properties. """
        logger.debug (f"--adding node id:{identifier} label:{label} prop:{properties}")
        if identifier and properties:
            properties['id'] = identifier
        node = Node(node_id=identifier, alias=identifier, label=label, properties=properties)
        self.redis_graph.add_node(node)
        return node

    def get_edge (self, start, end, predicate=None):
        """ Get an edge from the graph with the specified start and end identifiers. """
        result = None
        for edge in self.redis_graph.edges:
            if edge.src_node.id == start and edge.dest_node.id == end:
                result = edge
                break
        return result
    
    def add_edge (self, start, predicate, end, properties={}):
        """ Add an edge with the given predicate and properties between start and end nodes. """
        logger.debug (f"--adding edge start:{start} pred:{predicate} end:{end} prop:{properties}")
        if isinstance(start, str) and isinstance(end, str):
            start = Node(node_id = start, label='thing')
            end = Node(node_id = end, label='thing')
            self.redis_graph.add_node (start)
            self.redis_graph.add_node (end)
        edge = Edge(start, predicate, end, properties)
        self.redis_graph.add_edge (edge)
        return edge

    def has_node (self, identifier):
        return identifier in self.redis_graph.nodes

    def get_node (self, identifier, properties=None):
        return self.redis_graph.nodes[identifier]
    
    def commit (self):
        """ Commit modifications to the graph. """
        self.redis_graph.commit()

    def query (self, query):
        """ Query and return result set. """
        result = self.redis_graph.query(query)
        print(result)
        return result
    
    def delete (self):
        """ Delete the named graph. """
        self.redis_graph.delete()
        
def test ():
    rg = RedisGraph ()
    p = { 'a' : 4,
          'b' : 'c',
          'x' : 0 }
    last = None
    for x in range(0, 10000):
        p['x'] = x + 1
        node = rg.add_node (
            label='yeah',
            properties=copy.deepcopy (p))
        if last is not None:
            rg.add_edge (node, 'link', last)
        last = node
    rg.commit ()    
    rg.query ("""MATCH (obj:yeah)-[:link]->(j:yeah) RETURN obj.a, obj.b, obj.x""")    
    rg.query ("""MATCH (a) RETURN a""")
    rg.delete ()

#    rg.query ("""MATCH (a { id : 'chemical_substance' }) RETURN a""")
#test ()