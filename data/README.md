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
