# Fine-tuning, resultados e verificações

## Protocolo de fine-tuning

O SecureBERT-NER foi adaptado às labels do dataset próprio. Os mesmos IDs de
documentos foram usados em todas as condições:

- divisão documental fixa: `179` treino, `60` validação e `60` teste;
- seed do split: `2024`; seeds de treino: `42`, `123` e `2024`;
- cinco épocas, sequência máxima de 512 tokens e `stride=128`;
- cabeça BIO nova com nove rótulos (`O` e `B/I` para os quatro tipos).

Foram comparadas quatro receitas:

- **Full:** atualiza todos os pesos do modelo;
- **LoRA+:** treina adapters de baixo rank em `query`/`value` e a cabeça de
  classificação;
- **CCE ponderada:** entropia cruzada categórica com pesos para aumentar o
  custo dos erros em classes raras;
- **ROS:** *Repeated OverSampling*, reamostragem de documentos de treino com
  reposição; pesos por presença de classe limitados a `3x`. Validação e teste
  não foram reamostrados.

## Resultados no overlay (média de três seeds)

As métricas abaixo são Strict F1 e Partial same-type F1, nessa ordem; `±`
representa o desvio padrão entre seeds.

| Receita | Strict F1 | Partial same-type F1 |
| --- | ---: | ---: |
| LoRA+ | 0,1061 ± 0,0152 | 0,3270 ± 0,0136 |
| Full | 0,4336 ± 0,0056 | 0,5528 ± 0,0018 |
| Full + CCE ponderada | 0,4421 ± 0,0049 | 0,5429 ± 0,0025 |
| Full + ROS | 0,4410 ± 0,0073 | 0,5602 ± 0,0038 |

Full, CCE e ROS ficaram próximos neste split e superaram LoRA+. Os resultados
sugerem adaptação à camada usada no treino; não demonstram que o overlay esteja
objetivamente correto nem estimam, por si sós, a generalização para outros
corpora.

## Sensibilidade à camada de labels

No fine-tuning Full, a diagonal Muse/Muse obteve Strict/Partial same-type F1 de
`0,3131 ± 0,0072` / `0,4776 ± 0,0044`; a diagonal overlay/overlay obteve
`0,4336 ± 0,0056` / `0,5528 ± 0,0018`. Os resultados cruzados foram menores:
treino Muse/teste overlay `0,2403 / 0,3699`; treino overlay/teste Muse
`0,2379 / 0,3033`. Isso evidencia sensibilidade à política de anotação.

## Verificações de software

Antes do commit do projeto:

- `pytest`: **60 testes passaram**;
- Ruff focado em `src`, `tests` e `scripts`: passou;
- `compileall` em `src`, `tests` e `scripts`: passou;
- parsing de `configs/reproduction.toml`: passou;
- validador do overlay: `314` registros de origem, `299` retidos e `5.111`
  entidades;
- validação estrutural da apresentação PowerPoint: passou.

Essas verificações confirmam o comportamento estrutural do código e dos
artefatos, não a validade semântica das labels.

## Continuidade possível

Não há etapa de execução pendente para apresentar o Marco 3. Se o estudo
continuar, os próximos passos científicos são auditoria humana independente
das labels, ampliação do conjunto de teste/fontes e análise de incerteza.
