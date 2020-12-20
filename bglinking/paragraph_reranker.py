import os
import argparse
from tqdm import tqdm
import json
import numpy as np
from operator import attrgetter
import sys

from pyserini import search
from pyserini import index
from pyserini import analysis
import networkx as nx

from bglinking.general_utils import utils
from bglinking.database_utils import db_utils
from bglinking.graph.graph import Graph
from bglinking.graph.graph_comparators.GMCSComparator import GMCSComparator
from bglinking.graph.graph_builders.DefaultGraphBuilder import DefaultGraphBuilder
from bglinking.graph.graph_builders.ParagraphGraphBuilder import ParagraphGraphBuilder
from bglinking.graph.graph_builders.NxBuilder import convert_to_nx, create_document_graph

parser = argparse.ArgumentParser()
parser.add_argument('--index', dest='index', default='lucene-index.core18.pos+docvectors+rawdocs_all',
                    help='specify the corpus index')

parser.add_argument('--db', dest='db', default='entity_database_19.db',
                    help='specify the database')

parser.add_argument('--embedding', dest='embedding', default='',
                    help='specify the embeddings to use')

parser.add_argument('--stats', dest='stats', default=False,
                    help='Show index stats')

parser.add_argument('--year', dest='year', default=None, type=int,
                    help='TREC year 18, 19 or 20')

parser.add_argument('--topics', dest='topics', default='topics.backgroundlinking19.txt',
                    help='specify qrels file')

parser.add_argument('--candidates', dest='candidates', default='run.backgroundlinking20.bm25+rm3.topics.backgroundlinking20.txt',
                    help='Results file that carries candidate docs')

parser.add_argument('--qrels', dest='qrels', default='qrels.backgroundlinking19.txt',
                    help='specify qrels file')

parser.add_argument('--output', dest='output', default='output_graph.txt',
                    help='specify output file')

parser.add_argument('--run-tag', dest='run_tag', default='unspecified_run_tag',
                    help='specify run tag')

parser.add_argument('--anserini', dest='anserini', default='/Volumes/Samsung_T5/anserini',
                    help='path to anserini')

parser.add_argument('--textrank', dest='textrank', default=False, action='store_true',
                    help='Apply TextRank')

parser.add_argument('--use-entities', dest='use_entities', default=False, action='store_true',
                    help='Use named entities as graph nodes')

parser.add_argument('--nr-terms', dest='nr_terms', default=0, type=int,
                    help='Number of tfidf terms to include in graph')

parser.add_argument('--term-tfidf', dest='term_tfidf', default=1.0, type=float,
                    help='Weight that should be assigned to tfidf score of terms (for node initialization)')

parser.add_argument('--term-position', dest='term_position', default=0.0, type=float,
                    help='Weight for term position in initial node weight')

parser.add_argument('--term-embedding', dest='term_embedding', default=0.0, type=float,
                    help='Weight for word embeddings in edge creation')

parser.add_argument('--text-distance', dest='text_distance', default=0.0, type=float,
                    help='Weight for text distance in edge creation')

parser.add_argument('--l', dest='node_edge_l', default=0.5, type=float,
                    help='Weight for importance nodes over edges')

parser.add_argument('--novelty', dest='novelty', default=0.0, type=float,
                    help='Weight for novelty in relevance score')

parser.add_argument('--diversify', dest='diversify', default=False, action='store_true',
                    help='Diversify the results according to entity types')

parser.add_argument('--use-gcc', dest='use_gcc', default=False, action='store_true',
                    help='Use GCC')

parser.add_argument('--passage-nr', dest='passage_nr', default=0, type=int,
                    help='Passage used as query graph')

args = parser.parse_args()
#utils.write_run_arguments_to_log(**vars(args))

if args.diversify and not args.use_entities:
    parser.error("--diversify requires --use-entities.")

if args.year is not None:
    if args.year == 20:
        args.index = 'lucene-index.core18.pos+docvectors+rawdocs_all_v3'
    args.db = f'entity_database_{args.year}.db'
    args.topics = f'topics.backgroundlinking{args.year}.txt'
    args.candidates = f'run.backgroundlinking{args.year}.bm25+rm3.topics.backgroundlinking{args.year}.txt'
    args.qrels = f'newsir{args.year}-qrels-background.txt'


print(f'\nIndex: resources/Index/{args.index}')
print(f'Topics were retrieved from resources/topics-and-qrels/{args.topics}')
print(f'Results are stored in resources/output/runs/{args.output}\n')
utils.create_new_file_for_sure(f'resources/output/{args.output}')

# '../database_utils/db/rel_entity_reader.db'
conn, cursor = db_utils.connect_db(f'resources/db/{args.db}')

# load word embeddings
if args.term_embedding > 0 and args.embedding != '':
    embeddings = utils.load_word_vectors(
        f'resources/embeddings/{args.embedding}')
    print('Embeddings sucessfully loaded!')
else:
    embeddings = {}

# Load index
index_utils = index.IndexReader(f'resources/Index/{args.index}')

# Configure graph options.
comparator = GMCSComparator()

# Build kwargs for graph initialization:
build_arguments = {'index_utils': index_utils,
                   'cursor': cursor,
                   'embeddings': embeddings,
                   'use_entities': args.use_entities,
                   'nr_terms': args.nr_terms,
                   'term_tfidf': args.term_tfidf,
                   'term_position': args.term_position,
                   'text_distance': args.text_distance,
                   'term_embedding': args.term_embedding}

