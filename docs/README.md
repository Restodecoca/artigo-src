# Relatórios do projeto

Documentação resumida do Marco 3 e dos experimentos de reconstrução/expansão do
estudo sobre NER em notícias de cibersegurança na área da saúde.

1. [Dataset e processo de rotulagem](01_dataset_e_rotulagem.md)
2. [Avaliação dos modelos](02_avaliacao_modelos.md)
3. [Fine-tuning, resultados e verificações](03_finetuning_e_verificacoes.md)
4. [Anotações humanas, consenso e histórico experimental](04_anotacoes_assistidas.md)

A anotação descrita no artigo partiu de sugestões do Muse Spark, modelo de
linguagem da Meta. Os anotadores revisaram manualmente os trechos e as
categorias e acrescentaram entidades ausentes. Os registros dos demais
experimentos preliminares permanecem separados desse procedimento.

Os textos completos das notícias, os archives e as auditorias integrais estão
em `review-data/`, para revisão acadêmica. As exportações sem texto e os
resultados agregados estão em `data/muse-artifacts/`. Os diagnósticos por
documento permanecem restritos.
