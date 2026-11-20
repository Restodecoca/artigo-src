# Artigo de Segurança em Redes de Computadores (4 páginas)

Template LaTeX extraído de `2026_WCAMA_Dataset_Paper.zip` e adaptado para um
*short paper* de 4 páginas com `resumo` e `abstract` em português/inglês.

## Conteúdo

O artigo apresenta uma reconstrução metodológica e extensão do estudo de Paim
e Ignaczak. Não é uma reprodução numérica do original, pois usa corpus e
anotações próprios. O recorte prioriza:

- 329 URLs selecionadas, 314 textos extraídos e 299 notícias retidas;
- diferenças entre o protocolo original e a coleta/anotação local;
- referência revisada (`overlay`, 5.111 entidades) e referência de consenso
  (9.318 entidades, com cobertura parcial pelos três anotadores);
- precisão, revocação e F1 dos dois modelos sem ajuste, nos 299 documentos;
- uma série pareada de ajuste completo (`Full`) nas duas referências, com
  179 documentos de treino, 60 de validação e 60 de teste, e três seeds;
- anotações iniciais geradas pelo Muse Spark, modelo de linguagem da Meta,
  seguidas de revisão manual humana;
- limitações das comparações, da cobertura entre anotadores e da disponibilidade.

A metodologia identifica o Muse Spark 1.3 como modelo de linguagem da Meta e
distingue as sugestões automáticas da revisão manual dos anotadores.
Experimentos preliminares arquivados e as demais configurações de ajuste
permanecem documentados separadamente em `docs/`.
As tabelas de corpus e de siglas foram preservadas como arquivos auxiliares,
mas não são incluídas no PDF.

Os números foram retirados de `README.md`, de `docs/01_dataset_e_rotulagem.md`,
`docs/02_avaliacao_modelos.md`, `docs/03_finetuning_e_verificacoes.md` e
`docs/04_anotacoes_assistidas.md` e do resultado agregado
`data/muse-artifacts/results/muse_validation_vinitvek_corrected_t4.json`.
A comparação de ajuste fino usa apenas a série pareada descrita na seção
“Treino na camada de consenso” de `docs/04_anotacoes_assistidas.md`, sem
misturá-la com a série anterior de outras receitas. Textos de artigos e
anotações por documento **não** são redistribuídos publicamente.

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
- `tables/`: tabelas de inferência e ajuste fino, além de auxiliares não incluídas.
- `references.bib`: referências em formato SBC (`sbc.bst`).
- `sbc-template.sty`, `sbc.bst`: arquivos do template original.

## Ajustes antes da submissão

- Autores e emails constam no preâmbulo de `main.tex`, com o domínio comum
  `@unifesspa.edu.br`: Gabriel S. Rodrigues (`gabriel.s_r`), Gabriel Machado
  (`gabrielcarlosnm`) e Angelo Rodrigues (`angelo.rodrigues`).
- As referências seguem o formato SBC do template (`sbc.bst`), com nomes
  completos dos eventos e DOIs. Os dados foram conferidos nas fontes
  oficiais da SBC, ACL, IEEE/Crossref, Springer/EAI e Meta.
- Os DOIs também constam em `note`, pois o estilo original não imprime o
  campo `doi`. A referência da Meta identifica a origem do Muse Spark.
