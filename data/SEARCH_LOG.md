# Corpus Search Log

Status as of 2026-08-23: the original healthcare-news corpus and its manual
annotations were not found in a public repository. The reproduction status
therefore remains `approximate` until an authorized copy is obtained.

## Direct sources checked

| Source | Query or endpoint | Result |
| --- | --- | --- |
| GitHub | `https://api.github.com/users/rafaapaim/repos?per_page=100` | 37 public repositories; none concerns the paper, SecureBERT/APTNER, healthcare-news NER, or the reported SQLite corpus. |
| GitHub | `https://api.github.com/users/rafaapaim/gists?per_page=100` | No relevant public gist found. |
| Hugging Face models | `https://huggingface.co/api/models?search=SecureBERT&limit=100` | Model checkpoints were found, including the two evaluated models, but no paper corpus. |
| Hugging Face datasets | `https://huggingface.co/api/datasets?search=healthcare%20cybersecurity&limit=100` | No matching dataset returned. |
| Hugging Face datasets | `https://huggingface.co/api/datasets?search=cybersecurity%20news&limit=100` | Returned unrelated Russian Telegram data and 2025-2026 news metadata; no equivalent 2023 healthcare corpus or manual labels. |
| Kaggle | searches for `SecureBERT`, `healthcare cybersecurity news`, and `cybersecurity incident healthcare` | Returned unrelated fine-tuning, log, CVE, ransomware, and global-threat datasets. |
| Kaggle | `chuneeb/healthcare-cybersecurity-vulnerabilities-dataset` | 1,515 NVD CVE records about healthcare vulnerabilities; not news articles and not the paper's entity annotations. |
| Zenodo | `SecureBERT` and `healthcare cybersecurity news` API searches | Requests returned HTTP 504, so these checks are inconclusive rather than evidence of absence. |

## First ten article access probe

Status as of 2026-09-12: all ten canonical Becker's URLs in
`healthcare_cyber_v10_hybrid_1066.csv` returned HTTP 403 when fetched directly.
The `r.jina.ai` reader returned article body text for CSV positions 1, 3, 4,
and 6. Positions 2, 5, 7, 8, 9, and 10 returned CAPTCHA or empty-content
warnings. This confirms that the links are real article candidates, but access
is not reliable enough to treat the ten URLs as a ready-to-evaluate corpus.

The accessible articles still have no manual entity annotations. They may be
used only as authorized inputs for a separately documented annotation sample;
otherwise the project needs the original SQLite/annotation package or a
licensed public dataset for model evaluation.

The protocol-aligned reconstruction file contains 1,066 metadata records, but
it also includes HHS OCR Breach Portal, HIPAA Journal, and 2026 records that
are outside the paper's selected-portal protocol. Restricting it to the three
reported portals and the paper's 2023 period yields 689 records: 518 Becker's
Hospital Review, 149 JD Supra, and 22 Security Magazine. This is enough for a
deterministic 20-document-per-portal sample, subject to successful full-text
retrieval. The file is a reconstruction candidate, not evidence that these are
the unavailable original 1,039 records.

On 2026-09-13, a protocol-aligned local sample was fetched through the Jina
Reader endpoint from the reconstructed URLs. The private ignored artifact
`data/raw/protocol_60_texts.jsonl` contains 60 unique truncated article-text
records: 20
from each of Security Magazine, Becker's Hospital Review, and JD Supra. Text
was normalized to remove the configured reader-navigation markers and
truncated to the first 400 whitespace-delimited tokens. Structural validation
found 60 non-empty records, 60 unique URLs, and no residual CAPTCHA,
page-not-found, or configured navigation marker. Publisher boilerplate may
remain and must be reviewed before treating the texts as annotation material.
Eleven candidate URLs were skipped during retrieval: 10 were blocked or
rate-limited by the reader/source, and one produced an extracted body that was
too short;
the selector continued to later records within the same portal to preserve the
20-per-portal allocation. The matching metadata is in
`data/raw/protocol_60_metadata.json`; these files are not committed or
published. The 60 texts still have no gold spans and must be manually reviewed
before any Strict/Partial score is reported.

## Hugging Face dataset probe

