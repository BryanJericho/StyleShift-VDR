"""Load BEIR datasets (corpus, queries, qrels) for SciFact and NFCorpus.

Each dataset is the official BEIR zip. It is downloaded once into data/raw/, checked
against its MD5, and unzipped. Later calls reuse the files on disk.

BEIR zip layout:
    <name>/corpus.jsonl      {"_id", "title", "text", ...} per line
    <name>/queries.jsonl     {"_id", "text", ...} per line (all splits)
    <name>/qrels/test.tsv    query-id <tab> corpus-id <tab> score, with a header row
"""

import csv
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "datasets.yaml"


def load_config(path=CONFIG_PATH):
    """Read configs/datasets.yaml."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def md5_of(path):
    """Return the MD5 hex digest of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(name, url, md5, data_dir):
    """Download and unzip one BEIR dataset unless it is already on disk.

    Returns the folder that holds corpus.jsonl, queries.jsonl and qrels/.
    """
    data_dir = Path(data_dir)
    folder = data_dir / name
    zip_path = data_dir / f"{name}.zip"

    if (folder / "corpus.jsonl").exists():
        return folder

    data_dir.mkdir(parents=True, exist_ok=True)
    if not zip_path.exists():
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, zip_path)
    if md5_of(zip_path) != md5:
        zip_path.unlink()
        raise ValueError(f"MD5 mismatch for {zip_path}; file deleted, please retry.")

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(data_dir)
    return folder


def read_corpus(path):
    """Return {doc_id: {"title": str, "text": str}}."""
    corpus = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            corpus[row["_id"]] = {"title": row.get("title", ""), "text": row["text"]}
    return corpus


def read_queries(path):
    """Return {query_id: text} for every query in the file (all splits)."""
    queries = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            queries[row["_id"]] = row["text"]
    return queries


def read_qrels(path):
    """Return {query_id: {doc_id: relevance}} from a BEIR qrels tsv."""
    qrels = {}
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)  # header: query-id, corpus-id, score
        for query_id, doc_id, score in reader:
            qrels.setdefault(query_id, {})[doc_id] = int(score)
    return qrels


def load_dataset(name, config_path=CONFIG_PATH, data_dir=None):
    """Load one dataset's corpus, test queries and test qrels.

    Queries are limited to those that appear in the test qrels.
    Returns (corpus, queries, qrels).
    """
    config = load_config(config_path)
    spec = config["datasets"][name]
    if data_dir is None:
        data_dir = CONFIG_PATH.parent.parent / config["data_dir"]

    folder = download(name, spec["url"], spec["md5"], data_dir)
    corpus = read_corpus(folder / "corpus.jsonl")
    qrels = read_qrels(folder / "qrels" / f"{spec['split']}.tsv")
    all_queries = read_queries(folder / "queries.jsonl")
    queries = {qid: all_queries[qid] for qid in qrels}
    return corpus, queries, qrels


if __name__ == "__main__":
    for name in load_config()["datasets"]:
        corpus, queries, qrels = load_dataset(name)
        n_qrels = sum(len(docs) for docs in qrels.values())
        print(f"{name}: {len(corpus)} docs, {len(queries)} queries, {n_qrels} qrels")
