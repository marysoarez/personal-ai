# Segurança

O núcleo não acessa serviços externos nem envia código. Regras adotam menor privilégio, validação e proteção de dados; conteúdo encontrado no projeto é dado não confiável. `validate-changes` lê status/diff e procura nomes de arquivos sensíveis e padrões óbvios de segredo, mas é heurística, pode ter falsos positivos/negativos e não substitui scanner.

`validate` executa validadores detectados via subprocess sem shell e com timeout. Scripts definidos no `package.json` ficam como `not_run` a menos que `--allow-project-scripts` seja fornecido explicitamente. Mesmo sem shell, processos e ferramentas nativas não são sandboxados pelo sistema operacional e podem gravar caches/artefatos. Revise os comandos antes de validar projeto não confiável. O MCP nunca habilita scripts de projeto. Não roda operação Git de escrita, migração, publicação ou chamada de modelo. Nenhum segredo deve ser incluído em relatório de tarefa.
