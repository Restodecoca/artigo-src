# Contrato de dados

O corpus original de notícias do artigo e suas anotações manuais estão
indisponíveis. Este repositório público contém exportações de anotação sem os
textos integrais, resultados agregados e o código de preparação e avaliação.

## Dados públicos e restritos

- Público: identificadores de documento, offsets, rótulos, metadados agregados,
  resultados agregados e exportações sem o campo `text`.
- Restrito: textos completos das notícias, arquivos `batch_*.json` com `text`,
  arquivos compactados das camadas e notas que copiem trechos jornalísticos.

Os arquivos completos ficam em `review-data/`, publicado exclusivamente para a
revisão acadêmica do professor. Consulte
`data/muse-artifacts/PUBLIC_RELEASE.md` para a lista do que é público e do que
permanece restrito.

A camada de labels `Muse` original deve permanecer separada do overlay
adjudicado. Nenhuma delas deve ser descrita como as anotações gold manuais do
artigo.

## Como preparar entradas locais

Para executar a coleta ou a validação, são necessários os textos autorizados e
os arquivos completos. As saídas padrão ficam em `data/raw/`, ignorada pelo Git:

```powershell
uv run python scripts/data/prepare_muse_batches.py --help
uv run python scripts/data/fetch_vinitvek_articles.py --help
```

A recuperação de artigos completos requer URLs autorizadas e o Firecrawl CLI.
A anotação é uma etapa separada: gere os lotes, realize a revisão e valide os
arquivos locais com `scripts/data/validate_muse_labels.py` ou
`scripts/data/validate_corrected_muse_labels.py`. Os runners T4 estão em
`scripts/colab/` e precisam dos arquivos completos preparados localmente.

## JSONL de anotação

O formato abaixo é local. O campo `text` não deve ser versionado no repositório
público.

```json
{
  "document_id": "local-0001",
  "source": "SC Magazine",
  "published_date": "2023-05-01",
  "text": "local article text",
  "entities": [
    {"start": 0, "end": 12, "label": "IDTY"}
  ]
}
```

Os offsets são spans de caracteres zero-based e half-open dentro de `text`. As
labels devem ser uma de `IDTY`, `ACT`, `VUL` ou `LOC`. O campo `source` é mantido
para que os resultados possam ser reportados por portal, como no artigo.

## Organização

- `data/raw/`: entradas autorizadas e labels completas, ignoradas pelo Git.
- `data/muse-artifacts/`: exportações públicas sem texto, manifestos, resultados
  agregados e proveniência; ver o README local.
- `data/processed/`: overlays e dados derivados locais, ignorados pelo Git.
- `data/*.json`: resultados agregados gerados pelos runners; são ignorados pelo
  Git e devem ser relacionados no `README.md` ou em `data/SEARCH_LOG.md`.

O arquivo `.env` é local e ignorado. Ele pode conter `HF_TOKEN` para publicações
autorizadas; credenciais não devem ser copiadas para datasets, logs ou
documentação.

Não use um substituto público com este schema e o apresente como reprodução
`faithful`. Registre nos metadados o repositório, a licença, a data de acesso e
os desvios.
