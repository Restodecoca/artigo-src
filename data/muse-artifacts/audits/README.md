# Auditorias humanas do overlay

Exportações públicas de auditoria da camada overlay, sem notas livres e sem
textos integrais. As versões completas estão em `review-data/audits/` e não
devem ser redistribuídas.

Os anotadores realizaram revisão manual de anotações com origem nas
sugestões do Muse Spark, modelo de linguagem da Meta. O trabalho humano
consistiu em avaliar e corrigir os trechos e seus rótulos, não em anotação
do zero.

## Arquivos

- `gabriel_carlos_2026-11-20.json`: export do revisor **Gabriel Machado**,
  identificado como **Gabriel Carlos** no campo histórico. São 5.111 decisões
  sobre as 5.111 entidades do overlay.
- `gabriel_rodrigues_overlay_2026-11-20.json`: export derivado do overlay
  adjudicado, atribuído a Gabriel Rodrigues. Serve como referência da camada
  overlay para a comparação.
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

A concordância é alta e o relatório registra 4.787 decisões com a referência
visível na interface. Esse registro de exposição à referência deve ser
considerado na interpretação da concordância. A concordância se refere
aos trechos comparados e à cobertura de cada anotador.

O arquivo de Gabriel Rodrigues representa o overlay na comparação. O
formato desse arquivo não deve ser usado para substituir a descrição do
procedimento humano fornecida pelos autores.

## Validação em pares e consenso

| Par | Spans comuns | Concordância | Kappa |
| --- | ---: | ---: | ---: |
| Rodrigues x Carlos | 5.111 | 98,8% | 0,980 |
| Rodrigues x Angelo | 4.649 | 99,98% | — |
| Carlos x Angelo | 4.640 | 99,5% | 0,992 |

A referência consolidada (`review-data/archives/muse_consensus.tar.gz`) usa a
revisão do Angelo como base, sobrepõe os rótulos de Rodrigues e Machado em
spans exatos e mantém o voto majoritário; empates ficam com o rótulo do Angelo.
São 9.318 spans: 4.640 com três anotadores, 10 com dois e 4.668 exclusivos do
Angelo. Há 22 conflitos de rótulo, sem alteração final em relação à revisão do
Angelo.