Status as of 2026-09-12: the Hugging Face `hf` extra was already present in
`pyproject.toml` (`datasets` and `huggingface-hub`), so no dependency change was
needed. The following public datasets were loaded and inspected locally:

| Repository | Verified structure | Decision |
| --- | --- | --- |
| `mrmoor/cyber-threat-intelligence` | Revision `d8783e04f46039f3624df6958dd4d34405d8c72a`; 9,732 examples; full `text`; character-level `entities`; CC-BY-4.0; 20 labels | Best immediate external-validation candidate. Map `identity`, `attack-pattern`, `vulnerability`, and `location` to `IDTY`, `ACT`, `VUL`, and `LOC`; the project normalizer discards the other labels. |
| `bnsapa/cybersecurity-ner` | 2,664 train, 717 test, 785 validation; token sequences; 5 entity classes; Apache-2.0 | Useful smoke-test data, but lacks the paper's `ACT` and `LOC` label pair and does not preserve full text directly. |
| `chairulridjal/arcspan-cyber-ner` | 50,597 train, 5,642 validation, 4,973 test; character spans; Apache-2.0; mixed CTI sources | Strong technical NER benchmark, but its five-class taxonomy differs and includes APTNER/SecureBERT-related material, so it is not the cleanest evaluation set for these checkpoints. |
| `priamai/AnnoCTR` | 400 annotated CTI reports; 23 tags; CC-BY-SA-4.0; custom loader | Relevant but less reproducible locally because it relies on a remote dataset script and has a broader taxonomy. |

The selected dataset remains `reference_only`: it supports an `extension` or
external-validation experiment, not a faithful reproduction of the healthcare
news paper. Do not publish downloaded text or per-document outputs; follow
`DATA_AND_ARTIFACT_POLICY.md`.

## Quantitative benchmark decision

The project scope explicitly permits a reliable substitute rather than the
paper's unavailable exact corpus. Therefore `mrmoor/cyber-threat-intelligence`
is the primary quantitative benchmark for model scoring: its pinned revision is
CC-BY-4.0, it retains full text and character-level spans, and its
`identity`, `attack-pattern`, `vulnerability`, and `location` labels map
directly to `IDTY`, `ACT`, `VUL`, and `LOC`. The 60-document three-portal sample
remains the healthcare-focused extension for qualitative analysis and future
manual annotation; it is not required to unblock quantitative SecureBERT
results.

The previously executed three-seed external-validation run on 60 eligible
`mrmoor` records produced the following aggregate extension results:

| Model | Strict F1 mean +/- population SD | Partial F1 mean +/- population SD |
| --- | ---: | ---: |
| SecureBERT-NER | 0.161 +/- 0.029 | 0.262 +/- 0.023 |
| SecureBERT-APTNER | 0.155 +/- 0.024 | 0.291 +/- 0.024 |

These are valid substitute-dataset measurements with gold spans, not a claim
that the paper's 60 healthcare articles were recovered.

## Closest healthcare incident candidate

Status as of 2026-09-12: `vinitvek/cybersecurityattacks` was loaded from pinned
revision `92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b`. Its README declares the
`Unlicense`. The train split contains 13,407 records with `event_date`,
`affected_organization`, `affected_industry`, `description`, and `source_url`
fields. The descriptions are short incident summaries rather than complete
news articles, and the dataset has no manual NER spans.

Using the reproducible provisional healthcare filter
`"health" in affected_industry.lower()` or `"hospital"`/`"medical"` in
`affected_organization.lower()` yields 1,852 records. Restricting
`event_date` to the protocol's `2023-01-01` through `2023-10-30` interval yields
367 records. This is currently the closest public candidate for building a new
60-document annotation sample because it matches the domain and collection
period better than the generic CTI extension, while retaining source URLs for
provenance checks.

This candidate is registered as `reference_only`, not as the original corpus and
not as an already annotated evaluation set. The next valid use is to deduplicate
and manually annotate a documented 60-record sample with the paper's `IDTY`,
`ACT`, `VUL`, and `LOC` labels. Do not run model scoring on it before that
annotation exists.

## 100-document annotation pilot

Status as of 2026-09-12: a subagent created a local pilot annotation from the
first 100 deterministic records selected from the 367 healthcare-filtered
records in the protocol period. The local files are ignored under `data/raw/`:
`vinitvek_healthcare_100_annotated.jsonl` and
`vinitvek_healthcare_100_metadata.json`.

