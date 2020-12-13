import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
import pandas as pd
import numpy as np
import random
import ast

def graph_generator(text_file,document,ParagraphNumber):
    my_file = open(text_file, "r")
    content = my_file.read()
    ContnetList = content.split("Document id: ")
    #document = 0 # range(len(ContnetList)-1) <-------------------
    doc_graph = pd.DataFrame()
    doc_id = []
    pragraph_level = ContnetList[document+1].split("==========================================") # For the frist
    Number_of_paragraphs = len(pragraph_level)-2  # Last empty row and final element -2
    for paragraph in range(Number_of_paragraphs):
        data = pragraph_level[paragraph].split('\n')
        while '' in data:
            data.remove('')
        if paragraph==0:
            doc_id.append(data[0])
            data.remove(data[0])
        doc_graph = pd.concat([doc_graph, pd.DataFrame(data)], ignore_index=True, axis=1)

    node=0 # initialize variables-------------------------------------------
    EdgeOrNode = 1 # 0 is paragraph id , 1 is nodes, 2 is edges
    #Number_of_paragraphs
    #ParagraphNumber = 1
    # Cycle all id node and edges
    nodes = []
    edges =[]
    for EdgeOrNode in range(3):
        if EdgeOrNode == 0:
            P_id = doc_graph[ParagraphNumber][EdgeOrNode].split('Term: ')#[node+1]
            P_id = P_id[0][-1:]
        elif EdgeOrNode == 1:
            for node in range(len(doc_graph[ParagraphNumber][EdgeOrNode].split('Term: '))-1):
                nodes.append(doc_graph[ParagraphNumber][EdgeOrNode].split('Term: ')[node+1])
        elif EdgeOrNode == 2:
            edges = doc_graph[ParagraphNumber][EdgeOrNode].split('Term: ')[0][36:-1]
            edges = ast.literal_eval(edges)
    # Create a graph for the paragraph ------------------------
    G = nx.Graph()
    G.graph['Paragraph_id'] = P_id
    G.graph['Doc_id'] = doc_id[0]
    for node_n in range(len(nodes)):  # Add nodes
        N_ = nodes[node_n].split(', ')
        G.add_node(N_[0], w = float(N_[1][8:-3]))
    #nx.draw(G,with_labels = True)
    for i in range(len(list(edges.keys()))): # Add edges
        G.add_edge(list(edges.keys())[i][0],list(edges.keys())[i][1], weight = edges[list(edges.keys())[0]])
    #nx.draw(G,with_labels = True)
    return G,Number_of_paragraphs,doc_id
def GraphFromText(Text_file,document_number):#
    N_parapgraphs = graph_generator("paragraph_graph_export_weights.txt",document_number,1)[1]
    Graphs = [graph_generator("paragraph_graph_export_weights.txt",document_number,i)[0] for i in range(N_parapgraphs)]
    doc_id=graph_generator("paragraph_graph_export_weights.txt",document_number,1)[2]
    return Graphs,doc_id

def central_node(G): # Compute central node
    b = nx.betweenness_centrality(G)
    L = list(b.keys())
    return L[np.argmax(np.array([b[i] for i in L]))]

def ComposeFull(L): # Link into a single graph
    F = nx.Graph()
    central = []
    for g in L:
        F = nx.compose(F,g)
        central.append(central_node(g))
    for i in range(len(central)-1):
        F.add_edge(central[i], central[i+1], weight = max(1/np.sqrt(i+1),0.2))
    return F

def GCC_txt(TextFile, Document):
    Graphs, doc_id = GraphFromText("paragraph_graph_export_weights.txt",Document)
    document_graph = ComposeFull(Graphs)
    Gcc = max(nx.connected_components(document_graph), key=len)
    G0 = document_graph.subgraph(Gcc)
    G0.name=doc_id[0]
    return G0

def NxToPep(NXGraph,docid,fname):
        PepGraph = Graph(docid,fname)
        tf = 1 # It is not in the construction of the NX graph object
        term_positions=[0] # Not in the construction of the NX graph object
        nodes__ = dict([(i,
                         Node(i,
                         'term',
                         term_positions, # We could add this as a list in the arguments maybe
                         tf, # We could add this in the arguments maybe
                         GCC.nodes[i]['w'])) for i in GCC.nodes])
        PepGraph.__nodes =  nodes__
        # Transform the edges 
        PepGraph.__edges = dict([((i[0],i[1]),GCC[i[0]][i[1]]['weight']) for i in GCC.edges])
        return PepGraph
