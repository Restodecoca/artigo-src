# Histórico de Busca do Corpus

**Estado em 2026-09-15:** o corpus original de notícias de saúde, a coleção
SQLite e as anotações manuais descritas no artigo não foram encontrados em fonte
pública autorizada. Portanto, nenhuma execução local é `faithful`: substitutos
são `approximate` ou `extension`.

## Fontes e decisões

| Fonte | Verificação | Decisão |
| --- | --- | --- |
| GitHub (repositórios e gists de `rafaapaim`) | 37 repositórios; nenhum relacionado ao artigo, SecureBERT/APTNER, NER de saúde ou SQLite; nenhum gist relevante. | Não é fonte do corpus. |
| Hugging Face | Checkpoints SecureBERT encontrados; buscas por datasets não encontraram o corpus. | Usar checkpoints e datasets somente como referência externa. |
| Kaggle | Resultados não relacionados; `chuneeb/healthcare-cybersecurity-vulnerabilities-dataset` tem 1.515 CVEs, não notícias nem spans. | Não tratar como corpus original. |
| Zenodo | Buscas por API retornaram HTTP 504. | Verificação inconclusiva, não evidência de ausência. |
| Catálogo AI4HEALTHSEC/SoBigData | Relata 6.774 artigos e NER, mas a API D4Science exigiu Bearer token (HTTP 401 sem ele); arquivo, revision e licença de redistribuição não foram verificados. | Candidato de `extension`, não substituto equivalente. |

A reconstrução local tem 1.066 registros de metadados; restringida aos três
portais e a 2023, tem 689 registros (Becker's 518, JD Supra 149, Security
Magazine 22). Não prova os 1.039 registros originais.

Datasets públicos avaliados:

- `mrmoor/cyber-threat-intelligence`, revision
  `d8783e04f46039f3624df6958dd4d34405d8c72a`, CC-BY-4.0: benchmark externo
  principal, com `identity`, `attack-pattern`, `vulnerability` e `location`
  mapeados para `IDTY`, `ACT`, `VUL` e `LOC`; `reference_only`.
- `bnsapa/cybersecurity-ner` (Apache-2.0): smoke test; não preserva diretamente
  texto completo e não tem o par `ACT`/`LOC`.
- `chairulridjal/arcspan-cyber-ner` (Apache-2.0): benchmark técnico forte,
  mas taxonomia e fontes diferem, incluindo material relacionado a APTNER.
- `vinitvek/cybersecurityattacks`, revision
  `92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b`, README com `Unlicense`: candidato
  primário para nova amostra de saúde, não corpus original nem gold set.
- `ScortonAI/Cyber-Security-Breaches`, revision
  `1da6a89a887067a29fa536441d3f32dce0a5879c`, MIT: candidato secundário; tipos
  de breach são mais amplos que ciberataques.
- `gvic-unb/public-health-news-DF-qa` (CC-BY-4.0): stress test em português,
  mas cibersegurança incidental. Outros datasets médicos/Telegram sem licença,
  CVE, ransomware ou notícias gerais foram rejeitados para este protocolo.

Mesmo com `Unlicense` no dataset vinitvek, os artigos apontados por
`source_url` continuam sujeitos aos direitos dos sites. A decisão é não
redistribuir texto extraído, labels que contenham texto copiado ou predições por
documento; manter apenas metadados, agregados e hashes permitidos pela política
de artefatos.

## Proveniência vinitvek

O split train de `vinitvek/cybersecurityattacks` contém 13.407 resumos com
`event_date`, `affected_organization`, `affected_industry`, `description` e
`source_url`. O filtro reproduzível é saúde em `affected_industry` ou
`hospital`/`medical` em `affected_organization`: 1.852 registros; no intervalo
inclusivo `2023-01-01`--`2023-10-30`: 367 registros.

As `source_url` foram usadas como índice de artigos completos, não como texto de
`description`. O Firecrawl extraiu **329 URLs únicas**, com **314 extrações** e
15 falhas; o Muse processou os 314 pares source/label, reteve **299** e rejeitou
15 páginas inutilizáveis. Os quatro labels são `IDTY`, `ACT`, `VUL` e `LOC`.

Arquivos completos para revisão (com textos de terceiros):

- Os archives completos estão em `review-data/archives/` e não devem ser
  redistribuídos.
- Archive Muse original:
  `review-data/archives/vinitvek-articles-2023-muse-expanded.tar.gz`;
  SHA-256 `aebd0c149d1c5ac873fea47dce04acb57b8fea55f35529f5eba12b33d5db94cb`.
- Archive do overlay: `review-data/archives/muse_corrected.tar.gz`;
  SHA-256 `e2b3732fe64612564bc70ca95055fe9171a60d06e018578ea64bceef730b397d`.
- Fontes do piloto: `data/raw/vinitvek-articles-2023/` (ignorado pelo Git).

## Linha do tempo T4

### 2026-09-12: benchmark externo

Em 60 exemplos elegíveis de `mrmoor`, com três seeds, os resultados foram:

| Modelo | Strict F1 média +/- DP populacional | Partial F1 média +/- DP populacional |
| --- | ---: | ---: |
| SecureBERT-NER | 0.161 +/- 0.029 | 0.262 +/- 0.023 |
| SecureBERT-APTNER | 0.155 +/- 0.024 | 0.291 +/- 0.024 |

