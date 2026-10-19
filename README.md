# Reprodução de NER de cibersegurança em saúde

Reprodução e extensão de **An Analysis of Pre-trained Models to Identify
Cybersecurity Incidents Entities in the Healthcare Industry**, de Rafael Paim e
Luciano Ignaczak.

O projeto parte do protocolo descrito no artigo e mantém uma separação explícita
entre a reprodução fiel e a validação externa. O corpus original de notícias da
área da saúde e as anotações manuais originais estão indisponíveis. Os datasets
públicos encontrados no Hugging Face são apenas material de referência e nenhum
deles é tratado silenciosamente como o corpus original do artigo.

## Estado atual

O estado documentado do projeto é `extension`:

- o corpus original do artigo não está disponível;
- a camada `Muse` original permanece preservada como anotação silver;
- um `adjudicated overlay` separado foi produzido sobre os mesmos `299`
  documentos do conjunto expandido;
- as validações T4 foram concluídas para a camada `Muse` original e para o
  `adjudicated overlay`;
- o estudo de sensibilidade de fine-tuning foi concluído com `LoRA+`, `full`,
  `CCE` ponderado e `ROS`.

Nenhum resultado local é uma reprodução `faithful` dos resultados do artigo.

## Protocolo atual

- Modelos: `SecureBERT-NER` e `SecureBERT-APTNER`.
- Checkpoints públicos: `CyberPeace-Institute/SecureBERT-NER` e
  `Cyber-ThreaD/SecureBERT-APTNER`.
- Tipos de entidade compartilhados: `IDTY`, `ACT`, `VUL` e `LOC`.
- Modos de avaliação: correspondência estrita e parcial (`strict` e `partial`).
- Coleção reportada: `24,108` registros, reduzida a um corpus final de `1,039`.
- Avaliação manual do artigo: `60` notícias, truncadas nos primeiros `400`
  tokens.
- Data da coleta: `2023-10-30`, cobrindo `2023-01-01` a `2023-10-30`.

O protocolo legível por máquina está em `configs/reproduction.toml`. As
barreiras de segurança em Python estão em
`src/healthcare_ner_replication/protocol.py`.

A conversão de labels específica de cada modelo está explicitada em
`src/healthcare_ner_replication/inference.py`: `VULID` e `VULNAME` são mapeados
para o tipo agregado `VUL` do artigo.

O registro da auditoria de fontes públicas está em `data/SEARCH_LOG.md`. A
auditoria não encontrou uma cópia autorizada do corpus original; os datasets
públicos listados continuam sendo apenas material de referência.

O catálogo de entradas de linha de comando está em `scripts/README.md`. A
documentação técnica detalhada está em `tasks/finetune_labels_spec.md` e no
arquivo de configuração `configs/reproduction.toml`.

## Validação externa com Muse

A validação T4 primária usou as labels silver originais do Muse
(`silver_muse_review_pass4`) em `1,627` documentos retidos: `1,621` do Vinitvek
e `6` do Scorton. O GVIC foi avaliado durante a curadoria, mas não contribuiu
com documentos retidos. Os três conjuntos de fonte/labels passaram pela
validação estrutural com zero erros.

Os modelos foram executados em uma Tesla T4, usando revisões fixadas dos
checkpoints, limite de `512` tokens por modelo e janelas sobrepostas com
`stride=128`. Ambos processaram todos os documentos sem falhas. O resultado
agregado está em `data/muse_validation_t4.json` e o protocolo está em
`configs/reproduction.toml`.

| Modelo | Strict F1 | Partial F1 |
| --- | ---: | ---: |
| SecureBERT-NER | 0.1906 | 0.4650 |
| SecureBERT-APTNER | 0.0597 | 0.4840 |

O `SecureBERT 2.0` também foi testado no mesmo corpus. Como sua taxonomia
nativa é diferente, a execução de compatibilidade mapeou somente
`Organization -> IDTY` e `Vulnerability -> VUL`: Strict F1 `0.0279` e Partial
F1 `0.3265`. Esse resultado não é diretamente comparável aos dois checkpoints
originais e está registrado em `data/securebert2_muse.json`.

