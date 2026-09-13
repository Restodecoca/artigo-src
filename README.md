# Healthcare Cybersecurity NER Reproduction

Reproduction and extension of **An Analysis of Pre-trained Models to Identify
Cybersecurity Incidents Entities in the Healthcare Industry** by Rafael Paim and
Luciano Ignaczak.

The project starts from the paper's reported protocol and keeps an explicit
boundary between faithful reproduction and external validation. Public datasets
found on Hugging Face are reference material only; none is silently treated as
the paper's original healthcare-news corpus.

## Current Protocol

- Models: `SecureBERT-NER` and `SecureBERT-APTNER`.
- Public checkpoints: `CyberPeace-Institute/SecureBERT-NER` and
  `Cyber-ThreaD/SecureBERT-APTNER`.
- Shared entity types: `IDTY`, `ACT`, `VUL`, and `LOC`.
- Evaluation modes: strict and partial matching.
- Reported collection: `24,108` records, reduced to a final corpus of `1,039`.
- Manual evaluation: `60` news articles, truncated to the first `400` tokens.
- Collection date: `2023-10-30`, covering `2023-01-01` through `2023-10-30`.

The machine-readable protocol is in `configs/reproduction.toml`. The Python
guardrails are in `src/healthcare_ner_replication/protocol.py`.
Model-specific label conversion is explicit in
`src/healthcare_ner_replication/inference.py`: `VULID` and `VULNAME` are mapped
to the paper's aggregate `VUL` type.

The public-source audit is recorded in `data/SEARCH_LOG.md`. It found no
authorized copy of the original corpus; the listed public datasets remain
reference material only.

## Reproduction Boundary

The original article does not provide the complete corpus, manual annotations,
all model revisions, or every preprocessing detail. Therefore the project will
report one of these states for every result:

- `faithful`: original corpus and annotations verified;
- `approximate`: public substitute used, with all deviations documented;
- `extension`: new data, annotation, model, or evaluation protocol.

The canonical status names are defined in the configuration file as `faithful`,
`approximate`, and `extension`.

## Data Safety

Do not commit source news dumps, annotations containing copied article text,
credentials, model caches, or generated artifacts. See
`DATA_AND_ARTIFACT_POLICY.md` before downloading data.

The Kaggle token previously pasted in chat must be revoked and regenerated. It
is not stored in this repository and is not required for the current Hugging
Face-first workflow.

## Development

```powershell
uv sync --extra dev
uv run pytest -q
uv run ruff check .
```

Model and dataset dependencies are intentionally optional until the corpus and
hardware path are confirmed:

```powershell
uv sync --extra hf --extra models --extra dev
```

## AMD ROCm

The available ROCm environment is outside this repository at
`C:\rocm-rf01\RCOm-windows-gfx1030`. Its nightly Python environment detected an
AMD Radeon RX 6600M and passed a tensor and memory test. Use that environment
for model inference only after the CPU tests pass here:

```powershell
& 'C:\rocm-rf01\RCOm-windows-gfx1030\.venv-nightly\Scripts\python.exe' `
  'C:\rocm-rf01\RCOm-windows-gfx1030\scripts\test-gpu.py'
```

The project does not copy ROCm wheels into its lockfile. This keeps the
reproduction environment separate from the hardware-specific runtime.
