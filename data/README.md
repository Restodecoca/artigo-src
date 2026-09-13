# Local Data Contract

The original article's news corpus and manual annotations are not committed to
this repository. Store authorized local inputs under `data/raw/` or
`data/processed/`; both paths are ignored by Git.

## Annotation JSONL

Each line represents one document:

```json
{
  "document_id": "local-0001",
  "source": "SC Magazine",
  "published_date": "2023-05-01",
  "text": "local article text",
  "entities": [
    {"start": 0, "end": 12, "label": "IDTY"}
  ]
}
```

Offsets are zero-based, half-open character spans into `text`. Labels must be
one of `IDTY`, `ACT`, `VUL`, or `LOC`. The `source` field is retained so results
can be reported by portal, as in the paper.

Do not use a public substitute with this schema and call it a faithful
reproduction. Record its repository, license, access date, and deviations in
the experiment metadata.
