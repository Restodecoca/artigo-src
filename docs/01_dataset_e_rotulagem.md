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

## Camadas de anotação

O projeto preserva duas camadas independentes:

- **Muse original:** pré-anotação assistida, com 2.103 entidades nos 299
  documentos retidos. É uma camada *silver*, não um gold manual verificado.
- **Overlay adjudicado:** revisão em sete lotes seguida de uma segunda etapa de
  adjudicação. Contém 5.111 entidades nos mesmos 299 documentos. Não sobrescreve
  nem substitui as labels originais.

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

## Referência

Paim, R.; Ignaczak, L. *An Analysis of Pre-trained Models to Identify
Cybersecurity Incidents Entities in the Healthcare Industry*. SBSEG, 2025.
DOI: [10.5753/sbseg_estendido.2025.10726](https://doi.org/10.5753/sbseg_estendido.2025.10726).
