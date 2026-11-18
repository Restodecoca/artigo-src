# Anotações assistidas por IA e avaliação da camada aumentada

## Objetivo

O overlay adjudicado cobre 5.111 entidades em 299 notícias, mas ainda deixa
passar menções relevantes. Para medir esse gap e produzir uma camada mais
completa para os experimentos do artigo, foi construída uma camada separada de
adições: um leitor LLM leu cada notícia integralmente, propôs entidades ausentes
e o revisor humano confirmou ou rejeitou cada lote antes da gravação.

A camada **não substitui** o overlay e não é uma anotação exclusivamente humana.
Ela é registrada como `ai_assisted_human_verified` em
`data/muse-artifacts/annotations/ai_assisted_additions.json`.

## Método

1. O leitor LLM leu os 299 documentos retidos, em lotes, sem usar regex como
   método de anotação.
2. Foram propostas apenas entidades ausentes, com offsets exatos e uma das
   quatro categorias do protocolo.
3. Cada lote foi apresentado ao revisor humano, que confirmou ou rejeitou as
   propostas.
4. As propostas confirmadas foram validadas automaticamente contra o overlay:
   texto exato, rótulo válido, ausência de sobreposição e ausência de
   duplicidade de span/forma superficial no mesmo documento.
5. Menções repetidas da mesma forma superficial foram deduplicadas por
   documento, mantendo a primeira ocorrência.

## Resultados da camada

| Item | Valor |
| --- | ---: |
| Documentos com adições | 208 de 299 |
| Entidades adicionadas | 687 |
| IDTY | 459 |
| ACT | 106 |
| LOC | 101 |
| VUL | 21 |
| Overlay original | 5.111 |
| Camada aumentada | 5.798 |
| Média de adições por documento | 3,3 |
| Máximo em um documento | 22 |

### Relação com a camada Muse

| Situação da adição | Quantidade |
| --- | ---: |
| Mesmo span e mesmo rótulo na Muse | 24 |
| Mesmo span, rótulo diferente | 1 |
| Sobreposição parcial com a Muse | 8 |
| Sem correspondência na Muse | 654 |

A maior parte das adições (654) não estava em nenhuma das duas camadas
existentes. Outras 24 já estavam na Muse, mas não no overlay — evidência de que
o overlay também perdeu entidades que a pré-anotação havia capturado.

## Validação automática

```bash
uv run python scripts/validation/validate_ai_additions.py
```

Resultado: **0 erros**. O validador confere `text[start:end]`, rótulo, overlap
com o overlay e duplicidade por documento.

## Avaliação extrínseca

A camada aumentada foi empacotada no formato Muse e avaliada no Colab T4 com os
mesmos checkpoints e o mesmo protocolo de janelas da avaliação anterior
(512 tokens, `stride=128`, agregação simples).

| Camada / modelo | Strict F1 | Partial F1 | Partial same-type F1 |
| --- | ---: | ---: | ---: |
| Overlay / SecureBERT-NER | 0,0809 | 0,2617 | 0,2486 |
| Overlay / SecureBERT-APTNER | 0,0507 | 0,2933 | 0,2891 |
| Overlay + adições / SecureBERT-NER | **0,0852** | **0,2795** | **0,2645** |
| Overlay + adições / SecureBERT-APTNER | **0,0532** | **0,3111** | **0,3053** |

As adições elevam o F1 das duas arquiteturas. A interpretação é direta: parte
das predições antes contabilizadas como falsos positivos corresponde a
entidades reais que faltavam no overlay. O ganho é maior em `partial` e
`partial same-type`, coerente com o fato de que a camada adiciona spans e
menções, não apenas corrige rótulos.

## Fine-tuning preliminar

Foi executado um experimento preliminar de `Full` fine-tuning no Colab T4
(uma seed, 42; cinco épocas; divisão 179/60/60; seed de divisão 2024). A mesma
execução treina e avalia as duas camadas, permitindo comparar a diagonal e os
experimentos cruzados.

| Treino / teste | Strict F1 | Partial same-type F1 |
| --- | ---: | ---: |
| Muse / Muse | 0,3058 | 0,4558 |
| Aumentada / Aumentada | **0,4866** | **0,6344** |
| Muse / Aumentada | 0,2455 | 0,4033 |
| Aumentada / Muse | 0,2063 | 0,2595 |

O resultado é preliminar (uma seed) e não substitui a média de três seeds usada
na tabela principal do artigo. Ele indica que a camada aumentada fornece sinal
de treino adicional, mas também que a política de anotação continua afetando
fortemente o desempenho cruzado.

## Limitações

- A camada é **parcial**: 208 dos 299 documentos receberam ao menos uma adição;
  91 documentos não tiveram adição confirmada.
- A camada é **assistida por IA**: não deve ser descrita como anotação humana
  independente nem usada para medir concordância entre anotadores humanos.
- A avaliação extrínseca usa os mesmos checkpoints da avaliação anterior; ela
  mede o efeito da camada de referência, não uma nova capacidade dos modelos.
- O treino de fine-tuning na camada aumentada deve ser interpretado como
  preliminar até a conclusão das seeds e das receitas completas.

## Reprodutibilidade

O archive aumentado é montado a partir do overlay e do arquivo de adições:

```text
muse_batches/
  vinitvek-healthcare-corrected-ai/
    batch_0001.json ... batch_0007.json
    labels_batch_0001.json ... labels_batch_0007.json
```

O runner `scripts/colab/run_colab_muse_validation.py` foi executado no Colab CLI
com aceleração T4. O resultado agregado contém apenas contagens e métricas; o
diagnóstico por documento permanece privado.
