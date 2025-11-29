import json
import logging
import argparse
from tools.rag_retriever import upsert_chunks_to_vector_db

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Ingest JSON documents into vector DB')
    parser.add_argument('file', help='Path to JSON file containing list of docs, each with id, text, source')
    args = parser.parse_args()

    with open(args.file, 'r', encoding='utf-8') as f:
        docs = json.load(f)

    if not isinstance(docs, list):
        raise ValueError('JSON must contain a list of documents')

    upsert_chunks_to_vector_db(docs)
    logger.info('Ingested %d docs', len(docs))


if __name__ == '__main__':
    main()