The pilot uses the `description` field rather than fetching source articles and
uses zero-based, half-open, flat character spans for `IDTY`, `ACT`, `VUL`, and
`LOC`. Final counts are `ACT=190`, `IDTY=132`, `LOC=17`, and `VUL=6`; no document
has zero entities. Independent structural and semantic review found no remaining
findings. The selection reproduces exactly against dataset revision
`92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b`.

This is an `extension` pilot, not the paper's original gold set. Seven duplicate
URL entries occur across five URL values, so the 100 rows are not 100 independent
source URLs. Visible encoding and spelling anomalies are retained in the local
text and recorded in the metadata. The local raw text and per-document
annotations must not be committed or published.

Other inspected candidates were rejected for this protocol:
`gunnybd01/Healthcare_News` is financial-market news rather than healthcare
incident reports; `ScortonAI/Cyber-Security-Breaches` is a historical healthcare
breach table with no cybersecurity-news NER labels; and
`threatcluster/ransomware-leak-site-victims` contains current tabular victim
claims without article text.

## Five-candidate proximity triage

Status as of 2026-09-12: five additional public or publicly described candidates
were checked against the target requirements: full text, cybersecurity incident
content, healthcare relevance, NER annotations, and usable redistribution terms.

| Candidate | Evidence checked | Decision |
| --- | --- | --- |
| AI4HEALTHSEC / SoBigData `the_hackernews_dataset` | The project paper reports 6,774 normalized full-text Hacker News articles, with 918 NER-training and 84 NER-test articles. Its NER labels cover `Asset`/`Threat`, with a separate `Asset`/`Vulnerability`/`Adjectives` setup. The catalogue entry is `https://data.d4science.org/ctlg/ResourceCatalogue/the_hackernews_dataset`; the current endpoint exposed the catalogue shell but not a downloadable file. | Closest corpus-quality and annotation candidate; not healthcare-only, labels do not match, and access is currently unverified. |
| `OhWayTee/Cybersecurity-News_3` / Mendeley `10.17632/n7ntwwrtn5.1` | 3,742 full article rows from The Hacker News, four classification labels, and 171 rows containing healthcare-related keywords in a streaming inspection. Mendeley declares CC-BY-4.0. | Full text and permissive license, but no NER spans and healthcare is incidental. |
| `upb-nlp/NtVR_public` | 923 annotated cybersecurity news records with spans and 9 labels; healthcare-related titles were present, including medical-device and healthcare vulnerability stories. The public rows expose title/URL/spans but not article text, so offsets cannot be evaluated against retained text. | Annotated but unusable as a self-contained corpus and not healthcare-specific. |
| `boutdatansec/YACSDB` | Public GitHub JSONL/IOB2 release with 422 cybersecurity reports and 24,878 sentences, character spans, and STIX-oriented labels. | Strong general CTI NER resource, but APT reports rather than healthcare news and taxonomy differs. |
| `AttackER` (`arXiv:2408.05149`) | Paper reports 217 attack-attribution documents, 18 entity classes, two expert annotators, and 85.83% average partial agreement on 321 sentences. | High-quality general cyber NER candidate, but no healthcare focus and no directly verified corpus repository in this search. |

The AI4HEALTHSEC/SoBigData resource is the first candidate found that is
similar in corpus scale, full-text structure, and annotated NER design. It is
still an `extension` candidate, not an equivalent replacement for the paper's
1,039 healthcare-news corpus and four labels. The current healthcare-domain
candidate remains `vinitvek/cybersecurityattacks`; it is more domain-aligned but
contains summaries and requires annotation.

Follow-up access check: the catalogue page is reachable at
`https://data.d4science.org/ctlg/ResourceCatalogue/the_hackernews_dataset`, but
the D4Science data API requires an authenticated Bearer token and returned HTTP
`401` without one. No dataset file, revision, or redistribution licence could
therefore be verified locally. A token must be obtained through the platform's
normal account flow; it should not be pasted into this repository or chat.

## Local full-text file supplied

