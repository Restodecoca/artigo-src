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
