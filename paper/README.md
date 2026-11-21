# Artigo de Segurança em Redes de Computadores (4 páginas)

Template LaTeX extraído de `2026_WCAMA_Dataset_Paper.zip` e adaptado para um
*short paper* de 4 páginas com `resumo` e `abstract` em português/inglês.

## Conteúdo

O artigo apresenta uma reconstrução metodológica e extensão do estudo de Paim
e Ignaczak. Não é uma reprodução numérica do original, pois usa corpus e
anotações próprios. O recorte prioriza:

- 329 URLs selecionadas, 314 textos extraídos e 299 notícias retidas;
- diferenças entre o protocolo original e a coleta/anotação local;
- referência revisada (`overlay`, 5.111 menções) e referência consolidada
  (`consensus` nos arquivos, 9.318 menções, com cobertura parcial pelos três
  anotadores);
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
misturá-la com a série anterior de outras receitas. As exportações públicas
de anotação omitem os textos integrais. Os dados completos estão em
`review-data/`, para revisão acadêmica.

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
- `tables/`: critérios de anotação, contagens por referência, inferência e
  ajuste fino, além de auxiliares não incluídas.
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

## Notas de revisão

O artigo usa menção como unidade, definida por documento, limites em
caracteres e categoria. As duas referências contêm ocorrências repetidas
em posições distintas. Uma inspeção dos arquivos, sem alterar os dados,
confirmou 4.649 menções idênticas entre revisada e consolidada. Há 462
menções tipadas exclusivas da revisada e 4.669 exclusivas da consolidada.
Assim, a consolidada não é um superconjunto da revisada. Ela corresponde
às marcações finais da revisão, com conciliação dos rótulos nos limites
coincidentes.

As contagens da consolidada são `IDTY=5.041`, `ACT=3.255`, `VUL=115` e
`LOC=907`. Não houve duplicatas idênticas nem sobreposições de referência
nos arquivos inspecionados. O critério de todas as menções é uma diretriz
da revisão, não uma garantia de exaustividade sem auditoria independente.

A concordância já registrada para a auditoria em pares do overlay é:
5.050 acordos em 5.111 decisões, 98,8% e kappa 0,9802. A referência ficou
visível em 4.787 decisões. Não se trata de concordância independente de
limites nem de mensuração da descoberta de entidades.
Esse par é a camada de Gabriel Rodrigues e a auditoria de Gabriel Machado,
identificada como Gabriel Carlos no arquivo de comparação. Esse valor
não representa concordância dos três anotadores na referência consolidada.

O artigo passou a reportar a concordância conjunta das três anotações nos
4.640 trechos com marcação positiva em todas elas. Foram 4.618 rótulos
unânimes e 22 não unânimes, com proporção de unanimidade 0,9952586207 e
kappa de Fleiss 0,9945813277. O cálculo usa `fleiss_kappa` de
`scripts/validation/compare_audits.py`, alinhando por documento, início e
fim, sem deduplicação por forma textual. Decisões `NONE` não entram nessa
interseção de menções positivas. A concordância média dos pares usada na
fórmula de Fleiss difere da proporção de unanimidade.

O denominador é condicionado à interseção. Uma camada é a projeção do
overlay, e houve exposição à referência na auditoria. Portanto, o índice
não deve ser apresentado como anotação cega independente nem como
avaliação das omissões ou dos 4.668 trechos de anotação única.

O treino da consolidada reúne as três anotações e permanece na tabela de
ajuste completo. Cada uma das duas condições de referência foi repetida
com três sementes. Esses três treinamentos por condição não correspondem
a três treinamentos separados por anotador. O histórico local registra
a comparação revisada versus consolidada, não uma matriz de três
condições individuais de anotador.

A referência de Fleiss foi incluída para documentar a medida conjunta.
A referência geral de BERT permanece no arquivo bibliográfico, mas deixou
de ser citada no PDF para priorizar as fontes diretamente usadas e manter
o limite de quatro páginas.

Os rótulos dos checkpoints foram conferidos nas revisões fixadas de seus
`config.json`. O inventário NER usa BIO e o APTNER usa BIOES. A conversão do
runner preserva IDTY, ACT e LOC, une VULID e VULNAME em VUL e descarta
outras categorias. O agrupamento é o `simple` da pipeline, sem alegar
uma avaliação independente da adequação dessa decodificação a BIOES.

Na inferência, o runner reserva dois tokens especiais, alinha as janelas
a palavras e remove apenas duplicatas exatas de limites e categoria.
No ajuste, utiliza as janelas de transbordamento do tokenizador e nove
rótulos BIO. O runner usa AdamW, taxas de 0,00002 na base e 0,001 no
classificador, decaimento de pesos 0,01 e aquecimento de aproximadamente
10% dos passos. Avalia os pesos da última época, sem seleção por validação.
O lote padrão é 4, com acumulação de gradientes 2. Esses últimos valores
são padrões do runner, não uma nova medição dos experimentos.

A inspeção também identificou notícias em italiano, além das fontes em
inglês. Não foi executado classificador de idioma nem estimada sua
distribuição completa. Os resultados existentes não foram recalculados
por idioma.

O repositório público está em `https://github.com/Restodecoca/artigo-src`.
As exportações de anotação omitem os textos integrais. O pacote
`review-data/` reúne os dados completos para revisão acadêmica e não deve ser
redistribuído.
