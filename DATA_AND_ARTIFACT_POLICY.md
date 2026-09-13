# Data and Artifact Policy

## Public repository

The repository may contain source code, tests, configuration, documentation,
dataset metadata, model identifiers, synthetic fixtures, and aggregate results.

## Restricted material

Do not commit or publish:

- scraped article text or full news dumps;
- manual annotations that reproduce protected article content;
- model caches, checkpoints, or generated outputs without review;
- API keys, Kaggle tokens, Hugging Face tokens, or `.env` files;
- per-document results that can reconstruct or identify source articles.

## Reproduction states

Every experiment must label itself as `faithful`, `approximate`, or `extension`.
The public Hugging Face candidates currently registered in the project are
`reference_only`; they do not contain the original healthcare-news corpus.

## Publication gate

Before presenting publication claims, the project must record:

1. data source, license, access date, and permitted redistribution;
2. exact model revisions and dependency versions;
3. annotation procedure and inter-annotator agreement;
4. document-level and entity-level metrics with uncertainty estimates;
5. all deviations from the original paper;
6. a review of leakage, duplicates, dead links, and sensitive content.