Essas métricas são uma `extension`, não uma reprodução fiel do artigo, e as
labels não são anotações gold verificadas por humanos. Elas não devem sustentar
afirmações de publicação sem revisão humana independente, concordância entre
anotadores e análise formal de incerteza.

O piloto de artigos completos está registrado separadamente em
`data/muse_validation_vinitvek_60_t4.json`. Ele reteve `55` de `60` artigos do
Firecrawl após a triagem do Muse. O `SecureBERT-NER` atingiu Strict/Partial F1 de
`0.0702`/`0.2200`, enquanto o `SecureBERT-APTNER` atingiu `0.0351`/`0.2107`.
Essa é uma pequena extensão com labels silver e ela não deve ser combinada com
o benchmark de `1,627` documentos acima.

A amostra expandida do Firecrawl contém `329` URLs únicas de incidentes de
saúde de `2023`. A extração de artigos completos teve sucesso em `314`
registros; `15` falharam e continuam listados no manifesto privado. A anotação
Muse reteve `299` registros e descartou `15` páginas inutilizáveis, produzindo
`2,103` entidades silver. O arquivo consolidado de fonte/labels é
`data/raw/vinitvek-articles-2023-muse-expanded.tar.gz`, com SHA-256
`aebd0c149d1c5ac873fea47dce04acb57b8fea55f35529f5eba12b33d5db94cb`.

A validação T4 processou todos os `299` documentos retidos sem falhas. Desses,
`174` excederam o limite de `512` tokens do modelo e foram processados com
janelas sobrepostas alinhadas a palavras (`stride=128`). Os resultados estão
em `data/muse_validation_vinitvek_expanded_t4.json`. Um artefato detalhado
privado, com cada texto extraído, spans do Muse, spans do modelo e índices de
correspondência, está em `data/raw/vinitvek-articles-2023-muse-detailed.json`
para revisão local somente.

| Modelo | Strict F1 | Partial F1 | Partial same-type F1 |
| --- | ---: | ---: | ---: |
| SecureBERT-NER | 0.0450 | 0.1531 | 0.1455 |
| SecureBERT-APTNER | 0.0323 | 0.2019 | 0.1980 |

Esse resultado continua sendo uma extensão com labels silver, separada dos dois
benchmarks acima.

### Experimentos de reparo de spans

A varredura T4 testou as agregações de subwords `simple`, `first`, `average` e
`max`, além do reparo determinístico dos spans `simple`. O reparo expande um
span até os limites de palavras, combina fragmentos contíguos compatíveis como
`zero`-`day` e, opcionalmente, remove spans somente de pontuação e spans de dois
caracteres. Ele não adiciona um token que o modelo não previu nem altera uma
label prevista.

| Variante | NER strict / partial F1 | APTNER strict / partial F1 |
| --- | ---: | ---: |
| Full `simple` baseline | 0.0450 / 0.1531 | 0.0323 / 0.2019 |
| Full `first` | 0.0558 / 0.2005 | 0.0161 / 0.2073 |
| Full `average` | 0.0585 / 0.1944 | 0.0180 / 0.1861 |
| Full `max` | 0.0593 / 0.1913 | 0.0181 / 0.1900 |
| Full `simple` + cleanup | **0.0848 / 0.2108** | **0.0775 / 0.2489** |
| Truncated 400 `simple` | 0.0583 / 0.1836 | 0.0383 / 0.2348 |
| Truncated 400 `first` | 0.0709 / 0.2345 | 0.0218 / 0.2344 |

O resultado de cleanup é uma extensão diagnóstica, não uma nova pontuação do
modelo: parte do ganho de strict F1 vem da correção dos limites de tokenização.
O artefato baseline continua sendo o resultado principal reproduzível. As
variantes offline estão registradas em
`data/span_postprocessing_vinitvek_expanded.json`.

O `SecureBERT 2.0` foi executado novamente no mesmo arquivo de `299`
documentos. Sua taxonomia nativa não possui equivalente a `ACT` ou `LOC`, por
isso a pontuação de compatibilidade mapeia somente
`Organization -> IDTY` e `Vulnerability -> VUL`:

