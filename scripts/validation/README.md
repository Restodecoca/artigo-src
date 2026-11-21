# Validação humana das anotações Muse

Ferramenta local para os revisores conferirem a categoria que a LLM Muse atribuiu
a cada entidade. O objetivo é produzir uma camada de auditoria humana independente
e comparável entre três revisores, sem publicar texto de artigos.

## Artefatos necessários

Os archives completos estão em `review-data/archives/` e contêm textos de
terceiros para revisão acadêmica. As exportações sem texto estão em
`data/muse-artifacts/`. Consulte `DATA_AND_ARTIFACT_POLICY.md`.

- `review-data/archives/vinitvek-articles-2023-muse-expanded.tar.gz` —
  camada Muse original, 314 registros, 299 mantidos, 2.103 entidades.
- `review-data/archives/muse_corrected.tar.gz` — overlay adjudicado,
  314 registros, 299 mantidos, 5.111 entidades.

Conferência dos archives:

```bash
cd data/muse-artifacts && sha256sum -c checksums.sha256
```

Extraia antes de usar; a página lê JSON/JSONL, não tar:

```bash
mkdir -p /tmp/muse/{original,overlay}
tar xzf review-data/archives/vinitvek-articles-2023-muse-expanded.tar.gz \
  -C /tmp/muse/original
tar xzf review-data/archives/muse_corrected.tar.gz \
  -C /tmp/muse/overlay
```

Os lotes ficam em:

```text
/tmp/muse/original/muse_batches/vinitvek-articles-2023/
/tmp/muse/overlay/muse_batches/vinitvek-healthcare-corrected/
```

Selecione **todos** os `batch_*.json` e `labels_batch_*.json` de uma das pastas
de uma vez. Não misture a camada original com o overlay. Os 15 documentos com
`keep=false` não têm entidades e não entram na fila de auditoria.

Os JSONs agregados em `data/` (`candidate_benchmark_*`, `external_*`) e o CSV
`healthcare_cyber_v10_hybrid_1066.csv` não servem para esta auditoria: eles têm
métricas agregadas ou metadados de URLs, não `text` + `entities` por documento.

Formatos aceitos pela página:

- **Pares de batches**: `batch_*.json` com `{id, text, metadata}` e
  `labels_batch_*.json` com `{id, entities: [{start, end, label}]}`.
- **Overlay adjudicado**: os mesmos arquivos, com `keep` no registro e
  `text` opcional dentro de cada entidade.
- **JSONL consolidado**: uma linha por documento, no formato de `data/README.md`,
  com `document_id`, `text` e `entities`.
- **JSON consolidado**: um objeto ou lista com `text` e `entities`.

Não misture a camada `Muse` original com o `adjudicated overlay`, porque os IDs
dos documentos se repetem e as decisões ficariam ambíguas. A página também
recusa restaurar um export cujo `dataset_key` não corresponda ao conjunto
carregado.

Conferência esperada depois de carregar:

| Camada | Documentos com entidades | Entidades |
| --- | ---: | ---: |
| Muse original | 299 | 2.103 |
| Overlay adjudicado | 299 | 5.111 |

A interface chama a camada carregada de “Muse”. Se você carregar o overlay
adjudicado, os rótulos comparados são os do overlay, não a sugestão Muse
original; descreva o relatório como auditoria da camada efetivamente carregada.

## Revisão

1. Abra `scripts/validation/muse_audit.html` no navegador. Para um ambiente mais
   previsível de `localStorage`:

   ```bash
   uv run python -m http.server 8765 --directory scripts/validation
   ```

   Depois acesse `http://localhost:8765/muse_audit.html`.

2. Preencha o campo **Revisor** com `dev1`, `dev2` ou `dev3`. O progresso é
   separado por revisor e por conjunto de dados.
3. Carregue os artefatos e comece pelo filtro **Pendentes**.
4. No modo **Cego** (recomendado), a sugestão Muse fica oculta até a resposta.
   Use o modo assistido apenas para conferência, não para medir concordância
   independente.
5. Atalhos: `1`–`4` categorizam, `0` marca “não é entidade”, `M` revela a Muse,
   `U` marca incerteza, `A` abre a inclusão de entidade digitada, `←`/`→` navegam.
   Com um trecho selecionado no texto, `1`–`4` (ou os botões de tipo) criam uma
   entidade com aquele tipo a partir da seleção; sem seleção, eles apenas
   categorizam a entidade atual.
6. Use a observação para spans inválidos, fusão/divisão de entidades ou casos
   ambíguos. A ferramenta não edita offsets de entidades existentes.