É medição válida no substituto com gold spans, não nos artigos de saúde.

### 2026-09-13: candidatos

No benchmark T4 de 100 documentos por candidato, a sondagem de comportamento
foi: `vinitvek` 255/249 entidades (NER/APTNER), `ScortonAI` 210/112 e `GVIC`
120/3. A concordância tipada entre os dois modelos foi, respectivamente,
`0.2105`, `0.2826` e `0.6529` de F1; são diagnósticos, não gold evaluation.
Decisão: `vinitvek` primário, `ScortonAI` secundário e GVIC não primário.

### 2026-09-14: piloto de artigos completos

O piloto anotado pelo Muse reteve 55 de 60 artigos. Com limite de 512 tokens e
janelas sobrepostas (`stride=128`):

| Modelo | Strict F1 | Partial F1 | Partial same-type F1 |
| --- | ---: | ---: | ---: |
| SecureBERT-NER | 0.0702 | 0.2200 | 0.1996 |
| SecureBERT-APTNER | 0.0351 | 0.2107 | 0.2098 |

### 2026-09-14: Muse expandido

Nos 299 documentos e nas labels Muse originais (silver), os dois modelos
processaram tudo sem falhas:

| Modelo | Strict F1 | Partial F1 | Partial same-type F1 |
| --- | ---: | ---: | ---: |
| SecureBERT-NER | 0.0450 | 0.1531 | 0.1455 |
| SecureBERT-APTNER | 0.0323 | 0.2019 | 0.1980 |

A anotação silver tem 2.103 entidades (`IDTY=616`, `ACT=934`, `LOC=357`,
`VUL=196`). O sweep de aggregation/limpeza teve como melhor variante `simple +
cleanup`: NER `0.0848/0.2108` e APTNER `0.0775/0.2489` (strict/partial); é
diagnóstico, sem substituir o baseline. O SecureBERT 2.0, com apenas
`Organization -> IDTY` e `Vulnerability -> VUL`, obteve `0.0039` strict e
`0.0543` partial; não é avaliação dos quatro labels.

### 2026-09-15: overlay adjudicado

Os labels Muse originais não foram alterados. O overlay revisou os sete lotes,
conservou os mesmos 299 documentos e contém 5.111 entidades:
`IDTY=2.627`, `ACT=1.747`, `LOC=672`, `VUL=65`. A validação estrutural e a
execução T4 foram concluídas, com 299/299 documentos processados sem falhas:

| Modelo | Strict F1 | Partial F1 | Partial same-type F1 |
| --- | ---: | ---: | ---: |
| SecureBERT-NER | 0.0809 | 0.2617 | 0.2486 |
| SecureBERT-APTNER | 0.0507 | 0.2933 | 0.2891 |

Este é resultado de sensibilidade a uma nova camada adjudicada, não gold humana
nem reprodução fiel.

## Fine-tuning T4

O `SecureBERT-NER` usou split fixo `179/60/60`, três seeds (`42`, `123`, `2024`),
cinco epochs, cabeça BIO de 9 labels, máximo 512 e `stride=128`. A tabela mostra
`strict F1 / partial same-type F1`, média +/- DP nas diagonais e cruzamentos:

| Treino | Teste | Resultado |
| --- | --- | ---: |
| Muse original | Muse original | 0.3131 +/- 0.0072 / 0.4776 +/- 0.0044 |
| Muse original | overlay | 0.2403 +/- 0.0021 / 0.3699 +/- 0.0107 |
| overlay | Muse original | 0.2379 +/- 0.0047 / 0.3033 +/- 0.0079 |
| overlay | overlay (`full`) | **0.4336 +/- 0.0056 / 0.5528 +/- 0.0018** |

Na diagonal do overlay: `LoRA+` obteve `0.1061/0.3270`; `full` ponderado com
CCE obteve `0.4421/0.5429`; `full` com ROS em nível de documento obteve
`0.4410/0.5602` (strict/partial same-type). ROS usou replacement sampling,
pesos de presença limitados a `3x` e não reamostrou validation/test.

## Decisões finais

- Os 59 URLs coincidentes entre vinitvek e o corpus reconstruído são todos de JD
  Supra; devem ser marcados como potencial leakage/proveniência e excluídos de
  alegações de validação externa independente.
- Muse original e overlay são camadas distintas; ambas são silver, não as
  anotações gold manuais do artigo. O overlay e todas as validações T4 listadas
  acima estão concluídos.
- Resultados de substitutos, do Muse e do fine-tuning são `extension`; o
  benchmark `mrmoor` é `approximate`/validação externa. Não apresentar nenhum
  deles como reprodução fiel.
- Não publicar corpus original inexistente, texto de artigos, anotações por
  documento ou saídas por documento. Publicar somente agregados e metadados
  revisados, respeitando a licença do dataset e os direitos das fontes.
- O caminho autorizado para reprodução fiel continua sendo solicitar aos autores
  ou ao venue o SQLite e a amostra manual de 60 documentos; sem autorização,
  manter a validação externa separada.