| Modelo | Compatible strict F1 | Compatible partial F1 |
| --- | ---: | ---: |
| SecureBERT 2.0 NER | 0.0039 | 0.0543 |

Ele produziu `20,896` spans compatíveis para `812` labels Muse comparáveis. A
saída nativa contém `35,521` spans, incluindo `Indicator`, `System` e `Malware`,
que não são avaliados contra os quatro tipos Muse. Esse resultado não é uma
comparação completa de quatro labels. A saída por documento está armazenada
privadamente em `data/raw/vinitvek-articles-2023-muse-securebert2-detailed.json`.

Os relatórios exatos de comparação por span dos três modelos são gerados por
`scripts/analysis/compare_muse_model_spans.py`. Eles classificam cada span Muse como
`exact`, `overlap_same_type`, `overlap_wrong_type`, `missed` ou
`unmapped_label`, e cada span do modelo como correspondência ou
`false_positive`. Esses relatórios são privados porque contêm texto derivado
dos artigos:

- `data/raw/vinitvek-articles-2023-muse-securebert-ner-comparison.json`
- `data/raw/vinitvek-articles-2023-muse-securebert-aptner-comparison.json`
- `data/raw/vinitvek-articles-2023-muse-securebert2-comparison.json`

O primeiro lote de fontes também foi auditado semanticamente sem alterar as
labels brutas. A auditoria encontrou cobertura incompleta de roundups e limites
mistos entre `ACT` e `VUL`; portanto, as labels Muse devem ser descritas como
anotações silver, e não como gold verificadas por humanos. A auditoria privada
está em `data/raw/vinitvek-articles-2023-muse-batch-0001-audit.md`.

### Adjudicated overlay

As labels Muse foram revisadas em sete lotes por subagents independentes e por
uma segunda rodada de adjudicação. Os arquivos Muse originais permanecem
inalterados. O novo overlay conserva os mesmos `299` documentos e contém `5,111`
entidades, após remover spans malformados, sobrepostos, duplicados, genéricos e
semanticamente incorretos, e adicionar menções ausentes defensáveis. Ele está
armazenado em labels por lote em `data/processed/muse_corrected/`, com os
relatórios de adjudicação no mesmo diretório. A validação estrutural é
reproduzível com:

```powershell
uv run python scripts/validate_corrected_muse_labels.py `
  data/raw/vinitvek-articles-2023 data/processed/muse_corrected
