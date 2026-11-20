# Auditorias humanas do overlay

Arquivos privados de auditoria da camada overlay. Não redistribuir.

## Arquivos

- `gabriel_carlos_2026-11-20.json`: export do revisor **Gabriel Carlos**,
  5.111 decisões sobre as 5.111 entidades do overlay.
- `gabriel_rodrigues_overlay_2026-11-20.json`: export **derivado** do overlay
  adjudicado, atribuído a **Gabriel Rodrigues**. Não é uma auditoria cega
  independente; serve como referência da camada overlay para a comparação.
- `comparison_2026-11-20.json`: relatório agregado do `compare_audits.py`.

## Números

| Item | Valor |
| --- | ---: |
| Entidades do overlay | 5.111 |
| Decisões do Gabriel Carlos | 5.111 |
| Incertas (Carlos) | 23 |
| Com sugestão Muse revelada (Carlos) | 4.787 |
| Concordância overlay x Carlos | 98,8% |
| Cohen/Fleiss kappa | 0,980 |
| Entidades na camada Carlos (sem NONE) | 5.074 |
| Decisões NONE (Carlos) | 37 |

## Leitura

A concordância é alta, mas 4.787 das 5.111 decisões foram feitas com a sugestão
visível. Isso caracteriza um modo assistido, não uma auditoria cega; a
concordância deve ser interpretada como consistência com a camada exibida, não
como independência entre anotadores.

O export de Gabriel Rodrigues é uma projeção do overlay, não um julgamento
humano separado. Para uma comparação cega real, seria necessário um export
independente dele, gerado no modo cego.
