# StyleShift-VDR

Code for studying **presentation sensitivity and style bias in visual document retrievers**.

We render the same text documents in several visual styles (fonts, sizes, colours, layouts)
with byte-identical words, then measure:

1. **Invariance** — do retrieval scores and rankings change when only the style changes?
2. **Style bias** — in a mixed-style corpus, are some styles retrieved more often than their
   share of the corpus, regardless of relevance?
3. **Factors** — which visual factor drives the effect, controlling for OCR readability?
4. **Training-free fixes** — score normalisation and fusion with OCR + BM25.

> **Status:** work in progress. No results are published here yet.

## Setup

Coming soon.

## License

Code is released under the [MIT License](LICENSE).
