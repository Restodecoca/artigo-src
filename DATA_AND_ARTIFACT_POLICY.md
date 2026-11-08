# Política de dados e artefatos

## Repositório público

O repositório pode conter código-fonte, testes, configuração, documentação,
metadados de datasets, identificadores de modelos, fixtures sintéticos e
resultados agregados.

## Material restrito

Não faça commit nem publique:

- texto de artigos coletados ou dumps completos de notícias;
- anotações manuais que reproduzam conteúdo protegido de artigos;
- caches de modelos, checkpoints ou saídas geradas sem revisão;
- API keys, Kaggle tokens, Hugging Face tokens ou arquivos `.env`;
- resultados por documento que permitam reconstruir ou identificar artigos de
  origem.

Exceção operacional: somente neste repositório privado, os archives de anotação
em `data/muse-artifacts/` podem ser versionados para validação em pares. Eles
não podem ser redistribuídos publicamente e devem ser removidos do histórico
antes de qualquer abertura do repositório.

## Estados de reprodução

Todo experimento deve ser identificado como `faithful`, `approximate` ou
`extension`. O estado atual do projeto é `extension`: o corpus original do
artigo está indisponível, as validações T4 usam as camadas `Muse` original e
`adjudicated overlay`, e o fine-tuning foi executado com `LoRA+`, `full`, `CCE`
e `ROS`.

Os candidatos públicos do Hugging Face atualmente registrados no projeto são
`reference_only`; eles não contêm o corpus original de notícias da área da
saúde. A camada Muse original é silver, e o overlay possui o status técnico
`adjudicated_overlay_not_original_manual_gold`; nenhum dos dois equivale ao
conjunto gold manual original.

## Gate de publicação

Antes de apresentar afirmações de publicação, o projeto deve registrar:

1. fonte dos dados, licença, data de acesso e permissão de redistribuição;
2. revisões exatas dos modelos e versões das dependências;
3. procedimento de anotação e concordância entre anotadores;
4. métricas em nível de documento e de entidade, com estimativas de incerteza;
5. todos os desvios em relação ao artigo original;
6. revisão de vazamento, duplicatas, links mortos e conteúdo sensível.

## Hugging Face

O token local em `.env` pode ser lido somente por comandos de publicação
explicitamente autorizados. Antes de publicar um dataset ou checkpoint, confirme
nome do repositório, licença, permissões de redistribuição e se o conteúdo não
contém texto protegido ou resultados que reconstituam artigos. Nunca registre o
valor de `HF_TOKEN` e nunca o inclua em argumentos, logs ou artefatos.