Status as of 2026-09-12: the local file
`C:\Users\gabri\Downloads\dataset_cybersecurity.csv` was parsed without
publishing or copying its raw contents. It is a valid pipe-delimited,
multiline-quoted file with exactly two columns per record (`id` and `text`),
4,528 sequential records (`1` through `4528`), 13,951,371 total text
characters, and approximately 2,097,640 whitespace-delimited words. The
content matches The Hacker News article corpus style; an exact probe of the
first article resolves to a March 24, 2022 Hacker News article.

This file is a useful local full-text extension, but it is not the verified
AI4HEALTHSEC/SoBigData release: it contains no annotation column or entity
spans, its provenance and redistribution licence are not established, and its
4,528 records do not match the 6,774-article count reported by the
AI4HEALTHSEC paper. A keyword probe found 197 records containing `healthcare`,
so healthcare relevance is incidental rather than a documented corpus filter.
It can support a separately labeled annotation pilot only after the local
access and licence conditions are recorded; it must not be treated as the
paper's gold set.

Smoke inference on the deterministic 60-document healthcare-keyword sample
was executed locally on CPU using the pinned checkpoints from the protocol.
The sample is the first 60 records in source order whose case-insensitive text
contains at least one of `healthcare`, `hospital`, `medical device`, `patient`,
`clinic`, `pharma`, or `health system`. The parser and selector are implemented
in `src/healthcare_ner_replication/local_corpus.py`; the repeatable inference
entry point is `scripts/run_local_securebert_smoke.py`:

```text
uv run --extra models --with torch --with transformers python scripts/run_local_securebert_smoke.py C:\Users\gabri\Downloads\dataset_cybersecurity.csv --limit 60
```

The command prints aggregate metrics only and does not write source text or
per-document predictions.

The source-file SHA-256 is
`3a5a97d477234c2dcbe0c0f9295cc3a92eca849171128a13d01ada0d8fad73ba` and the
sample ID SHA-256 is
`9a941695caf61ad57587aa2ece692402f43fc164af293a93a8caeac56904108e`.

| Checkpoint | Target entities after mapping | Documents with target entities | Target label counts (`IDTY`, `ACT`, `VUL`, `LOC`) |
| --- | ---: | ---: | --- |
| `CyberPeace-Institute/SecureBERT-NER` | 1,229 | 60 | 365, 216, 336, 312 |
| `Cyber-ThreaD/SecureBERT-APTNER` | 1,052 | 58 | 480, 237, 68, 267 |

The symmetric agreement between the two prediction sets was `strict F1=0.3069`
and overlap-based `partial F1=0.5445`; these are agreement diagnostics, not
precision, recall, or reproduction scores. The run used the Transformers
pipeline defaults rather than the paper's 400-token evaluation limit, and no
gold spans were available. The local file is therefore usable for an
inference smoke test, but a valid 60-document model evaluation still requires
independent manual spans.

## Colab external-validation probe

Status as of 2026-09-12: SecureBERT-NER and SecureBERT-APTNER were executed on
a Colab Tesla T4 using 60 deterministic examples from the 2,642-row candidate
pool in the pinned train split at seeds 42, 123, and 2024. The runtime was
Python 3.13.15, PyTorch 2.11.0+cu128, Transformers 4.57.6, and `datasets`
4.8.5. The paper's 400-token limit was not applied, so these results are an
`extension`, not a reproduction. Each sample is identified in its JSON artifact
by a SHA-256 digest of selected dataset row IDs without storing those IDs. The
token-level postprocessor handles both BIO and BIOES output before scoring.

| Model | Strict F1 mean +/- population SD | Partial F1 mean +/- population SD |
| --- | ---: | ---: |
| SecureBERT-NER | 0.161 +/- 0.029 | 0.262 +/- 0.023 |
| SecureBERT-APTNER | 0.155 +/- 0.024 | 0.291 +/- 0.024 |

Aggregate JSON results are stored in `data/external_validation_securebert_seed42.json`,
`data/external_validation_securebert_seed123.json`, and
`data/external_validation_securebert_seed2024.json`. They contain no source
article text or per-document predictions. The Colab T4 session was stopped
after the runs.

## Rejected substitutes

The following sources must not be used as the original corpus:

