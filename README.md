# Background-linking
This repository is used for code to build a ranking system for finding relevant background articles for news articles and blog posts using the [TREC Washington Post Dataset](https://trec.nist.gov/data/wapost/).

As a start, [Pepijn Boers']((https://github.com/PepijnBoers/background-linking)) was used. He did previous research on this topic and the approach used in this research can be seen as a follow up for his approach. 

# Relevant changes

## Ranking changes
Below the relevant changes that were made as continuation on Pepijn Boers' code are listed:
- [build_db_paragraph.py](https://github.com/djessedirckx/ir-background-linking/blob/main/bglinking/database_utils/build_db_paragraph.py): This script is used to compute tf-idf scores on paragraph level and store them in the database.
- [build_db_passage.py](https://github.com/djessedirckx/ir-background-linking/blob/main/bglinking/database_utils/build_db_passage.py): This script is used to compute tf-idf scores on passage level and store them in the database.
- [ParagraphGraphBuilder.py](https://github.com/djessedirckx/ir-background-linking/blob/main/bglinking/graph/graph_builders/ParagraphGraphBuilder.py): This class is used to build graphs on paragraph/passage level depending on the database being used.
- [NxBuilder.py](https://github.com/djessedirckx/ir-background-linking/blob/main/bglinking/graph/graph_builders/NxBuilder.py): This module is used to connect multiple sub-graphs on document level using the NetworkX library.
- [create_top_n_tfidf_vector_paragraph()](https://github.com/djessedirckx/ir-background-linking/blob/8461dd646cb137ea20fcff417627b50766bf85b4/bglinking/general_utils/utils.py#L224): This function is used to compute tf-idf scores on either paragraph or passage level depending on the configuration being used.
- [paragraph_reranker.py](https://github.com/djessedirckx/ir-background-linking/blob/main/bglinking/paragraph_reranker.py): This script functions as an entrance file for ranking background articles using either paragraph- or passage sub-graphs depending on the configuration being used.
- [passage_importance.py](https://github.com/djessedirckx/ir-background-linking/blob/main/bglinking/passage_importance.py): This script is used to determine relevance scores for different passages of a query article.
- [paragraph_reranker_ensemble.py](https://github.com/djessedirckx/ir-background-linking/blob/main/bglinking/paragraph_reranker_ensemble.py): This script functions as an entrance file for ranking background articles using an ensemble voting method.

## Other important files
- [POC](https://github.com/djessedirckx/ir-background-linking/tree/main/POC): This directory contains POC code that was written for creating document-level graphs.
- [PowerBI](https://github.com/djessedirckx/ir-background-linking/tree/main/PowerBI): This directory contains PowerBI scripts that were used for visualizing the results obtained by this project.

# Results
- Visual [paragraph graph exploration](https://app.powerbi.com/view?r=eyJrIjoiMTYyOGJmMzItZDFjMS00MGM3LWFlNjgtYzgwNGJmYjhlNGJiIiwidCI6IjU1YmVlZWRmLTdhZmItNGI2YS1hYjU3LTBlMjYxYzI2NDJkZSIsImMiOjl9&pageName=ReportSection) (considering time constraints passage graphs were not visualized).
- [Research question results](https://app.powerbi.com/view?r=eyJrIjoiYWIyYjY1MTktM2Q1Yi00NjFkLWI1MmYtOGY4NGI4YjAwN2Q4IiwidCI6IjU1YmVlZWRmLTdhZmItNGI2YS1hYjU3LTBlMjYxYzI2NDJkZSIsImMiOjl9).

# Setup

## Docker
To be able to run the experiments more easily Docker was used. The Docker images for the respective experiments the following commands can be used.

After cloning the repository build the docker image using the dockerfile:

Background-linking on document level (using Pepijn's configuration):

```
docker build . -f docker-document -t document-linking
```

Background-linking on paragraph level
```
docker build . -f docker-paragraph -t paragraph-linking
```

Background-linking on passage level
```
docker build . -f docker-paragraph -t passage-linking
```

Passage importance
```
docker build . -f docker-passage-importance -t passage-importance
```

Ensemble voting
```
docker build . -f docker-ensemble -t ensemble-linking
```
## Resources
In order to reproduce the experiments, you need to specify the exact same resources as described below. 

- index: Index of the Washington Post Corpus (v2)
- db: Database with tf-idf scores
- topics: File with topics (TREC format)
- qrels: Query relevance file for the specified topics
- candidates: Candidate documents

### Index
TREC's [Washington Post](https://trec.nist.gov/data/wapost/) index was build using [Anserini](https://github.com/castorini/anserini), see [Regressions for TREC 2019 Background Linking](https://github.com/castorini/anserini/blob/master/docs/regressions-backgroundlinking19.md). In order to obtain the corpus, an individual agreement form has to be completed first. The exact command we used is shown below:

```
./target/appassembler/bin/IndexCollection -collection WashingtonPostCollection \
 -input /WashingtonPost.v2/data -generator WashingtonPostGenerator \
 -index lucene-index.core18.pos+docvectors+rawdocs_all \
 -threads 1 -storePositions -storeDocvectors -storeRaw -optimize -storeContents
```

The obtained index should be stored in `bglinking/resources/Index`.

### Database
A database was created to speed up the graph generation. Tf-idf terms were stored per candidate document in a database. 

- Tf-idf terms on paragraph level: [database script](https://github.com/djessedirckx/ir-background-linking/blob/main/bglinking/database_utils/build_db_paragraph.py)
- Tf-idf terms on passage level: [database](https://github.com/djessedirckx/ir-background-linking/blob/main/bglinking/database_utils/build_db_passage.py)

For creating the database, first create files called `paragraph-database.db` and `passage-database.db` in `bglinking/resources/db`. Use the following SQL script to generate the required database structure.
```sql
CREATE TABLE `entities` (
	`id`	INTEGER NOT NULL,
	`docid`	INTEGER NOT NULL,
	`parid`	INTEGER NOT NULL,
	`tfidf_terms`	TEXT NOT NULL,
	PRIMARY KEY(`id`)
);
```

The databases can be generated using the following commands
```sh
python database_utils/build_db_paragraph.py --name paragraph-database --index lucene-index.core18.pos+docvectors+rawdocs_all
```

```sh
python database_utils/build_db_passage.py --name passage-database --index lucene-index.core18.pos+docvectors+rawdocs_all --passages 5
```

### Candidates
Candidates were obtained using BM25 + RM3 via Anserini, see [Regressions for TREC 2019 Background Linking](https://github.com/castorini/anserini/blob/master/docs/regressions-backgroundlinking19.md).

The candidates file should be stored in `bglinking/resources/candidates`

### Topics and Qrels
Topics and query relevance files can be downloaded from the News Track [page](https://trec.nist.gov/data/news2019.html).

Store in `bglinking/resources/topics-and-qrels`


# Running experiments

## RQ 1

The configurations below use the full graph. Add the `--use-gcc` parameter to use the greatest connected component instead.

### Paragraph level
```
docker run --rm -v $PWD/bglinking/resources:/opt/background-linking/bglinking/resources paragraph-linking --index lucene-index.core18.pos+docvectors+rawdocs_all --db paragraph-database.db --topics topics.backgroundlinking19.txt --qrels qrels.backgroundlinking19.txt --candidates run.backgroundlinking19.bm25+rm3.topics.backgroundlinking19.txt --nr-terms 100 --text-distance 1 --output paragraph-linking.txt --run-tag paragraph-linking
```
### Passage level
```
docker run --rm -v $PWD/bglinking/resources:/opt/background-linking/bglinking/resources passage-linking --index lucene-index.core18.pos+docvectors+rawdocs_all --db passage-database.db --topics topics.backgroundlinking19.txt --qrels qrels.backgroundlinking19.txt --candidates run.backgroundlinking19.bm25+rm3.topics.backgroundlinking19.txt --nr-terms 100 --text-distance 1 --output passage-linking.txt --run-tag passage-linking
```

## RQ 2
The `--passage-nr` parameter can be changed to use a different paragraph as query article (ranges from 0-4)

```
docker run --rm -v $PWD/bglinking/resources:/opt/background-linking/bglinking/resources passage-importance --index lucene-index.core18.pos+docvectors+rawdocs_all --db passage-database.db --topics topics.backgroundlinking19.txt --qrels qrels.backgroundlinking19.txt --candidates run.backgroundlinking19.bm25+rm3.topics.backgroundlinking19.txt --nr-terms 100 --text-distance 1 --passage-nr 1 --output passage_experiment_1.txt --run-tag passage_experiment_1
```

## RQ 3

### Paragraph level
```
docker run --rm -v $PWD/bglinking/resources:/opt/background-linking/bglinking/resources ensemble-linking --index lucene-index.core18.pos+docvectors+rawdocs_all --db paragraph-database.db --topics topics.backgroundlinking19.txt --qrels qrels.backgroundlinking19.txt --candidates run.backgroundlinking19.bm25+rm3.topics.backgroundlinking19.txt --nr-terms 100 --text-distance 1 --output ensemble-paragraph-linking.txt --run-tag ensemble-paragraph-linking
```

### Passage level
```
docker run --rm -v $PWD/bglinking/resources:/opt/background-linking/bglinking/resources ensemble-linking --index lucene-index.core18.pos+docvectors+rawdocs_all --db passage-database.db --topics topics.backgroundlinking19.txt --qrels qrels.backgroundlinking19.txt --candidates run.backgroundlinking19.bm25+rm3.topics.backgroundlinking19.txt --nr-terms 100 --text-distance 1 --output ensemble-passage-linking.txt --run-tag ensemble-passage-linking
```

Results are stored in `bglinking/resources/output`

