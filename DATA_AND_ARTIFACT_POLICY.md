# Política de dados e artefatos

## Repositório público de revisão

O repositório público contém código-fonte, testes, configuração, documentação,
artigo, resultados agregados e exportações de anotação **sem os textos
integrais das notícias**. O objetivo é permitir revisão metodológica e auditoria
dos rótulos, offsets e decisões.

## Material restrito

Não faça commit nem publique:

- texto de artigos coletados ou páginas completas de notícias;
- arquivos compactados que contenham o campo `text` dos documentos;
- anotações ou exports com trechos copiados das notícias;
- notas livres de revisão que reproduzam conteúdo jornalístico;
- caches de modelos, checkpoints ou saídas geradas sem revisão;
- API keys, tokens ou arquivos `.env`;
- resultados por documento que permitam reconstruir os textos de origem.

As exportações públicas de anotação podem conter identificadores de documento,
offsets, rótulos, incerteza e metadados, desde que o campo `text` e as notas
livres tenham sido removidos. O pacote de liberação está descrito em
`data/muse-artifacts/PUBLIC_RELEASE.md`.

Exceção de revisão: a pasta `review-data/` contém os textos integrais e os
archives completos exclusivamente para avaliação acadêmica do professor. Esses
arquivos não podem ser redistribuídos. Antes de divulgar o repositório fora
desse contexto, remova `review-data/` ou restrinja seu acesso.

## Estados de reprodução

Todo experimento deve ser identificado como `faithful`, `approximate` ou
`extension`. O estado atual é `extension`: o corpus original do artigo está
indisponível, as validações usam as camadas `Muse` original e o overlay
adjudicado, e o ajuste fino foi executado com `LoRA+`, `full`, `CCE` e `ROS`.

Os candidatos públicos do Hugging Face registrados no projeto são
`reference_only`. A camada Muse original é silver, e o overlay tem o status
`adjudicated_overlay_not_original_manual_gold`. Nenhum deles equivale ao gold
manual original.

## Gate de publicação

Antes de publicar novos artefatos, registre:

1. fonte dos dados, licença, data de acesso e permissão de redistribuição;
2. revisões exatas dos modelos e versões das dependências;
3. procedimento de anotação e concordância entre anotadores;
4. métricas agregadas e limitações;
5. desvios em relação ao artigo original;
6. revisão de vazamento, duplicatas, links mortos e conteúdo sensível.

## Hugging Face

O token local em `.env` pode ser lido somente por comandos de publicação
explicitamente autorizados. Antes de publicar um dataset ou checkpoint, confirme
nome do repositório, licença, permissões de redistribuição e ausência de texto
protegido. Nunca registre o valor de `HF_TOKEN` em argumentos, logs ou artefatos.