- `chuneeb/healthcare-cybersecurity-vulnerabilities-dataset`: NVD CVE records;
- `rivalytics/healthcare-ransomware-dataset`: a separate ransomware dataset;
- `atharvasoundankar/global-cybersecurity-threats-2015-2024`: global incident data;
- `OhWayTee/Cybersecurity-News` and related datasets: general cybersecurity news;
- `ScoutieAutoML/cybersecurity_news_telegram_dataset`: Russian Telegram data;
- `olgazigbeehub/cybersecurity-news-dataset-english-3000`: 2025-2026 metadata;
- `kaleabbelayhun3/securebert-finetune`: model fine-tuning data of unknown scope.

The existing Hugging Face candidates in `src/healthcare_ner_replication/data_sources.py`
remain `reference_only` for smoke tests or external validation.

## Reproduction consequence

The paper reports a local SQLite collection and does not publish the complete
corpus, manual annotations, or a public code/data supplement. Without those
artifacts, scores on any public substitute must be reported as `approximate` or
`extension`, with the source license, access date, filtering, and label mapping
recorded separately.

## Next authorized path

1. Ask the authors or the venue for the SQLite corpus and 60-document manual
   annotation sample.
2. If access is granted, store only authorized local inputs under `data/raw/`
   and record the access conditions in experiment metadata.
3. Otherwise, run a separately labeled external-validation experiment using a
   documented public dataset; do not compare its metrics as if they reproduced
   the paper.

## Manual-annotation candidates

Status as of 2026-09-13: the search was widened to include public datasets with
usable healthcare or cybersecurity text but no gold NER spans. These are valid
inputs for a separately documented manual-annotation study. They are not the
paper's corpus and must not be scored before annotation and structural review.

### Hugging Face

| Repository | Verified structure | License/access | Decision |
| --- | --- | --- | --- |
| `vinitvek/cybersecurityattacks` | 13,407 incident summaries with `description`, organization/industry metadata, dates, and source URLs; a reproducible healthcare filter yields 1,852 records, including 367 in the paper's 2023 collection interval. | Unlicense; pinned revision `92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b`. | **P1**. Best domain-aligned starting point; descriptions are summaries, not full articles. |
| `ScortonAI/Cyber-Security-Breaches` | 1,055 records with `Summary`, entity, breach type, location, and dates; non-empty summaries are directly annotatable. Some records have null summaries. Includes healthcare breach records but also theft, loss, and mis-mailing. | MIT; pinned revision `1da6a89a887067a29fa536441d3f32dce0a5879c`. | **P1**. Strong healthcare-breach candidate, but broader than cybersecurity incidents. |
| `gvic-unb/public-health-news-DF-qa` | 1,688 Portuguese public-health news articles in the `knowledge_base` configuration with `title`, `content`, and URL. | CC-BY-4.0; pinned revision `9944e31a41e6cc1f3ed484b5d95cca363e6dc5ac`. | **P2**. Useful if Portuguese annotation is acceptable; cybersecurity relevance is incidental. |
| `kienlc1/all_medical_news` | 73,714 medical-web records with `title`, `content`, URL, and tags. | No license declared in the dataset metadata. | **P3**. Large text pool, but provenance, duplication, language, and reuse rights require separate review. |
| `ScoutieAutoML/medical_news_dataset` | Russian medical-news text from 30 Telegram channels; the existing `ners` field is automatically generated and should be treated only as noisy preannotation. | No license declared in the dataset metadata. | **P3**. Not suitable for primary evaluation without language and licensing review. |

### Kaggle

