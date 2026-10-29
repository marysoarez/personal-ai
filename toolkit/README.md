# AI Engineering Toolkit

Toolkit local e reutilizável para desenvolvimento assistido por agentes em Flutter/Dart, React e Node.js. Inclui instruções Markdown, templates e harness Python. Não exige chave de API nem serviço externo.

## Requisitos e início rápido

- Python 3.10+ para CLI, testes do núcleo e avaliações determinísticas.
- Git é opcional; habilita inspeção de status/diff.
- Validadores de stack dependem das ferramentas já instaladas no projeto. O toolkit não instala dependências.

Na raiz do repositório:

```sh
python toolkit/scripts/ai_toolkit.py inspect .
python toolkit/scripts/ai_toolkit.py validate-spec specs/feature.md
python toolkit/scripts/ai_toolkit.py validate .
python toolkit/scripts/ai_toolkit.py validate-changes . --scope src --scope specs
python toolkit/scripts/ai_toolkit.py summarize . --objective "Descrever a tarefa"
python -m unittest discover -s toolkit/tests
python toolkit/evals/run_evals.py
```

Em Windows, use `py -3` se `python` não estiver no PATH. A CLI oferece `inspect`, `packages`, `validate`, `validate-spec`, `validate-changes`, `summarize`, `skills-index`, `find-skills`, `read-skill`, `read-skill-reference` e `get-project-context`. Use `--help` em cada comando para ver argumentos.

## Camadas

- `instructions/shared/`: modos de agente, especificação, contexto, feature, revisão, refatoração, testes, segurança, privacidade/LGPD, Firebase e escalabilidade.
- `instructions/flutter/AGENTS.md`, `react/AGENTS.md`, `node/AGENTS.md`: adaptadores condicionados à stack.
- `templates/`: especificação, plano, revisão, decisão e caso de avaliação.
- `scripts/ai_toolkit.py`: CLI local, detecção de stack/pacotes, validações e orquestração de skills.
- `mcp_server.py`: servidor MCP stdio opcional, somente leitura de arquivos do projeto e execução limitada a validadores catalogados.
- `evals/cases/`: fixtures determinísticas; `tests/`: testes unitários e de protocolo.
- `docs/`: arquitetura, fluxos, segurança, SDD, contexto, harness, review, refatoração, MCP e evals.

## Harness e estados

`validate` executa verificações reconhecidas, registra estado, código, duração e saída, e para após uma falha obrigatória. Scripts definidos no `package.json` só rodam com `--allow-project-scripts`; por padrão aparecem como `not_run`. O relatório é salvo em `.ai-toolkit/validation-report.{json,md}`. Estados de verificação: `passed`, `failed`, `skipped`, `not_run`, `error`; estados agregados também incluem `partial`. Códigos de saída: 0 sucesso, 1 falha de validação, 2 erro de uso/execução, 3 interrupção e 4 validação parcial ou não executada.

## Adaptadores

- **Flutter/Dart:** detectados por `pubspec.yaml`; distingue Dart puro de Flutter e consulta format, analyze e test quando disponíveis.
- **React/Node:** React é identificado por manifest/dependências; Node por `package.json`. Usa somente scripts existentes e gerenciador inferido do lockfile.
- **Monorepo:** detecta workspaces npm/pnpm/Yarn, Lerna e padrões configurados. Permite selecionar pacote e validar `--affected`, incluindo consumidores de dependências internas. Scripts nested não são autorizados automaticamente.

## Skills e contexto progressivo

As skills de `skills/` são fonte especializada e independente. `skills-index` lista metadados sem ler todos os corpos; `find-skills` seleciona pela stack/intenção; `read-skill` abre apenas a skill escolhida; `read-skill-reference` abre apoio sob demanda. `get-project-context` reúne instruções, manifests, arquivos relacionados e skills selecionadas com limites de tamanho. Configure `skills_dir` em `ai-toolkit.json` quando a biblioteca estiver em outro local. O toolkit não altera os `SKILL.md` originais.

Adaptadores direcionam para as instruções existentes. Arquitetura especializada só é selecionada quando pedida ou detectada. Convenções PKT são específicas desse aplicativo e não são impostas a outros projetos. O catálogo marca `loaded: false` enquanto só metadados foram lidos.

O scanner arquitetural só aplica regras explícitas em `architecture_rules.forbidden_imports` dentro de `ai-toolkit.json`; não impõe uma arquitetura universal. Veja [ai-toolkit.json.example](../ai-toolkit.json.example).

## Incorporar em outro repositório

Copie `toolkit/` para um caminho dedicado e mescle regras de `instructions/shared/AGENTS.md` ao `AGENTS.md` local. Não substitua instruções existentes: resolva conflitos e mantenha convenções/arquitetura locais. Adicione apenas adaptadores aplicáveis. Comandos detectados são sugestões; revise-os antes de automatizar CI.

## MCP opcional

Instale `toolkit/requirements-mcp.txt` em ambiente virtual isolado, configure `toolkit/mcp-client.example.json` com roots absolutos autorizados e inicie `python -m toolkit.mcp_server`. O servidor usa stdio, não aceita shell arbitrário, não roda scripts de projeto e não escreve arquivos do projeto. Veja [docs/mcp.md](docs/mcp.md).

## Limites

Git é usado para ler status/diff; o toolkit não publica, commita, faz push nem chama modelos. Gitleaks é opcional; a detecção local de segredos é heurística. Validadores podem executar ferramentas nativas do projeto, criar caches ou artefatos; não há sandbox de sistema operacional. Evals atuais são offline e determinísticos: verificam fixtures/regras, não garantem qualidade de respostas LLM nem substituem revisão humana.

Mais detalhes: [início](docs/getting-started.md), [arquitetura](docs/architecture.md), [fluxos](docs/workflows.md), [segurança](docs/security.md), [SDD](docs/sdd.md), [contexto](docs/context-engineering.md), [harness](docs/harness-engineering.md), [revisão](docs/code-review.md), [refatoração](docs/ai-refactoring.md), [MCP](docs/mcp.md), [evals](docs/evals.md).

## Base das orientações

As instruções compartilhadas foram sintetizadas das skills deste repositório para que `toolkit/` continue utilizável quando copiado sozinho: Flutter, React, Node, Firebase, review, feature, testes, LGPD, segurança e escalabilidade. Para projetos PKT, consulte as skills `pkt-personal-feature`, `pkt-personal-architecture` e `pkt-personal-code-review`; suas convenções permanecem próprias do app PKT.
