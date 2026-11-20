# Revisão e anotação do overlay `vinitvek-healthcare-corrected`

## O pedido

Ler cada notícia do overlay e anotar as entidades conforme a característica:

- **identidade** (`IDTY`), por exemplo o nome do hospital atacado;
- **ataque** (`ACT`);
- **localização** (`LOC`);
- **vulnerabilidade** (`VUL`).

Como o anotador anterior já tinha feito parte do trabalho, a tarefa era
**validar o que ele marcou e anotar o que estava faltando**.

## O que foi feito

As 299 notícias mantidas do overlay (`processed/muse_corrected.tar.gz`, 7 lotes,
5.111 entidades) foram lidas uma a uma. Para cada notícia:

1. cada entidade do anotador anterior foi conferida e ficou como estava,
   teve o span corrigido, teve o rótulo trocado ou foi removida;
2. as entidades que faltavam foram adicionadas, em **todas** as menções do texto.

O leitor LLM propôs as decisões em blocos de cerca de 6 notícias, e o revisor
humano aprovou cada bloco. Os 299 documentos estão aprovados
(`verification: user_approved`): 94 foram aprovados antes da gravação (lotes
0001 e 0002) e 205 depois, já gravados (lotes 0003 a 0007). A camada é
**assistida por IA e verificada por humano**.

A revisão partiu só do overlay. A camada anterior de adições
(`ai_assisted_additions.json`) foi usada apenas no final, para comparação.

## Critérios de anotação

| Rótulo | O que marca | Exemplos | O que não marca |
| --- | --- | --- | --- |
| `IDTY` | organizações: hospitais, clínicas, sistemas de saúde, empresas, órgãos públicos, grupos criminosos | "Mission Community Hospital", "Cook County Health", "Attorney General of Maine", "LockBit" | pessoas, produtos e sistemas (MOVEit, Microsoft 365), menções genéricas ("the hospital") |
| `ACT` | tipos de ataque e ações do atacante | "data breach", "ransomware attack", "exfiltrated", "gained access", "compromised" (quando o sujeito é conta ou sistema) | negações, hipóteses, particípios atributivos ("the stolen data") |
| `LOC` | cidades, estados e países | "Toronto", "Peru", "Lackawanna County" | lugar que faz parte do nome de uma organização |
| `VUL` | vulnerabilidades | CVEs, falhas nomeadas, servidor mal configurado | o ataque em si |

Regras gerais:

- Todas as menções da entidade são marcadas, não só a primeira.
- Nome de órgão com estado ("Maine Attorney General") é `IDTY` inteiro; o
  estado não vira `LOC` separado.
- Não se marca texto-padrão de escritório de advocacia ("data breach lawyer",
  "data breach lawsuit", "being/gaining access to consumers’ …",
  "compromised files", "what information was leaked").
- O span não pode cortar uma palavra ("[access]ible", "[Russia]n").

## Validação do trabalho do anotador anterior

Das 5.111 entidades do overlay, 4.648 foram confirmadas sem alteração.

| Decisão | Quantidade | Exemplos |
| --- | ---: | --- |
| Removidas (`reject`) | 347 | ACT 317, LOC 18, IDTY 12. Mais comuns: "access" e "gaining access" no texto-padrão jurídico, "data breach" em "data breach lawyer", "compromised" referindo-se a dados, "Russia" cortado de "Russian" |
| Span corrigido (`fix_span`) | 115 | "Maine" (LOC) → "Maine Attorney General" (IDTY); "Toronto" (LOC) → "Toronto Star" (IDTY); "University of Utah" → "University of Utah Health"; "Culbertson Memorial Hospital" → "Sarah D. Culbertson Memorial Hospital"; "La Clinic" → "La Clinica" |
| Rótulo trocado (`relabel`) | 1 | "Lackawanna County": IDTY → LOC |

## O que estava faltando

Foram adicionadas **4.554 entidades**: IDTY 2.375, ACT 1.825, LOC 304, VUL 50.
A maior parte são nomes de hospitais e órgãos que o anotador marcou só uma vez
ou não marcou, e ações de ataque repetidas ao longo do texto. Entre os nomes de
instituições de saúde mais adicionados estão "U.S. Department of Health and
Human Services Office for Civil Rights", "Oak Valley Hospital District",
"Mission Community Hospital", "Community First Medical Center" e "North
Mississippi Health Services".

## Resultado

| Rótulo | Overlay | Revisado |
| --- | ---: | ---: |
| IDTY | 2.627 | 5.041 |
| ACT | 1.747 | 3.255 |
| LOC | 672 | 907 |
| VUL | 65 | 115 |
| **Total** | **5.111** | **9.318** |

Por lote:

| Lote | Notícias | Overlay | Adicionadas | Removidas | Corrigidas | Final |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0001 | 46 | 314 | 1.255 | 3 | 7 | 1.566 |
| 0002 | 48 | 450 | 1.058 | 7 | 7 | 1.501 |
| 0003 | 48 | 1.473 | 291 | 135 | 12 | 1.629 |
| 0004 | 47 | 448 | 1.040 | 27 | 16 | 1.461 |
| 0005 | 48 | 939 | 461 | 83 | 42 | 1.317 |
| 0006 | 50 | 1.256 | 419 | 83 | 32 | 1.592 |
| 0007 | 12 | 231 | 30 | 9 | 0 | 252 |
| **Total** | **299** | **5.111** | **4.554** | **347** | **116** | **9.318** |

"Corrigidas" soma `fix_span` e `relabel`.

## Comparação com a camada de adições anterior

Das 687 entidades de `ai_assisted_additions.json`, a revisão encontrou 576
(84%) com o mesmo span e rótulo, 36 com sobreposição parcial e 1 com rótulo
diferente; 74 não aparecem na revisão. As duas passagens usam o mesmo leitor
LLM, então isso mede consistência entre passagens, não concordância entre
anotadores humanos. Detalhes em `docs/04_anotacoes_assistidas.md`.

## Arquivos

- `data/muse-artifacts/annotations/overlay_review_v1.json`: decisões e adições
  por documento (IDs, offsets, rótulos e texto exato das entidades).
- `data/muse-artifacts/processed/muse_reviewed.tar.gz`: overlay revisado no
  formato Muse (`muse_batches/vinitvek-healthcare-reviewed/`), com checksum em
  `data/muse-artifacts/checksums.sha256`.
- `scripts/validation/validate_overlay_review.py` e
  `tests/test_overlay_review.py`: validador e testes.
- `data/muse-artifacts/annotations/README.md`: proveniência e critérios.

O overlay original não foi alterado.

## Como verificar

```bash
uv run python -m scripts.validation.validate_overlay_review
uv run python -m scripts.validation.validate_overlay_review --export-dir /tmp/muse/reviewed
uv run python scripts/data/validate_corrected_muse_labels.py /tmp/muse/reviewed /tmp/muse/reviewed
```

Resultado atual: **0 erros**; 314 registros, 299 mantidos, 9.318 entidades.

## Pendências

- Preencher `verified_by` em `overlay_review_v1.json` com o nome do revisor.
- Avaliar os modelos na camada revisada (ainda não foi feito).
- Fazer o commit dos arquivos.
