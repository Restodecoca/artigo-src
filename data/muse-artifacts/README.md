# Artefatos de anotação Muse

Branch **privada** para validação em pares das camadas de anotação do projeto.
Ela não é uma reprodução fiel do artigo e não contém o gold manual original.

> Material restrito. Não redistribuir publicamente, não citar trechos dos
> artigos e não tratar estas labels como gold humano. Os textos continuam
> sujeitos aos direitos dos sites de origem.

## Camadas

| Camada | Arquivo | Documentos | Entidades | Status |
| --- | --- | ---: | ---: | --- |
| Muse original (silver) | `raw/vinitvek-articles-2023-muse-expanded.tar.gz` | 299 mantidos de 314 | 2.103 | `silver_pending_human_audit` |
| Overlay adjudicado | `processed/muse_corrected.tar.gz` | 299 mantidos de 314 | 5.111 | `adjudicated_overlay_not_original_manual_gold` |

Distribuição das entidades mantidas:

| Camada | IDTY | ACT | VUL | LOC |
| --- | ---: | ---: | ---: | ---: |
| Muse original | 616 | 934 | 196 | 357 |
| Overlay | 2.627 | 1.747 | 65 | 672 |

As duas camadas usam offsets de caractere zero-based e half-open, labels
`IDTY`, `ACT`, `VUL` e `LOC`, e o campo `keep` para documentos retidos ou
rejeitados. O overlay não sobrescreve a camada Muse original.

## Conteúdo da branch

- `raw/`: archive da camada Muse original.
- `processed/`: archive do overlay adjudicado.
- `manifests/`: proveniência das fontes, revisão por lote e hashes dos textos.
- `results/`: resumos agregados das validações T4 (sem texto por documento).
- `checksums.sha256`: hashes dos dois archives.

Os archives contêm pares `batch_*.json` (texto e metadados) e
`labels_batch_*.json` (spans). Ao extrair:

```text
muse_batches/vinitvek-articles-2023/          # Muse original
muse_batches/vinitvek-healthcare-corrected/   # overlay
```

## Como validar

A partir do branch `master` do repositório principal:

```bash
mkdir -p /tmp/muse/{original,overlay}
tar xzf raw/vinitvek-articles-2023-muse-expanded.tar.gz -C /tmp/muse/original
tar xzf processed/muse_corrected.tar.gz -C /tmp/muse/overlay

uv run python scripts/data/validate_muse_labels.py \
  /tmp/muse/original/muse_batches/vinitvek-articles-2023

uv run python scripts/data/validate_corrected_muse_labels.py \
  /tmp/muse/overlay/muse_batches/vinitvek-healthcare-corrected \
  /tmp/muse/overlay/muse_batches/vinitvek-healthcare-corrected
```

Resultado esperado nesta revisão:

```text
source_records=314 label_records=314 errors=0
{"records": 314, "kept": 299, "entities": 5111}
```

## Proveniência

- Fonte primária: `vinitvek/cybersecurityattacks`, revisão
  `92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b`, filtro de saúde e período
  disponível; ver `manifests/muse_manifest.json`.
- Revisão dos lotes: `manifests/muse_review_manifest.json` (1.627 documentos
  mantidos na segunda passagem) e `manifests/muse_review_empty_manifest.json`
  (quarta passagem).
- Camada Muse original: SHA-256
  `aebd0c149d1c5ac873fea47dce04acb57b8fea55f35529f5eba12b33d5db94cb`.
- Overlay: SHA-256
  `e2b3732fe64612564bc70ca95055fe9171a60d06e018578ea64bceef730b397d`.

## Limites

- O corpus original de notícias do artigo e suas anotações manuais continuam
  indisponíveis; este material é uma extensão.
- O overlay é uma adjudicação técnica, não o gold manual original.
- Os resultados em `results/` são sensibilidade e diagnóstico, não reprodução
  fiel dos números do artigo.
- Antes de qualquer publicação, consulte `DATA_AND_ARTIFACT_POLICY.md` e
  `data/SEARCH_LOG.md` no branch `master`.
