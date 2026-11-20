# Camada de adições assistidas por IA

Arquivo: `ai_assisted_additions.json`

Esta camada **não substitui** o overlay adjudicado. Ela registra entidades que
faltavam no overlay e foram propostas por um leitor LLM e confirmadas pelo
revisor humano antes da gravação.

## Proveniência

- `annotation_status`: `ai_assisted_human_verified`
- `annotator_type`: `ai-assisted`
- `verified_by`: `gabriel`
- `verification_method`: cada lote foi apresentado ao revisor, que confirmou ou
  rejeitou as entidades antes da gravação.
- `base_layer`: `processed/muse_corrected.tar.gz`

O nome do modelo não é registrado no artefato. A camada deve ser descrita como
**assistida por IA e verificada por humano**, nunca como anotação exclusivamente
humana.

## Números

| Item | Valor |
| --- | ---: |
| Documentos com adições | 208 |
| Entidades adicionadas | 687 |
| IDTY adicionadas | 459 |
| ACT adicionadas | 106 |
| LOC adicionadas | 101 |
| VUL adicionadas | 21 |
| Overlay original | 5.111 |
| Camada aumentada | 5.798 |

As adições aparecem uma vez por forma superficial em cada documento (a primeira
menção), para evitar repetição da mesma entidade ao longo do texto.

## Validação

```bash
uv run python scripts/validation/validate_ai_additions.py
```

O validador confere, para cada adição:

- `text[start:end]` idêntico ao texto de origem;
- rótulo em `IDTY`, `ACT`, `VUL`, `LOC`;
- ausência de sobreposição com o overlay;
- ausência de span ou forma superficial duplicada no mesmo documento.

Resultado atual: **0 erros**.

## Uso nos experimentos

Para avaliar ou treinar com a camada aumentada, é preciso empacotar o overlay
com as adições em um archive no formato Muse (`batch_*.json` +
`labels_batch_*.json`). O script `scripts/validation/validate_ai_additions.py`
expõe as funções de leitura e validação; o empacotamento usado nos experimentos
está descrito em `docs/04_anotacoes_assistidas.md`.

## Privacidade

O arquivo contém IDs de documento, offsets, rótulos e o texto exato das
entidades adicionadas. Trate como material restrito: não redistribua os textos
integrais dos artigos e não versione exports de revisão individuais.

# Revisão completa do overlay

Arquivo: `overlay_review_v1.json`. Archive resultante:
`processed/muse_reviewed.tar.gz` (pasta `muse_batches/vinitvek-healthcare-reviewed/`).

Esta camada revê as 299 notícias mantidas do overlay adjudicado. Ela
**não** usa `ai_assisted_additions.json`, que serve só para comparação. Também
não sobrescreve o overlay: registra decisões sobre as entidades existentes
(`relabel`, `fix_span`, `reject`) e entidades faltantes (`added_entities`).
Entidades do overlay sem decisão foram confirmadas como estão.

## Proveniência e verificação

As anotações iniciais foram geradas pelo Muse Spark, modelo de linguagem
da Meta. Os anotadores humanos revisaram manualmente os trechos e as
categorias, corrigiram marcações e acrescentaram entidades ausentes.
Trata-se de revisão humana sobre sugestões automáticas, não de anotação
humana do zero.

Os campos `annotation_status: ai_assisted_human_verified` e
`verification: user_approved` permanecem nos arquivos históricos. Os
metadados não foram alterados nesta revisão documental. A descrição do
procedimento distingue a geração automática das sugestões da revisão
manual realizada pelos anotadores.

A base registrada é `processed/muse_corrected.tar.gz`, com SHA256 iniciado
por `e2b3732f`. O campo `verified_by` ainda não está preenchido no arquivo.

## Critérios

- Todas as menções de cada entidade são marcadas, não só a primeira.
- `IDTY`: organizações, incluindo órgãos como "Attorney General of Maine"
  inteiros (o estado dentro do nome do órgão não vira `LOC`). Pessoas, produtos e
  sistemas (por exemplo MOVEit, Microsoft 365) não são marcados.
- `ACT`: tipos de ataque e ações do atacante (data breach, ransomware attack,
  exfiltrated, gained access, compromised quando o sujeito é conta ou sistema).
- Removidos por critério, inclusive onde o overlay marcava: texto-padrão de
  escritório de advocacia ("data breach lawyer", "data breach lawsuit",
  "being/gaining access to consumers’ …", "compromised files",
  "what information was leaked"), negações, hipóteses, menções genéricas,
  particípios atributivos ("the stolen data") e spans que cortam palavras
  ("[access]ible", "[Russia]n").

## Números

| Item | Valor |
| --- | ---: |
| Documentos revisados | 299 de 299 |
| Entidades no overlay | 5.111 |
| Entidades adicionadas | 4.554 |
| Entidades removidas (`reject`) | 347 |
| Spans corrigidos (`fix_span`) | 115 |
| Rótulos trocados (`relabel`) | 1 |
| Entidades na camada revisada | 9.318 |

| Rótulo | Overlay | Revisada |
| --- | ---: | ---: |
| IDTY | 2.627 | 5.041 |
| ACT | 1.747 | 3.255 |
| LOC | 672 | 907 |
| VUL | 65 | 115 |

## Validação

```bash
uv run python -m scripts.validation.validate_overlay_review
uv run python -m scripts.validation.validate_overlay_review --export-dir /tmp/muse/reviewed
uv run python scripts/data/validate_corrected_muse_labels.py \
  /tmp/muse/reviewed /tmp/muse/reviewed
```

O validador confere se cada decisão aponta para uma entidade do overlay, se
`text[start:end]` bate, se os rótulos são válidos e se a camada final não tem
spans sobrepostos. Resultado atual: **0 erros**; o archive tem 314 registros,
299 mantidos e 9.318 entidades.
