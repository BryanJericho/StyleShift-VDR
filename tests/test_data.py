"""Tests for src/data.py. The first run downloads about 5 MB into data/raw/."""

import pytest

from src.data import load_dataset


@pytest.mark.parametrize("name", ["scifact", "nfcorpus"])
def test_load_dataset(name):
    corpus, queries, qrels = load_dataset(name)

    assert len(corpus) > 0 and len(queries) > 0 and len(qrels) > 0
    doc = next(iter(corpus.values()))
    assert set(doc) == {"title", "text"}

    for query_id, judged in qrels.items():
        assert query_id in queries
        for doc_id in judged:
            assert doc_id in corpus
