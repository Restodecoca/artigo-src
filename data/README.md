# Contrato de dados locais

O corpus original de notícias do artigo e suas anotações manuais estão
indisponíveis e não são distribuídos neste repositório. Armazene entradas locais
autorizadas em `data/raw/` ou `data/processed/`; ambos os paths são ignorados
pelo Git.

A camada de labels `Muse` original deve permanecer separada do
`adjudicated overlay`. O overlay é armazenado em
`data/processed/muse_corrected/`, sem sobrescrever os arquivos Muse originais.
Nenhuma dessas camadas deve ser descrita como as anotações gold manuais do
artigo.

## Como preparar entradas locais

Os arquivos de artigos, labels e resultados por documento não são distribuídos.
Para começar uma execução local, consulte os argumentos disponíveis nos
comandos abaixo; as saídas padrão ficam em `data/raw/`, ignorada pelo Git:

```powershell
uv run python scripts/data/prepare_muse_batches.py --help
uv run python scripts/data/fetch_vinitvek_articles.py --help
```

A recuperação de artigos completos requer URLs autorizadas e o Firecrawl CLI.
A anotação Muse é uma etapa separada: gere os lotes, realize/revise a anotação
fora do repositório e valide os arquivos locais com
`scripts/data/validate_muse_labels.py` ou
`scripts/data/validate_corrected_muse_labels.py`. Os runners T4 estão em
`scripts/colab/` e precisam dos arquivos privados preparados localmente.

## JSONL de anotação

Cada linha representa um documento:

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

## Organização local

- `data/raw/`: entradas autorizadas, fontes e labels Muse originais.
- `data/processed/`: overlays, archives e dados derivados locais.
- `data/*.json`: resultados agregados gerados pelos runners; são ignorados pelo
  Git e devem ser relacionados no `README.md` ou em `data/SEARCH_LOG.md`.

O arquivo `.env` também é local e ignorado. Ele pode conter `HF_TOKEN` para
publicações explicitamente autorizadas no Hugging Face; credenciais não devem
ser copiadas para datasets, logs ou documentação.

Não use um substituto público com este schema e o apresente como reprodução
`faithful`. Registre nos metadados do experimento o repositório, a licença, a
data de acesso e os desvios.