7. Para registrar uma entidade que a Muse não marcou, basta **selecionar o trecho**
   no texto (contexto ou documento completo) e clicar em `IDTY`/`ACT`/`VUL`/`LOC`
   (ou teclar `1`–`4`). Um aviso mostra o trecho selecionado antes do clique. Como
   alternativa para texto digitado/copiado, use **+ Adicionar entidade** (ou `A`),
   escolhendo a ocorrência e a categoria. A entidade entra na fila já categorizada,
   aparece no filtro **Adicionadas pelo revisor** e pode ser removida pelo botão
   **Remover entidade adicionada**. Ela é salva por revisor e exportada com
   `origin="custom"` e `muse_label` vazio, sem entrar no cálculo de concordância
   com a Muse.
8. Exporte **JSON** ao terminar. O CSV é opcional para inspeção em planilha.
9. Para retomar de um export, use **Restaurar revisão exportada**. É possível
   carregar o export antes dos artefatos: a aplicação fica pendente e ocorre
   automaticamente depois da leitura dos batches.

Cada revisor deve exportar seu próprio arquivo. Se os três usarem o mesmo
navegador/perfil, basta trocar o campo Revisor: as respostas ficam separadas.
Ainda assim, exporte antes de trocar de máquina ou limpar o navegador.

Para medir concordância entre humanos, os três devem revisar o mesmo conjunto
carregado. Se o objetivo for apenas dividir a cobertura em subconjuntos,
consolide cada subconjunto separadamente: o `compare_audits.py` rejeita exports
com `dataset_key` diferentes para não misturar dados.

A restauração exige o mesmo `dataset_key` do conjunto carregado; exports de
outro conjunto são recusados para não misturar a camada Muse original com o
overlay. Ela também não sobrescreve uma resposta local cujo `reviewed_at` seja
mais recente que o do arquivo importado. As respostas mantidas aparecem na
mensagem final; para forçar a versão do arquivo, limpe a revisão local antes de
importar.

## Consolidação

```bash
uv run python scripts/validation/compare_audits.py \
  data/muse-artifacts/audits/gabriel_rodrigues_overlay_2026-11-20.json \
  data/muse-artifacts/audits/gabriel_carlos_2026-11-20.json \
  --output data/muse-artifacts/audits/comparison_2026-11-20.json
```

As anotações iniciais foram geradas pelo Muse Spark, modelo de linguagem da
Meta, e posteriormente revisadas manualmente. O arquivo de Gabriel Rodrigues representa o overlay
na comparação. Seu formato de exportação não estabelece, por si só, como
foi realizada a anotação humana. A revisão completa do Angelo e a camada de consenso estão em
`review-data/archives/muse_reviewed.tar.gz` e
`muse_consensus.tar.gz`; os detalhes estão em `docs/04_anotacoes_assistidas.md`.

O relatório contém apenas dados agregados: cobertura, concordância com a Muse,
Cohen's kappa por revisor, métricas por categoria, matriz de confusão,
concordância par a par e Fleiss' kappa entre os revisores. Notas e texto das
entidades não entram no agregado.

Use `--json` para imprimir o relatório completo em vez do resumo de terminal.

## Interpretação

- **Acurácia vs. Muse**: proporção de decisões humanas iguais à sugestão.
- **Cohen's kappa**: concordância com a Muse corrigida pelo acaso.
- **Fleiss' kappa**: concordância entre os três revisores nos itens que todos
  responderam.
- **Cobertura**: itens revisados ÷ entidades do conjunto.
- **Confident accuracy**: acurácia ignorando itens marcados como incertos.
- **Muse revelada**: itens em que o revisor viu a sugestão antes de responder;
  o agregado reporta essa contagem para transparentizar possível viés.

O relatório não transforma a camada Muse em gold manual. Ele mede a auditoria
humana de uma camada `silver`/overlay e deve ser descrito como extensão.

## Privacidade

- A página não faz requisições de rede; os arquivos são lidos pelo navegador.
- O progresso fica no `localStorage` do navegador.
- Os exports contêm IDs de documento, spans, rótulos, incerteza, notas, entidades
  adicionadas (`origin="custom"`, `custom_entities`) e a lista de itens cuja
  sugestão Muse foi revelada. Exports com texto não devem ser versionados.
  A versão pública usa apenas IDs, offsets, rótulos e metadados.
- `data/processed/` e `auditoria_muse_*.json|csv` são ignorados pelo Git.

## Testes

```bash
uv run pytest tests/test_compare_audits.py tests/test_muse_audit_html.py -q
uv run ruff check scripts/validation tests/test_compare_audits.py
uv run pyright scripts/validation/compare_audits.py
```

A página é testada manualmente em navegador (ou com um DOM headless) porque o
teste automatizado do repositório é estático e não executa JavaScript.
