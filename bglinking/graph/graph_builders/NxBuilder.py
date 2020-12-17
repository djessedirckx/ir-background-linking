import networkx as nx
import numpy as np

from bglinking.graph.graph import Graph
from bglinking.graph.Node import Node

def convert_to_nx(paragraph_id, doc_id, orig_graph: Graph) -> nx.Graph:

    # Create new insance of nx Graph
    paragraph_graph = nx.Graph()
    paragraph_graph.graph['paragraph_id'] = paragraph_id
    paragraph_graph.graph['doc_id'] = doc_id

    # Add all nodes from original graph to nx graph
    for term, node in orig_graph.nodes.items():
        paragraph_graph.add_node(term, w = node.weight)

    # Add all edges from original graph to nx graph
    for edge in orig_graph.edges.items():
        edge_values = edge[0]
        edge_weight = edge[1]
        paragraph_graph.add_edge(edge_values[0], edge_values[1], weight = edge_weight)

    return paragraph_graph

def create_document_graph(paragraph_graphs, doc_id, fname, use_gcc=False) -> Graph:
    doc_graph = nx.Graph()
    central_nodes = []

    # Fetch central nodes
    for par_graph in paragraph_graphs:
        doc_graph = nx.compose(doc_graph, par_graph)

        central_node_result = central_node(par_graph)
        if central_node_result:
            central_nodes.append(central_node_result)

    # Create edges
    for i in range(len(central_nodes)-1):
        doc_graph.add_edge(central_nodes[i], central_nodes[i+1], weight = max(1/np.sqrt(i+1),0.2))

    # Create connected graph
    if use_gcc:
        gcc = max(nx.connected_components(doc_graph), key=len)
        g0 = doc_graph.subgraph(gcc)
    else:
        g0 = doc_graph
    g0.name = doc_id

    return nx_to_internal_graph(g0, doc_id, "test")

def central_node(graph):
    betw_centr = nx.betweenness_centrality(graph)
    betw_keys = list(betw_centr.keys())

    if betw_keys:
        return betw_keys[np.argmax(np.array([betw_centr[i] for i in betw_keys]))]
    return None

def nx_to_internal_graph(doc_graph: nx.Graph, doc_id, fname) -> Graph:
    internal_graph = Graph(doc_id, fname)

    # Convert nodes
    for node in doc_graph.nodes:
        graph_node = Node(node, 'term', [], 0)
        graph_node.weight = doc_graph.nodes[node]['w']
        internal_graph.add_node(graph_node)

    # Convert edges
    for edge in doc_graph.edges:
        edge_weight = doc_graph.edges[edge]['weight']
        internal_graph.add_edge(*edge, edge_weight)

    return internal_graph

