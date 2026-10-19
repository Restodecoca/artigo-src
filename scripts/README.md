# Scripts e comandos

`src/healthcare_ner_replication/` contém lógica reutilizável. Os scripts em
`scripts/colab/` são autônomos: o `colab exec -f` transfere o arquivo ao runtime
remoto, não o pacote Python inteiro.

## Por categoria

### `scripts/data/`

- `fetch_protocol_sample.py`: seleciona uma amostra de metadados alinhada ao artigo.
- `fetch_vinitvek_articles.py`: recupera texto completo a partir das URLs.
- `prepare_muse_batches.py` e `chunk_muse_batches.py`: preparam lotes locais
  para anotação; os arquivos podem conter texto protegido e ficam em `data/raw/`.
- `validate_muse_labels.py` e `validate_corrected_muse_labels.py`: validam as
  camadas Muse original e adjudicada.
- `package_muse_archive.py` e `package_corrected_muse_archive.py`: empacotam os
  dados locais correspondentes.

Exemplo de validação local (a saída contém apenas contagens agregadas):

```powershell
uv run python scripts/data/validate_corrected_muse_labels.py data/raw/vinitvek-articles-2023 data/processed/muse_corrected
```

### `scripts/colab/`

Runners autônomos de validação e fine-tuning:

- `run_colab_muse_validation.py` e `run_colab_securebert_validation.py`;
- `run_colab_securebert2_muse.py`;
- `run_colab_candidate_probe.py` e `run_colab_candidate_benchmark.py`;
- `run_colab_loraplus_muse_sensitivity.py` (LoRA+, Full, CCE e ROS).

Exemplos de envio:

```powershell
colab exec -f scripts/colab/run_colab_muse_validation.py
colab exec -f scripts/colab/run_colab_loraplus_muse_sensitivity.py
```

### `scripts/analysis/`

Ferramentas para resumir diagnósticos, comparar spans, avaliar pós-processamento,
medir sobreposição de corpus e verificar windowing. Usam artefatos já gerados;
os diagnósticos por documento continuam privados.

### `scripts/local/` e `scripts/presentations/`

`local/` contém smoke tests locais de modelos. `presentations/` contém utilitários
para editar/gerar materiais de apresentação; eles não fazem parte do pipeline de
dados ou avaliação.

## Segurança

Antes de executar coleta, preparação ou empacotamento, confirme os paths de
entrada e saída. Não publicar `.env`, tokens, texto de artigos, labels por
documento, checkpoints ou resultados detalhados. Consulte
`DATA_AND_ARTIFACT_POLICY.md` e `data/README.md`.
