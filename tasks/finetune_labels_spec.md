# Spec: Sensibilidade de Labels com LoRA+, Full Fine-Tuning, CCE e ROS

## Objetivo

Medir como o SecureBERT-NER se adapta à camada de anotação usada no
fine-tuning. Comparar receitas idênticas treinadas com os labels Muse
originais e com `adjudicated_muse_overlay_v1`, avaliando cada modelo contra as
duas camadas nos mesmos documentos held-out. O protocolo inclui LoRA+, full
fine-tuning, class-weighted categorical cross-entropy (CCE) e document-level
repeated oversampling (ROS).

Este protocolo foi executado. É uma `extension`, não uma reprodução fiel nem
uma avaliação human-gold.

## Protocolo Fixo

- Model: `CyberPeace-Institute/SecureBERT-NER`, revision
  `7f935a4f7db13697580c881e381bb2636dfa779a`.
- Hardware: Colab Tesla T4, FP16, max sequence length 512, window stride 128.
- Split: divisão determinística de documentos com seed `2024`, aproximadamente
  60/20/20 train/validation/test; as duas camadas usam a mesma divisão.
- Training seeds: `42`, `123` e `2024`.
- Training: cinco epochs, AdamW, encoder LR `2e-5`, LoRA+ B/A LR ratio `8`,
  fresh classifier LR `1e-3`, weight decay `0.01`, warmup `10%`, gradient
  clipping `1.0`. Full fine-tuning usa os mesmos encoder/classifier learning
  rates sem adapters. Weighted CCE usa pesos normalizados de frequência de
  tokens, inverso da raiz quadrada, calculados somente no training split. ROS
  usa replacement sampling com class-presence weights limitados a `3x`.
- PEFT: LoRA em `query` e `value` do RoBERTa, com trainable `classifier` head.
- Labels: fresh 9-label BIO head (`O`, `B/I-IDTY`, `B/I-ACT`, `B/I-VUL`,
  `B/I-LOC`) para que as duas camadas tenham o mesmo output space.
- Evaluation: strict span F1 e partial same-type span F1, com one-to-one
  matching; resultados por seed e média/std.
- Status: executado para LoRA+, full fine-tuning, weighted CCE e ROS. ROS não
  reamostra validation nem test.

## Matriz

| Model trained on | Evaluate against Muse | Evaluate against adjudicated |
| --- | ---: | ---: |
| LoRA+ / Muse original | yes | yes |
| LoRA+ / adjudicated overlay | yes | yes |
| Full / Muse original | yes | yes |
| Full / adjudicated overlay | yes | yes |
| Full + weighted CCE / Muse original | yes | yes |
| Full + weighted CCE / adjudicated overlay | yes | yes |
| Full + ROS / Muse original | yes | yes |
| Full + ROS / adjudicated overlay | yes | yes |

## Artifacts

- Runner: `scripts/run_colab_loraplus_muse_sensitivity.py`.
- Aggregate LoRA+ result: `data/finetune_loraplus_muse_sensitivity_t4_v2.json`.
- Aggregate full result: `data/finetune_full_muse_sensitivity_t4.json`.
- Aggregate weighted-CCE result:
  `data/finetune_full_weighted_cce_muse_sensitivity_t4.json`.
- Aggregate ROS result: `data/finetune_full_ros_muse_sensitivity_t4.json`.
- Archive inputs: `data/raw/vinitvek-articles-2023-muse-expanded.tar.gz` e
  `data/processed/muse_corrected.tar.gz`.

## Limites

- Não dividir janelas sobrepostas entre train e test.
- Não selecionar hiperparâmetros usando o test split.
- Não sobrescrever labels Muse ou adjudicados.
- Não reportar o resultado como reprodução do artigo nem como prova de que o
  overlay está objetivamente correto.
- ROS é uma ablação separada: amostrar documentos de treino com replacement
  usando class-presence weights limitados a `3x`; nunca reamostrar validation ou
  test.

## Critérios de sucesso

- As condições de treino completam os três seeds sem NaN, OOM ou checkpoints ausentes.
- Split e document IDs são idênticos entre as condições.
- A saída contém métricas por seed e agregadas para os quatro pareamentos de anotação train/test.
- Runtime T4, checkpoint revision, hashes dos arquivos, configuração de treino e falhas são registrados.
- O protocolo executado registra os artefatos agregados de LoRA+, full fine-tuning, weighted CCE e ROS.
