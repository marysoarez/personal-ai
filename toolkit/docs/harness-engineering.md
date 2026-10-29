# Harness Engineering

`inspect` reporta stack, manifests, package manager, scripts, configurações de teste/estática, instruções, skills e CI observado. `packages` lista pacotes detectados. `validate` executa verificações reconhecidas, registra estado, código, tempo e saída; scripts de projeto exigem `--allow-project-scripts`, ausências ficam como `not_run`, e falha interrompe próximos comandos obrigatórios. `validate-changes` lista status/diff, verifica escopo e caminhos sensíveis e roda validadores catalogados para pacotes afetados sem autorizar scripts de projeto. `summarize` cria estado retomável.

Estados de checks: `passed`, `failed`, `skipped`, `not_run` e `error`. O agregado pode ser `partial`; códigos de saída são 0 (passou), 1 (falha), 2 (erro de uso/execução), 3 (interrompido) e 4 (parcial/não executado). Quando nenhuma ferramenta se aplica, não há sucesso inventado. Monorepos suportam workspaces npm/pnpm/Yarn, Lerna e padrões configurados, dentro de limites de profundidade/quantidade. Valide seleções manualmente antes de CI.

Regras de arquitetura são aplicadas apenas se o repositório declarar `architecture_rules.forbidden_imports` no `ai-toolkit.json`; os findings incluem caminho e linha. A inspeção de dependências e arquitetura não substitui análise de linguagem.
