# Dataset e processo de rotulagem

## Objetivo

O projeto reconstrói o método do artigo de Paim e Ignaczak usando uma base
própria de notícias. O corpus e as anotações manuais originais do artigo não
estavam disponíveis; portanto, os resultados locais são uma extensão, não uma
reprodução dos dados originais.

## Construção do corpus

As URLs vieram do dataset público `vinitvek/cybersecurityattacks`, filtradas
para o setor de saúde e o período de 2023. As URLs foram usadas para recuperar
o texto completo das páginas de origem.

| Etapa | Quantidade |
| --- | ---: |
| URLs únicas selecionadas | 329 |
| Textos extraídos com sucesso | 314 |
| Documentos retidos após triagem | 299 |
| Falhas de extração / páginas descartadas | 15 / 15 |

Os textos completos e os resultados por documento são restritos e não são
incluídos neste repositório.

## Referências de anotação

As anotações iniciais foram geradas pelo Muse Spark, modelo de linguagem da
Meta. Os anotadores revisaram manualmente os trechos e suas categorias,
corrigiram marcações e acrescentaram entidades ausentes. O artigo utiliza
duas referências sobre os mesmos 299 documentos. Esse procedimento não é
uma anotação humana do zero.

A referência revisada, denominada overlay nos artefatos, contém 5.111
entidades. A referência de consenso reúne 9.318 entidades e inclui menções
repetidas da mesma entidade no texto. As versões são mantidas separadas.

A cobertura não é uniforme. Na referência de consenso, 4.640 trechos têm
três registros de anotação, 10 têm dois e 4.668 pertencem apenas à revisão
final. A concordância deve ser interpretada nos trechos compartilhados.

Contagem do overlay: `IDTY=2.627`, `ACT=1.747`, `LOC=672` e `VUL=65`.

| Label | Significado no protocolo |
| --- | --- |
| `IDTY` | Organização ou instituição |
| `ACT` | Ação ou tipo de ataque |
| `VUL` | Vulnerabilidade |
| `LOC` | Localidade geográfica |

A validação automatizada verificou estrutura, offsets, texto, schema e spans
malformados/sobrepostos. Essa verificação não estabelece, por si só, a correção
semântica das anotações. O overlay também não é o gold manual original do
artigo.

A ferramenta `scripts/validation/muse_audit.html` apoia a anotação manual e a
conferência das categorias. Os arquivos de cada revisor são consolidados por
`scripts/validation/compare_audits.py`. O nome Muse na interface e nos
caminhos remete à origem automática das sugestões. A revisão dessas
sugestões foi realizada manualmente. As exportações sem texto estão em
`data/muse-artifacts/` e os dados completos em `review-data/`. O procedimento
e as métricas de concordância estão em `scripts/validation/README.md`.

## Referência

Paim, R.; Ignaczak, L. *An Analysis of Pre-trained Models to Identify
Cybersecurity Incidents Entities in the Healthcare Industry*. SBSEG, 2025.
DOI: [10.5753/sbseg_estendido.2025.10726](https://doi.org/10.5753/sbseg_estendido.2025.10726).