# Read in topics via Pyserini.
topics = utils.read_topics_and_ids_from_file(
    f'resources/topics-and-qrels/{args.topics}')

paragraph_graph_builder = ParagraphGraphBuilder()

def export_doc_graph(doc_id, doc_graph):
    nodes = doc_graph.nodes.keys()
    edges = doc_graph.edges.keys()

    export_edges = []

    edge_nodes = set()
    for edge in edges:
        origin_node = edge[0]
        target_node = edge[1]

        edge_nodes.add(origin_node)
        edge_nodes.add(target_node)

        export_edges.append((doc_id, origin_node, target_node))

    non_existent_nodes = edge_nodes.symmetric_difference(nodes)

    for n_e_n in non_existent_nodes:
        export_edges.append((doc_id, n_e_n, n_e_n))  

    for doc_id, o_node, t_node in export_edges:
        cursor.execute('INSERT INTO docGRAPHS (doc_id, origin_node, target_node) VALUES (?,?,?)',
                    (doc_id, o_node, t_node))
    conn.commit()

def export_paragraph_structure(doc_id, result, par_ids):
    for index, paragraph_graph in enumerate(result):
        nodes = paragraph_graph.nodes.keys()
        edges = paragraph_graph.edges.keys()

        export_edges = []

        par_id = par_ids[index]
        edge_nodes = set()
        for edge in edges:
            origin_node = edge[0]
            target_node = edge[1]

            edge_nodes.add(origin_node)
            edge_nodes.add(target_node)

            export_edges.append((doc_id, par_id, origin_node, target_node))

        non_existent_nodes = edge_nodes.symmetric_difference(nodes)

        for n_e_n in non_existent_nodes:
            export_edges.append((doc_id, par_id, n_e_n, n_e_n))  

        for doc_id, par_id, o_node, t_node in export_edges:
            cursor.execute('INSERT INTO paraGRAPHS (doc_id, par_id, origin_node, target_node) VALUES (?,?,?,?)',
                        (doc_id, par_id, o_node, t_node))
        conn.commit()

for topic_num, topic in tqdm(topics):  # tqdm(topics.items()):
    query_num = str(topic_num)
    query_id = topic  # ['title']

    passage_nr = args.passage_nr
    
    fname = f'query_article_{query_num}'
    query_graph = Graph(query_id, fname, paragraph_graph_builder)
    result, par_ids = query_graph.build(**build_arguments)

    # Exporting for visuals     
    # export_paragraph_structure(query_id, result, par_ids)

    # Convert all query paragraph graphs to nx graphs
    graphs = list()
    for i in range(len(result)):
        paragraph_graph = convert_to_nx(par_ids[i], query_id, result[i]) 
        graphs.append(paragraph_graph)

    # # Create document graph
    query_graph = create_document_graph(graphs, query_id, fname, args.use_gcc)

    # export_doc_graph(query_id, query_graph)

    # recalculate node weights using TextRank
    if args.textrank:
        query_graph.rank()

    # Create new ranking.
    ranking = {}
    addition_types = {}

    # Loop over candidate documents and calculate similarity score.
    qid_docids = utils.read_docids_from_file(
        f'resources/candidates/{args.candidates}')
    for docid in qid_docids[query_num]:
        # Create graph object.
        
        fname = f'candidate_article_{query_num}_{docid}'
        candidate_graph = Graph(docid, fname, paragraph_graph_builder)
        candidate_graph.set_graph_comparator(comparator)

        candidate_result, candidate_par_ids = candidate_graph.build(**build_arguments)
        
        # Convert all candidate paragraph graphs to nx graphs
        candidate_graphs = list()
        for i in range(len(candidate_result)):
            paragraph_graph = convert_to_nx(candidate_par_ids[i], docid, candidate_result[i]) 
            candidate_graphs.append(paragraph_graph)

        candidate_document_graph = create_document_graph(candidate_graphs, docid, fname, args.use_gcc)

        # recalculate node weights using TextRank
        if args.textrank:
            candidate_document_graph.rank()

        relevance, diversity_type = candidate_document_graph.compare(
            query_graph, args.novelty, args.node_edge_l)
        ranking[docid] = relevance

        addition_types[docid] = diversity_type

    # Sort retrieved documents according to new similarity score.
    sorted_ranking = utils.normalize_dict({k: v for k, v in sorted(
        ranking.items(), key=lambda item: item[1], reverse=True)})

    # Diversify
    if args.diversify:
        nr_types = len(
            np.unique([item for sublist in addition_types.values() for item in sublist]))
        present_types = []
        to_delete_docids = []
        for key in sorted_ranking.keys():
            if len(present_types) == nr_types:
                break
            if len(addition_types[key]) > 1:
                new_types = utils.not_in_list_2(
                    addition_types[key], present_types)
                if len(new_types) > 0:
                    present_types.append([new_types[0]])
                else:
                    to_delete_docids.append(key)
            else:
                if addition_types[key] not in present_types:
                    present_types.append(addition_types[key])
                else:
                    to_delete_docids.append(key)
        for key in to_delete_docids[:85]:  # delete max 85 documents per topic.
            del sorted_ranking[key]

    # Store results in txt file.
    utils.write_to_results_file(
        sorted_ranking, query_num, args.run_tag, f'resources/output/{args.output}')

if args.year != 20:
    # Evaluate performance with trec_eval.
    os.system(
        f"/opt/anserini-tools/eval/trec_eval.9.0.4/trec_eval -c -M1000 -m map -m ndcg_cut -m P.10 resources/topics-and-qrels/{args.qrels} resources/output/{args.output}")
