# Revisão pública dos artefatos de anotação

Este repositório público contém código, documentação, resultados agregados,
exportações de anotação sem os textos integrais e um pacote separado com os
dados completos para revisão acadêmica.

## Exportações sem texto

- `annotations/overlay_review_v1.json`: decisões da revisão completa do overlay,
  com identificadores, offsets e rótulos, sem o campo `text`.
- `annotations/ai_assisted_additions.json`: camada experimental de adições,
  sem o campo `text`.
- `audits/gabriel_carlos_2026-11-20.json` e
  `audits/gabriel_rodrigues_overlay_2026-11-20.json`: decisões de auditoria,
  com identificadores, offsets, rótulos e metadados, sem notas livres.
- `audits/comparison_2026-11-20.json`: relatório agregado de concordância.
- `manifests/` e `results/`: proveniência e resultados agregados.
- `checksums.sha256`: hashes dos arquivos completos.

## Dados completos para revisão

A pasta `review-data/` contém os textos integrais e os archives completos para
o professor revisar o trabalho. Ela inclui:

- os quatro archives com textos e rótulos;
- as exportações completas com os trechos anotados;
- as auditorias completas;
- o artigo original e os metadados do corpus.

Os textos pertencem aos veículos de origem. O uso é restrito à avaliação
acadêmica. Não redistribua os arquivos de `review-data/`.

## Nomes nos arquivos

O arquivo `audits/gabriel_carlos_2026-11-20.json` preserva o rótulo histórico
`Gabriel Carlos`. Ele corresponde a Gabriel Machado, coautor responsável por
essa auditoria. O arquivo de Gabriel Rodrigues é uma projeção do overlay
adjudicado, não uma auditoria cega independente.

## Limites de interpretação

As exportações sem texto permitem verificar a estrutura e os rótulos. A
reprodução da avaliação dos modelos exige os textos completos de `review-data/`.
Consulte `DATA_AND_ARTIFACT_POLICY.md`, `data/README.md` e
`review-data/README.md`.