| Dataset | Verified structure | License/access | Decision |
| --- | --- | --- | --- |
| `thedevastator/major-us-health-data-breaches` | More than 860 US health-breach records from 2009--2019; `Web Description` contains incident text alongside entity, breach type, and location fields. | Kaggle version 2, accessed 2026-09-13: [dataset](https://www.kaggle.com/datasets/thedevastator/major-us-health-data-breaches). Kaggle lists data files as copyright by original authors; the card links CC-BY-4.0 and the upstream data.world source. | **P1**. Best Kaggle candidate for healthcare incident annotation after rights verification; older and not limited to cyberattacks. |
| `darkmatternet/sec-cybersecurity-disclosures-incidents` | 80 SEC 8-K/8-KA filings from 55 registrants with extracted Item 1.05 incident text and source links. | Kaggle version 2, accessed 2026-09-13: [dataset](https://www.kaggle.com/datasets/darkmatternet/sec-cybersecurity-disclosures-incidents). Kaggle says “Other”; extracted text remains subject to SEC registrants' rights. | **P1/P2**. High-quality narrative text; first filter registrants for healthcare, pharma, and medtech before annotation. |
| `chuneeb/healthcare-cybersecurity-vulnerabilities-dataset` | 1,515 NVD CVE records with `Description`, `Reference`, and medical-device/EHR keyword fields. | Kaggle version 1, accessed 2026-09-13: [dataset](https://www.kaggle.com/datasets/chuneeb/healthcare-cybersecurity-vulnerabilities-dataset). CC0/Public Domain; sourced from NVD. | **P2**. Good for `VUL`, product, and organization annotation; CVE summaries are not news articles. |
| `joebeachcapital/ransomware-attacks` | Approximately 360 structured ransomware incidents with organization, sector, descriptions, and notes; includes hospital and healthcare cases. | Kaggle version 1, accessed 2026-09-13: [dataset](https://www.kaggle.com/datasets/joebeachcapital/ransomware-attacks). Kaggle declares `Database: Open Database, Contents: Database Contents`; rights and work-in-progress status still require review. | **P2**. Useful small seed set, but sparse narrative text and incomplete cleaning. |

The immediate annotation shortlist is therefore `vinitvek/cybersecurityattacks`
plus `ScortonAI/Cyber-Security-Breaches`, with
`thedevastator/major-us-health-data-breaches` as the strongest independent
healthcare-breach comparison. A practical manual sample should preserve the
source identifier, source URL where available, dataset revision/version, and
the exact text used for annotation. The four paper labels remain `IDTY`, `ACT`,
`VUL`, and `LOC`; empty spans are allowed, but every selected document must be
reviewed for text quality before annotation.

## T4 candidate probe

Status as of 2026-09-13: the first five non-empty source-order records of three
Hugging Face candidates were executed on a Colab Tesla T4 using the pinned
SecureBERT revisions. The runner is `scripts/run_colab_candidate_probe.py` and
stores only aggregate sample length/fingerprint metadata and model counts. It
does not store raw text, spans, or per-document predictions. Runtime versions
were Python 3.13.15, PyTorch 2.11.0+cu128, Transformers 4.57.6, and Datasets
4.8.5.

| Candidate | Mean chars / words | SecureBERT-NER | SecureBERT-APTNER | Interpretation |
| --- | ---: | --- | --- | --- |
| `vinitvek/cybersecurityattacks` (`description`) | 198.6 / 28.8 | 24 target entities in 4/5 records: `IDTY=17`, `ACT=2`, `LOC=5` | 7 in 5/5: `IDTY=4`, `ACT=1`, `LOC=2` | Best immediate candidate for the target domain and period; descriptions are short incident summaries and still need manual review. |
| `ScortonAI/Cyber-Security-Breaches` (`Summary`) | 823.6 / 124.8 | 10 in 3/5: `IDTY=10` | 0 in 0/5 | Better text length and healthcare-breach focus, but mixed breach types and weak initial model coverage. |
| `gvic-unb/public-health-news-DF-qa` (`knowledge_base.content`) | 3,135 / 497.6 | 5 in 1/5: `IDTY=5` | 0 in 0/5 | Full news-like text, but Portuguese public-health content is not cybersecurity-focused; keep as a language/domain stress test, not primary candidate. |

The probe is a feasibility diagnostic, not a quality ranking and not an
evaluation: prediction counts cannot replace manual spans. The recommended
next annotation order is `vinitvek` first, `ScortonAI` second, and Kaggle
health-breach data only after downloading and reviewing its current version and
rights. The aggregate outputs are stored in
`data/external_candidate_probe_vinitvek_t4.json`,
`data/external_candidate_probe_scorton_t4.json`, and
`data/external_candidate_probe_gvic_t4.json`.

## Mature T4 candidate benchmark

Status as of 2026-09-13: a larger no-gold-span benchmark was run through the
WSL Colab CLI on one Tesla T4. The benchmark used 100 deterministic documents
per candidate, seed `20260913`, dataset revisions pinned above, and both pinned
SecureBERT checkpoints. The Colab runtime reported Python 3.13.15 and PyTorch
2.11.0+cu128; Transformers 4.57.6 and Datasets 4.8.5 match the repository
constraints. Python and the CUDA PyTorch wheel are recorded runtime metadata,
not lockfile entries.

Sampling protocol:

- `vinitvek/cybersecurityattacks`: healthcare filter plus the inclusive
  `2023-01-01`--`2023-10-30` period, exact deduplication by `source_url`; 367
  eligible rows reduced to 329 unique URLs, then 100 were selected.
- `ScortonAI/Cyber-Security-Breaches`: non-empty `Summary`, deduplicated by the
  composite `Name_of_Covered_Entity` + `Date_of_Breach` identity; only 142
  records were usable, so 100 were selected. This remains a broad
  healthcare-breach sample, not a cyber-only sample.
- `gvic-unb/public-health-news-DF-qa`: `knowledge_base/corpus`, all non-empty
  `content`; 100 of 1,688 articles were selected as a Portuguese healthcare
  text stress test, not as a cybersecurity corpus.

| Candidate | Length / overflow | NER behavior | APTNER behavior | Concordance diagnostic |
| --- | --- | --- | --- | --- |
| `vinitvek/cybersecurityattacks` | Median 24 words; 0/100 over 512 tokens; 0 failures. | 255 entities, 77/100 non-empty, 10.93 entities/100 words, labels `IDTY=167`, `VUL=48`, `ACT=22`, `LOC=18`; mean uncalibrated score 0.7970. | 249 entities, 81/100 non-empty, 10.67/100 words, labels `IDTY=181`, `VUL=10`, `ACT=36`, `LOC=22`; mean uncalibrated score 0.4854. | Typed concordance F1 0.2105; empty/non-empty agreement 0.86. |
| `ScortonAI/Cyber-Security-Breaches` | Median 119 words; 1/100 over 512 tokens; 0 failures. | 210 entities, 67/100 non-empty, 1.60/100 words; mostly `IDTY=199`; mean uncalibrated score 0.6185. | 112 entities, 36/100 non-empty, 0.85/100 words; `IDTY=109`, `LOC=3`; mean uncalibrated score 0.4216. | Typed concordance F1 0.2826; empty/non-empty agreement 0.57. |
| `gvic-unb/public-health-news-DF-qa` | Median 467.5 words; 98/100 over 512 tokens; 0 failures, but all 80,413 excess tokens were discarded under the pipeline's default single-window truncation behavior before inference. | 120 entities, 34/100 non-empty, 0.23/100 words; `IDTY=113`, `VUL=6`, `LOC=1`; mean uncalibrated score 0.6360. | 3 entities, 3/100 non-empty, 0.01/100 words; `LOC=2`, `VUL=1`; mean uncalibrated score 0.3026. | Typed concordance F1 0.6529, driven largely by both models returning empty output; not evidence of quality. |

These concordance values compare model outputs with each other and are not
precision, recall, F1 against a gold standard, or evidence that either model is
correct. The score fields are uncalibrated model scores. The mature benchmark
supports the following selection decision:

1. Use `vinitvek/cybersecurityattacks` as the primary manual-annotation
   candidate: it is aligned with healthcare cybersecurity and the paper's date
   range, has no overflow in the 100-document sample, and activates both
   models across all four target labels.
2. Keep `ScortonAI/Cyber-Security-Breaches` as a secondary healthcare-breach
   candidate: its summaries are substantially longer, but the usable pool is
   small and includes non-cyber breach types.
3. Do not use `gvic-unb/public-health-news-DF-qa` as the primary candidate
   without a separate sliding-window protocol and a cybersecurity filter; its
   current output is a language/length stress test only.

The benchmark runner is `scripts/run_colab_candidate_benchmark.py`. It stores
only aggregate sampling, length, runtime, model-output, and concordance
diagnostics, including one aggregate SHA-256 digest per selected sample. The
aggregate artifacts are
`data/candidate_benchmark_vinitvek_t4.json`,
`data/candidate_benchmark_scorton_t4.json`, and
`data/candidate_benchmark_gvic_t4.json`.
