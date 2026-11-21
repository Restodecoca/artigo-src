# Artefatos de anotação

Este diretório reúne exportações públicas, manifestos e resultados agregados
das camadas de anotação. Ele não é uma reprodução fiel do artigo e não contém o
gold manual original.

## Camadas

| Camada | Exportação pública | Documentos | Entidades |
| --- | --- | ---: | ---: |
| Muse original (silver) | resultados e manifestos | 299 | 2.103 |
| Overlay adjudicado | `audits/` e `annotations/` | 299 | 5.111 |
| Revisão completa | `annotations/overlay_review_v1.json` | 299 | 9.318 |
| Referência consolidada | resultados agregados | 299 | 9.318 |

As exportações públicas usam offsets de caractere zero-based e half-open,
labels `IDTY`, `ACT`, `VUL` e `LOC`, e não incluem o campo `text`. Os archives
com textos estão em `review-data/` para a revisão acadêmica.

## Conteúdo

- `annotations/`: decisões de revisão e camada experimental, sem textos.
- `audits/`: exportações de auditoria sem notas livres e relatório agregado.
- `manifests/`: proveniência, filtros e hashes dos textos.
- `results/`: resumos agregados das validações T4.
- `checksums.sha256`: hashes dos archives completos em `review-data/archives/`.

## Proveniência

- Fonte primária: `vinitvek/cybersecurityattacks`, revisão
  `92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b`, filtro de saúde e período
  disponível; ver `manifests/muse_manifest.json`.
- Camada Muse original: SHA-256
  `aebd0c149d1c5ac873fea47dce04acb57b8fea55f35529f5eba12b33d5db94cb`.
- Overlay: SHA-256
  `e2b3732fe64612564bc70ca95055fe9171a60d06e018578ea64bceef730b397d`.

## Limites

- O corpus original de notícias do artigo e suas anotações manuais continuam
  indisponíveis.
- O overlay é uma adjudicação técnica, não o gold manual original.
- Os resultados em `results/` são análises de sensibilidade, não reprodução
  fiel dos números do artigo.
- Consulte `PUBLIC_RELEASE.md`, `DATA_AND_ARTIFACT_POLICY.md` e
  `review-data/README.md`.
