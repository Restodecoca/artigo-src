# Short paper (4 páginas), formato SBC / WCAMA

Template LaTeX extraído de `2026_WCAMA_Dataset_Paper.zip` e adaptado para um
*short paper* de 4 páginas com `resumo` e `abstract` em português/inglês.

## Conteúdo

O rascunho descreve o conjunto de dados deste repositório:

- 329 URLs selecionadas, 314 textos extraídos e 299 notícias retidas;
- camada Muse (`silver`, 2.103 entidades) e overlay adjudicado (5.111 entidades);
- camada separada de 687 adições assistidas por IA e verificadas por humano,
  totalizando 5.798 entidades;
- avaliação de SecureBERT-NER/APTNER nas camadas Muse, overlay e aumentada;
- resultados de fine-tuning (Full, LoRA+, CCE, ROS) e um experimento preliminar
  na camada aumentada;
- ferramenta local de auditoria, incluindo a adição de entidades pelo revisor.

Os números foram retirados de `README.md`, de `docs/01_dataset_e_rotulagem.md`,
`docs/02_avaliacao_modelos.md`, `docs/03_finetuning_e_verificacoes.md` e
`docs/04_anotacoes_assistidas.md`. Textos de artigos e anotações por documento
**não** são incluídos.

## Compilação

Requer TeX Live com `pdflatex` e `bibtex`:

```bash
cd paper
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

O resultado é `main.pdf` com exatamente 4 páginas. O arquivo PDF e os artefatos
de compilação (`.aux`, `.bbl`, `.blg`, `.log`, `.out`) são gerados localmente e
não devem ser versionados.

## Arquivos

- `main.tex`: preâmbulo, título, autores, resumo/abstract e inclusão das seções.
- `sections/`: introdução, corpus, experimentos e conclusão.
- `tables/`: tabelas de corpus, acrônimos e comparação entre camadas.
- `references.bib`: referências em estilo ABNT numérico (`abntex2-num`).
- `sbc-template.sty`, `sbc.bst`: arquivos do template original.

## Ajustes antes da submissão

- Confirmar autores, afiliação, e-mail e ORCID no preâmbulo de `main.tex`.
- O pacote `orcidlink` do template foi substituído por um comando simples porque
  conflita com o `babel` nesta versão do TeX Live; se o ambiente de submissão
  suportar, basta restaurar `\usepackage{orcidlink}`.
- Conferir os dados bibliográficos das referências no sistema do evento.
