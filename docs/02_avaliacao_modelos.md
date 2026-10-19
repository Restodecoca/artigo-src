# Avaliação dos modelos

## Relação com o artigo

O artigo original avaliou SecureBERT-NER e SecureBERT-APTNER em uma amostra de
60 notícias anotadas manualmente, limitadas aos primeiros 400 tokens. O corpus
completo e essas anotações não estão disponíveis para este projeto. Mantivemos
a tarefa e as quatro categorias do protocolo, mas usamos notícias e labels
próprias; as métricas locais não são uma reprodução direta dos números do
artigo.

## Execuções locais

Foram avaliados checkpoints públicos com revisões fixadas, usando inferência
em Tesla T4. Para os artigos completos, o limite foi de 512 tokens, com janelas
alinhadas a palavras e `stride=128`. Os 299 documentos retidos foram
processados sem falhas.

### Benchmark público substituto — 1.627 documentos

Esta execução anterior usa uma composição de datasets públicos com labels
Muse. Ela é uma validação externa distinta da base de 299 artigos completos.

| Modelo | Strict F1 | Partial F1 |
| --- | ---: | ---: |
| SecureBERT-NER | 0,1906 | 0,4650 |
| SecureBERT-APTNER | 0,0597 | 0,4840 |

### Artigos completos — comparação entre camadas

| Camada de avaliação | Modelo | Strict F1 | Partial F1 | Partial same-type F1 |
| --- | --- | ---: | ---: | ---: |
| Muse original | SecureBERT-NER | 0,0450 | 0,1531 | 0,1455 |
| Muse original | SecureBERT-APTNER | 0,0323 | 0,2019 | 0,1980 |
| Overlay adjudicado | SecureBERT-NER | 0,0809 | 0,2617 | 0,2486 |
| Overlay adjudicado | SecureBERT-APTNER | 0,0507 | 0,2933 | 0,2891 |

`Strict` exige limites e tipo exatos. `Partial` considera sobreposição dos
spans sem exigir o tipo correto; `Partial same-type` exige sobreposição e tipo
correto. Por isso, os valores de partial não devem ser misturados sem declarar
qual regra foi usada.

## Interpretação

O desempenho depende da camada de anotação e da definição da métrica. A
diferença entre Strict e Partial indica que a correspondência dos limites dos
spans é um desafio importante. Como os dados e labels diferem dos originais,
esses resultados descrevem uma extensão no dataset próprio; não são uma
comparação direta com o gold manual do artigo.
