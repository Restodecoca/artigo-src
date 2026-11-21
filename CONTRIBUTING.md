# Como contribuir

Obrigado por ajudar a manter o projeto reproduzível e seguro. Antes de alterar
código ou dados, leia `DATA_AND_ARTIFACT_POLICY.md` e `data/README.md`.

## Ambiente local

Requisitos: Python 3.12+ e `uv`.

```powershell
uv sync --extra dev
uv run pytest
uv run ruff check src tests scripts
uv run pyright
```

Para recursos específicos, instale apenas os extras necessários (`hf`,
`models` ou `finetune`) listados no `pyproject.toml`.

## Fluxo recomendado

1. Crie uma branch curta para uma mudança independente.
2. Faça alterações pequenas e mantenha lógica reutilizável em
   `src/healthcare_ner_replication/`.
3. Acrescente ou atualize testes; prefira fixtures sintéticas a dados de artigos.
4. Execute testes, Ruff e os validadores relevantes antes de abrir um PR.
5. Atualize a documentação correspondente e descreva limitações e desvios do
   protocolo.

Pull requests executam automaticamente a suíte de testes, Ruff e Pyright pelo GitHub
Actions. Use o checklist em `.github/pull_request_template.md`.

## Regras para dados e credenciais

- Nunca faça commit de `.env`, tokens, checkpoints, caches ou diagnósticos
  detalhados.
- Exportações públicas de anotação devem omitir o campo `text` e notas livres.
- Os textos completos ficam em `review-data/`, apenas para revisão acadêmica.
- Antes de publicar qualquer artefato, confirme licença, direitos da fonte e
  ausência de conteúdo que permita reconstruir artigos.
- Não chame substitutos públicos ou o overlay de gold manual do artigo.

## Scripts remotos

Os arquivos em `scripts/colab/` permanecem autônomos porque `colab exec -f`
transfere o corpo do script ao runtime. Ao alterar um runner, não dependa de
módulos locais que não serão enviados ao Colab; atualize também o protocolo e o
catálogo se o path ou o comportamento mudar.

## Checklist de PR

- [ ] Testes relevantes passam.
- [ ] Ruff passa nos caminhos alterados.
- [ ] Nenhum dado privado ou credencial foi adicionado.
- [ ] Paths, configuração e documentação foram atualizados.
- [ ] Limitações e impacto nos resultados estão descritos.
