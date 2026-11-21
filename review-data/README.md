# Dados completos para revisão

Esta pasta reúne os dados necessários para o professor revisar o trabalho.
Ela contém textos integrais de notícias de terceiros e deve ser usada apenas
para avaliação acadêmica. Não redistribua estes arquivos.

## Conteúdo

| Caminho | Conteúdo |
| --- | --- |
| `archives/vinitvek-articles-2023-muse-expanded.tar.gz` | Camada inicial com textos e 2.103 entidades. |
| `archives/muse_corrected.tar.gz` | Overlay revisado com textos e 5.111 entidades. |
| `archives/muse_reviewed.tar.gz` | Revisão completa com textos e 9.318 entidades. |
| `archives/muse_consensus.tar.gz` | Referência consolidada com os textos e as três anotações. |
| `annotations/overlay_review_v1.json` | Decisões da revisão completa, com os trechos anotados. |
| `annotations/ai_assisted_additions.json` | Camada experimental de 687 adições. |
| `audits/gabriel_carlos_2026-11-20.json` | Auditoria de Gabriel Machado, 5.111 decisões. O campo histórico `reviewer` diz `Gabriel Carlos`. |
| `audits/gabriel_rodrigues_overlay_2026-11-20.json` | Projeção do overlay de Gabriel Rodrigues, 5.111 decisões. |
| `audits/comparison_2026-11-20.json` | Relatório agregado de concordância. |
| `source/36753-853-29849-1-10-20250831.md` | Artigo original usado como referência. |
| `source/healthcare_cyber_v10_hybrid_1066.csv` | Metadados da reconstrução do corpus. |

## Como abrir os archives

```bash
mkdir -p /tmp/muse/{original,overlay,reviewed,consensus}
tar xzf archives/vinitvek-articles-2023-muse-expanded.tar.gz -C /tmp/muse/original
tar xzf archives/muse_corrected.tar.gz -C /tmp/muse/overlay
tar xzf archives/muse_reviewed.tar.gz -C /tmp/muse/reviewed
tar xzf archives/muse_consensus.tar.gz -C /tmp/muse/consensus
```

Cada archive contém pares `batch_*.json` (texto e metadados) e
`labels_batch_*.json` (offsets e rótulos). Os offsets são de caractere,
zero-based e half-open.

## Validação

```bash
uv run python scripts/data/validate_muse_labels.py \
  /tmp/muse/original/muse_batches/vinitvek-articles-2023
uv run python scripts/data/validate_corrected_muse_labels.py \
  /tmp/muse/overlay/muse_batches/vinitvek-healthcare-corrected \
  /tmp/muse/overlay/muse_batches/vinitvek-healthcare-corrected
uv run python -m scripts.validation.validate_overlay_review
```

Os resultados agregados usados no artigo estão em
`data/muse-artifacts/results/`. As exportações sem texto estão em
`data/muse-artifacts/annotations/` e `data/muse-artifacts/audits/`.

## Uso e limites

Os textos pertencem aos veículos de origem. Esta pasta existe para revisão
acadêmica e não autoriza redistribuição. Antes de tornar o repositório
amplamente divulgado, os textos devem ser removidos ou o acesso deve ser
restrito aos revisores.
