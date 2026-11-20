# NER de cibersegurança em notícias de saúde

Projeto de reconstrução metodológica e extensão do estudo de Paim e Ignaczak
sobre reconhecimento de entidades em incidentes cibernéticos na área da saúde.
O corpus e as anotações manuais originais não estavam disponíveis; os
experimentos locais usam uma base própria e **não são uma reprodução fiel** dos
dados ou resultados do artigo.

## O que foi feito

As anotações iniciais foram geradas pelo Muse Spark, modelo de linguagem da
Meta, e posteriormente revisadas manualmente pelos anotadores humanos.
Essa revisão incluiu correções dos trechos e das categorias, além da
inclusão de entidades ausentes. Não se trata de anotação humana do zero.

- Construída uma amostra própria: 329 URLs, 314 textos extraídos e 299 notícias
  retidas.
- Mantida a anotação Muse silver original (2.103 entidades) e criado um overlay
  adjudicado separado (5.111 entidades).
- Construída uma camada separada de 687 adições assistidas por IA e verificadas
  por humano, elevando o total para 5.798 entidades.
- Revisão completa do overlay (9.318 entidades) e camada de consenso com três
  anotações; a validação em pares ficou entre 98,8% e 99,5%.
- Avaliados SecureBERT-NER e SecureBERT-APTNER e executados experimentos de
  fine-tuning com Full, LoRA+, CCE ponderada e ROS.

| Experimento no overlay | Strict F1 | Partial F1 / same-type |
| --- | ---: | ---: |
| SecureBERT-NER, inferência | 0,0809 | 0,2617 / 0,2486 |
| SecureBERT-APTNER, inferência | 0,0507 | 0,2933 / 0,2891 |
| Full fine-tuning, teste de 60 docs | 0,4336 ± 0,0056 | 0,5528 ± 0,0018 (same-type) |

Um *short paper* de 4 páginas com resumo/abstract, baseado nesses resultados,
está em [`paper/`](paper/README.md) (template LaTeX SBC/WCAMA). A ferramenta de
auditoria permite adicionar novas entidades encontradas pelo revisor, marcadas
como `origin=custom` na exportação.

Resultados e limitações estão detalhados em [`docs/`](docs/README.md), incluindo
a [camada aumentada e os experimentos preliminares](docs/04_anotacoes_assistidas.md). Os
artefatos restritos de anotação Muse usados na validação em pares estão em
[`data/muse-artifacts/`](data/muse-artifacts/README.md) neste repositório
privado; eles não devem ser redistribuídos publicamente.

## Começar

Requisitos: Python 3.12+ e [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
uv run pytest
uv run ruff check src tests scripts
uv run pyright
```

Para executar inferência/modelos ou fine-tuning, consulte os extras opcionais
em `pyproject.toml` e os runners em `scripts/colab/`. Os runners enviados ao
Colab são autônomos por requisito do `colab exec -f`.

## Estrutura

```text
src/healthcare_ner_replication/  lógica reutilizável
scripts/data/                    coleta, preparação, validação e archives
scripts/colab/                   runners remotos/autônomos
scripts/analysis/                análise de artefatos agregados
scripts/validation/              auditoria humana e concordância das labels Muse
scripts/local/                   verificações locais de modelos
scripts/presentations/           utilitários de apresentações
paper/                          short paper LaTeX (4 páginas, abstract)
tests/                           testes automatizados
configs/                         protocolo legível por máquina
tasks/                           especificações experimentais
docs/                            relatórios e apresentação do Marco 3
```

O catálogo e os comandos de cada grupo estão em [`scripts/README.md`](scripts/README.md).
Para contribuir, leia [`CONTRIBUTING.md`](CONTRIBUTING.md). A política de
dados, credenciais e artefatos está em
[`DATA_AND_ARTIFACT_POLICY.md`](DATA_AND_ARTIFACT_POLICY.md).

## Privacidade e limites

Não versionar `.env`, tokens, texto de artigos, labels por documento,
checkpoints ou saídas detalhadas, exceto os archives privados de validação em
`data/muse-artifacts/` previstos na exceção operacional de
`DATA_AND_ARTIFACT_POLICY.md`; eles não podem ser redistribuídos publicamente.
O `.env.example` é apenas um modelo sem credenciais. Leia `data/README.md` antes
de trabalhar com dados locais.

O overlay é uma camada adjudicada de uma extensão, não o gold manual original.
O estado e as decisões sobre fontes estão em `data/SEARCH_LOG.md`; os
resultados devem ser interpretados dentro desses limites.
