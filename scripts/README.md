# Catálogo de scripts

Os scripts são entradas de linha de comando. A lógica de domínio reutilizável
fica em `src/healthcare_ner_replication/`; os scripts remotos permanecem
autônomos porque `colab exec -f` transfere o corpo do arquivo, não o pacote
local inteiro.

## Pipeline

- `fetch_protocol_sample.py`: coleta a amostra alinhada ao protocolo.
- `fetch_vinitvek_articles.py`: recupera artigos completos a partir das URLs.
- `prepare_muse_batches.py`: prepara lotes para anotação Muse; pode remover
  lotes antigos no diretório de saída.
- `chunk_muse_batches.py`: divide lotes longos em chunks privados.
- `validate_muse_labels.py`: valida labels Muse originais.
- `validate_corrected_muse_labels.py`: valida o overlay adjudicado.
- `package_muse_archive.py`: empacota fonte e labels originais.
- `package_corrected_muse_archive.py`: empacota fonte e labels adjudicados.

## T4 e fine-tuning

- `run_colab_muse_validation.py`: validação SecureBERT-NER/APTNER contra Muse.
- `run_colab_securebert2_muse.py`: compatibilidade SecureBERT 2.0.
- `run_colab_candidate_probe.py`: sondagem agregada de candidatos.
- `run_colab_candidate_benchmark.py`: benchmark agregado de candidatos.
- `run_colab_loraplus_muse_sensitivity.py`: LoRA+, full fine-tuning, CCE
  ponderada e ROS, sempre em split documental fixo.

## Análise

Os diagnósticos reproduzíveis ficam em `scripts/analysis/` e consomem os
artefatos já gerados:

- `analyze_muse_diagnostic.py`: resume diagnósticos privados.
- `compare_muse_model_spans.py`: compara spans por modelo.
- `evaluate_span_postprocessing.py`: avalia reparos de spans.
- `measure_corpus_overlap.py`: mede sobreposição de URLs.
- `check_colab_windowing.py`: verifica janelas do archive.

## Slides

Os scripts de `slides/` e os scripts de manutenção de apresentações não fazem
parte desta limpeza e permanecem intocados.

## Segurança

Textos, labels, checkpoints, resultados por documento e caches ficam em
`data/raw/`, `data/processed/`, `artifacts/`, `checkpoints/` ou `models/`, todos
fora do commit. O `.env` local pode fornecer `HF_TOKEN` para operações
explicitamente autorizadas, mas o token nunca deve aparecer em logs, código ou
artefatos versionados.
