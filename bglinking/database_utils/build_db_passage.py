import os
import argparse
import requests
import sqlite3
import math
import re

from bglinking.general_utils import utils
from bglinking.database_utils import db_utils
from bglinking.database_utils.create_db import create_db

from pyserini import index

from tqdm import tqdm
from collections import defaultdict
from operator import itemgetter
import numpy as np


# REL Info
IP_ADDRESS = "https://rel.cs.ru.nl/api"


def get_docids(topics: str, candidates:str, topics_only: bool) -> list:
    res_file = f'./resources/candidates/{candidates}'
    qid_docids = utils.read_docids_from_file(res_file)
    topic_docids = utils.read_topic_ids_from_file(f'./resources/topics-and-qrels/{topics}')

    if topics_only:
        return topic_docids
    else:
        return [docid for qid in qid_docids.keys() for docid in qid_docids[qid]] + topic_docids


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', dest='index',
                        default='lucene-index.core18.pos+docvectors+rawdocs_all_v3', help='Document index')
    parser.add_argument('--name', dest='name', default='default_database_name',
                        help='Database name without .db or path')
    parser.add_argument('--extractor', dest='extractor', default='rel',
                        help='Module for entity extraction (rel or spacy)')
    parser.add_argument('--candidates', dest='candidates', default='run.backgroundlinking19.bm25+rm3.topics.backgroundlinking19.txt',
                        help='File with candidates documents (ranking)')
    parser.add_argument('--topics', dest='topics', default='topics.backgroundlinking19.txt', 
                        help='Topic file')
    parser.add_argument('--topics-only', dest='topics_only', default=False, action='store_true',
                        help='Use only topic ids')
    parser.add_argument('-n', dest='n', default=100, type=int,
                        help='Number of tfidf terms to extract')
    parser.add_argument('--cut', dest='cut', default=9999999, type=int,
                        help='Cut off used to build smaller sample db.')
    parser.add_argument('--passages', dest='passages', default=3, type=int,
                        help='Number of passages to split on')
    
    args = parser.parse_args()

    # Check if database exists if not, create it:
    if not os.path.exists(f'./resources/db/{args.name}.db'):
        create_db(args.name)

    # Index Utility
    index_utils = index.IndexReader(f'./resources/Index/{args.index}')
    total_docs = index_utils.stats()['non_empty_documents']

    # Docids
    all_docids = get_docids(args.topics, args.candidates, args.topics_only)

    # Connect Database
    conn, cursor = db_utils.connect_db(f'./resources/db/{args.name}.db')

    # Loop over docids:

    pattern = re.compile(r"\. |\n")
    for docid in tqdm(all_docids[:args.cut]):
        # Extract all paragraphs from doc and store in list.

        # Extract lines using regex
        contents = list(filter(None, pattern.split(index_utils.doc_contents(docid))))
        passages = np.array_split(contents, args.passages)

        if len(passages) != 5:
            print("encountered incorrect parsing for docid: {}".format(docid))

        # Loop over passages
        for i, passage in enumerate(passages):

            # Join senteces into a single passage
            passage = ". ".join(passage)

            term_locations = defaultdict(list)
            analyzed_terms = index_utils.analyze(passage)

            # Tfidf terms
            passage_tfs = {term:analyzed_terms.count(term) for term in analyzed_terms}
            tfidf_terms = utils.create_top_n_tfidf_vector_paragraph(passage_tfs, index_utils, n=args.n, t=2.0, total_N=total_docs)

            for term in tfidf_terms.keys():
                term_locations[term].append(analyzed_terms.index(term))


            terms = [f'{term};;;{locations};;;{tfidf_terms[term]}' 
                    for term, locations in term_locations.items()]

            # Insert into sql database.
            cursor.execute('INSERT INTO entities (docid, parid, tfidf_terms) VALUES (?,?,?)',
                        (docid, i, '\n'.join(terms)))
        conn.commit()

    conn.close()