```

O arquivo `data/processed/muse_corrected.tar.gz` foi usado na validação T4 das
labels corrigidas. As pontuações contra esse overlay são um novo resultado de
`extension` e não devem ser comparadas como se fossem o conjunto gold manual do
artigo.

A validação T4 das labels corrigidas foi concluída em uma Tesla T4, com as
mesmas revisões fixadas dos modelos, limite de `512` tokens e `stride=128`.
Ambos os modelos processaram `299/299` documentos sem falhas:

| Modelo | Strict F1 | Partial F1 | Partial same-type F1 |
| --- | ---: | ---: | ---: |
| SecureBERT-NER | 0.0809 | 0.2617 | 0.2486 |
| SecureBERT-APTNER | 0.0507 | 0.2933 | 0.2891 |

O artefato agregado e `data/muse_validation_vinitvek_corrected_t4.json`; o
SHA-256 do arquivo e
`e2b3732fe64612564bc70ca95055fe9171a60d06e018578ea64bceef730b397d`. Em
relação ao overlay Muse original, o Partial F1 mudou de `0.1531` para `0.2617`
para NER e de `0.2019` para `0.2933` para APTNER. Esse é um resultado de
sensibilidade da camada de anotação, não uma evidência de reprodução fiel.

### Sensibilidade de fine-tuning

Para testar se o modelo aprende a política de anotação, o `SecureBERT-NER` foi
submetido a fine-tuning com a mesma divisão de documentos (`179/60/60`), três
seeds, cinco epochs e uma cabeça BIO nova de `9` labels. A comparação principal
usou `full` fine-tuning:

| Labels de treino | Labels de teste | Strict F1 | Partial same-type F1 |
| --- | --- | ---: | ---: |
| Muse original | Muse original | 0.3131 +/- 0.0072 | 0.4776 +/- 0.0044 |
| Muse original | Adjudicated overlay | 0.2403 +/- 0.0021 | 0.3699 +/- 0.0107 |
| Adjudicated overlay | Muse original | 0.2379 +/- 0.0047 | 0.3033 +/- 0.0079 |
| Adjudicated overlay | Adjudicated overlay | **0.4336 +/- 0.0056** | **0.5528 +/- 0.0018** |

`LoRA+` atingiu `0.1061` de strict e `0.3270` de Partial same-type F1 na sua
diagonal. Portanto, `full` fine-tuning apresentou ganho substancial. `CCE`
ponderado atingiu `0.4421`/`0.5429`, enquanto `full` fine-tuning com `ROS` em
nível de documento atingiu `0.4410`/`0.5602` na diagonal corrigida. `ROS` usou
amostragem com reposição e pesos de presença de classe limitados a `3x`;
validação e teste nunca foram amostrados.

Os artefatos são `data/finetune_loraplus_muse_sensitivity_t4_v2.json`,
`data/finetune_full_muse_sensitivity_t4.json`,
`data/finetune_full_weighted_cce_muse_sensitivity_t4.json` e
`data/finetune_full_ros_muse_sensitivity_t4.json`. Esses resultados sustentam
a afirmação de que as pontuações do modelo dependem da camada de anotação, mas
não demonstram que o `adjudicated overlay` esteja objetivamente correto.

## Limites de reprodução e apresentação

O corpus completo original do artigo e as anotações gold manuais não estão
disponíveis neste repositório. Assim, as métricas reportadas pelo artigo podem
ser citadas como resultados do artigo, mas as execuções locais devem ser
apresentadas como `extension` ou validação externa, nunca como reprodução fiel.
As pontuações locais baixas são evidências úteis de desvio de domínio, anotação
e protocolo; não demonstram que as pontuações reportadas pelo artigo foram
reproduzidas.

Cada resultado deve usar um destes estados:

- `faithful`: corpus e anotações originais verificados;
- `approximate`: substituto público utilizado, com todos os desvios documentados;
- `extension`: novos dados, anotação, modelo ou protocolo de avaliação.

Os nomes canônicos dos estados são definidos no arquivo de configuração como
`faithful`, `approximate` e `extension`. O estado atual dos resultados locais é
`extension`.

## Segurança de dados

Não faça commit de dumps de notícias, anotações que contenham texto copiado de
artigos, credenciais, caches de modelos ou artefatos gerados sem revisão. Leia
`DATA_AND_ARTIFACT_POLICY.md` antes de baixar dados.

O Kaggle token anteriormente colado no chat deve ser revogado e regenerado. Ele
não está armazenado neste repositório e não é necessário para o fluxo atual
Hugging Face-first.

## Desenvolvimento

```powershell
uv sync --extra dev
uv run pytest -q
uv run ruff check .
```

As dependências de modelos e datasets são opcionais de propósito até que o
caminho do corpus e do hardware seja confirmado:

```powershell
uv sync --extra hf --extra models --extra dev
```

## AMD ROCm

O ambiente ROCm disponível está fora deste repositório, em
`C:\rocm-rf01\RCOm-windows-gfx1030`. O ambiente Python nightly detectou uma
AMD Radeon RX 6600M e passou em um teste de tensor e memória. Use esse ambiente
para inferência de modelos somente depois que os testes de CPU passarem aqui:

```powershell
& 'C:\rocm-rf01\RCOm-windows-gfx1030\.venv-nightly\Scripts\python.exe' `
  'C:\rocm-rf01\RCOm-windows-gfx1030\scripts\test-gpu.py'
```

O projeto não copia wheels ROCm para o lockfile. Isso mantém o ambiente de
reprodução separado do runtime específico do hardware.
