# Protocolo: sensibilidade às labels com fine-tuning

## Objetivo

Medir como o SecureBERT-NER se adapta à camada de anotação usada no treino.
Comparar LoRA+, fine-tuning completo (*Full*), entropia cruzada categórica
ponderada (CCE) e sobreamostragem de documentos (ROS). Cada condição é avaliada
contra as camadas Muse original e overlay adjudicado, nos mesmos documentos
reservados para teste.

O protocolo foi executado como uma `extension`; não é reprodução fiel nem
avaliação contra o gold manual original.

## Configuração fixa

- Modelo: `CyberPeace-Institute/SecureBERT-NER`, revisão
  `7f935a4f7db13697580c881e381bb2636dfa779a`.
- Hardware: Tesla T4 no Colab, FP16, sequência máxima 512 e `stride=128`.
- Split documental determinístico: seed `2024`; `179/60/60` documentos para
  treino/validação/teste. O mesmo split é usado nas duas camadas.
- Seeds de treino: `42`, `123` e `2024`; cinco épocas.
- Otimizador AdamW; taxa do encoder `2e-5`, taxa da cabeça classificadora nova
  `1e-3`, weight decay `0.01`, warmup de 10% e clipping de gradiente `1.0`.
- LoRA+ usa adaptadores em `query` e `value`, rank 8, alpha 16 e dropout 0.1;
  razão de learning rate B/A igual a 8.
- A cabeça de classificação BIO tem nove rótulos: `O` e `B/I` para `IDTY`,
  `ACT`, `VUL` e `LOC`.
- CCE ponderada usa pesos por frequência de tokens, inverso da raiz quadrada,
  calculados somente no split de treino.
- ROS reamostra documentos de treino com reposição, com pesos de presença de
  classe limitados a `3x`. Validação e teste nunca são reamostrados.
- Métricas: Strict span F1 e Partial same-type span F1 com pareamento um-a-um;
  registrar valores por seed e média/desvio padrão.

## Matriz de avaliação

| Treino | Avaliar contra Muse original | Avaliar contra overlay |
| --- | --- | --- |
| LoRA+ / Muse | Sim | Sim |
| LoRA+ / overlay | Sim | Sim |
| Full / Muse | Sim | Sim |
| Full / overlay | Sim | Sim |
| Full + CCE / Muse | Sim | Sim |
| Full + CCE / overlay | Sim | Sim |
| Full + ROS / Muse | Sim | Sim |
| Full + ROS / overlay | Sim | Sim |

## Artefatos

- Runner: `scripts/colab/run_colab_loraplus_muse_sensitivity.py`.
- Resultados agregados: `data/finetune_loraplus_muse_sensitivity_t4_v2.json`,
  `data/finetune_full_muse_sensitivity_t4.json`,
  `data/finetune_full_weighted_cce_muse_sensitivity_t4.json` e
  `data/finetune_full_ros_muse_sensitivity_t4.json`.
- Archives locais: `data/raw/vinitvek-articles-2023-muse-expanded.tar.gz` e
  `data/processed/muse_corrected.tar.gz`.

## Guardrails

- Não dividir janelas sobrepostas do mesmo documento entre treino e teste.
- Não selecionar hiperparâmetros com o split de teste.
- Não sobrescrever a camada Muse original nem o overlay adjudicado.
- Não interpretar o resultado como reprodução do artigo ou prova de que o
  overlay está objetivamente correto.
- Registrar revisões do modelo, hashes, split, configuração, resultados por
  seed e falhas de execução.
