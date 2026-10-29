# Minhas Skills de IA e AI Engineering Toolkit

Coleção pessoal de skills para assistentes de IA, organizada por tipo de trabalho, junto de um toolkit reutilizável de engenharia de software assistida por IA. As skills continuam independentes e compatíveis com o formato do Codex.

## AI Engineering Toolkit

O diretório [`toolkit/`](toolkit/README.md) fornece regras compartilhadas, adaptadores para Flutter/Dart, React e Node.js, modelos de especificação/revisão, scripts multiplataforma em Python (biblioteca padrão) e avaliações determinísticas. Ele detecta ferramentas a partir dos arquivos do projeto e não instala dependências nem chama serviços externos.

Comece com `python toolkit/scripts/ai_toolkit.py inspect .`; consulte o [guia do toolkit](toolkit/README.md) para instalação, validação e incorporação em outros repositórios.

## Flutter e arquitetura

| Skill | Para que serve |
|---|---|
| [`flutter-development`](skills/flutter-development/SKILL.md) | Desenvolvimento geral Flutter/Dart: widgets, estado, navegação, responsividade, acessibilidade e testes. |
| [`flutter-architecture`](skills/flutter-architecture/SKILL.md) | Arquitetura modular MVVM com Modular/MobX, quando o projeto já usa ou pede esse padrão. |
| [`criar-projeto-flutter`](skills/criar-projeto-flutter/SKILL.md) | Bootstrap de projetos Flutter e configuração de estrutura, ambientes e testes. |
| [`criar-feature`](skills/criar-feature/SKILL.md) | Implementação ponta a ponta, adaptada à stack e arquitetura encontradas no repositório. |
| [`pkt-personal-architecture`](skills/pkt-personal-architecture/SKILL.md) | Camadas, padrões atuais e migrações arquiteturais específicas do app PKT Personal. |
| [`pkt-personal-feature`](skills/pkt-personal-feature/SKILL.md) | Implementação de features PKT usando o padrão local Provider/Firebase ou o já migrado. |
| [`pkt-personal-code-review`](skills/pkt-personal-code-review/SKILL.md) | Revisão Flutter específica do PKT: camadas, Firebase, Provider, rotas e regressões. |

## Firebase e backend

| Skill | Para que serve |
|---|---|
| [`firebase-development`](skills/firebase-development/SKILL.md) | Firebase, FlutterFire, Auth, regras, bancos, Functions, emuladores e segurança. |
| [`node-architecture`](skills/node-architecture/SKILL.md) | Arquitetura segura para serviços Node.js/TypeScript e APIs. |

## Qualidade, segurança e operações

| Skill | Para que serve |
|---|---|
| [`code-review`](skills/code-review/SKILL.md) | Revisão geral de diffs: bugs, segurança, arquitetura, compatibilidade, desempenho e testes. |
| [`attack-defense`](skills/attack-defense/SKILL.md) | Modelagem de ameaças e fortalecimento contra riscos OWASP e abuso de APIs. |
| [`data-security`](skills/data-security/SKILL.md) | Privacidade por padrão e proteção de dados pessoais ou sensíveis. |
| [`lgpd`](skills/lgpd/SKILL.md) | Analisar privacidade e requisitos da LGPD em produtos, sistemas e fluxos de dados no Brasil. |
| [`criar-testes`](skills/criar-testes/SKILL.md) | Estratégia e implementação de testes unitários, widget, integração, segurança e concorrência. |
| [`escalabilidade`](skills/escalabilidade/SKILL.md) | Performance, capacidade, disponibilidade, observabilidade e custos. |

## Frontend e design

| Skill | Para que serve |
|---|---|
| [`react-frontend`](skills/react-frontend/SKILL.md) | Construir e manter interfaces React, com componentes, hooks, estado, acessibilidade e testes. |
| [`impeccable`](skills/impeccable/SKILL.md) | Projetar, avaliar e aprimorar interfaces frontend. Atualizada para Impeccable 4.8.0, com referências, scripts de apoio e licença Apache 2.0. |

## Origens e organização

As skills de Flutter, Firebase, revisão, React e PKT vieram das skills pessoais ou de plugins já disponíveis nesta máquina. A Impeccable veio de [pbakaus/impeccable, skill-v4.8.0](https://github.com/pbakaus/impeccable/releases/tag/skill-v4.8.0), sob licença Apache 2.0. As skills `attack-defense`, `criar-feature`, `criar-projeto-flutter`, `criar-testes`, `data-security`, `escalabilidade`, `flutter-architecture` e `node-architecture` foram integradas da biblioteca pessoal do GitHub Copilot. As orientações de Firebase Auth e revisão do Copilot foram incorporadas às skills `firebase-development` e `code-review` para evitar duplicação.

Cada pasta em `skills/` contém uma skill independente. O arquivo `SKILL.md` descreve quando e como usá-la; pastas como `references/`, `scripts/` e `assets/` podem conter material de apoio.

## Adicionar uma skill

1. Crie uma pasta em `skills/` com um nome curto em minúsculas e hífens.
2. Adicione um `SKILL.md` com frontmatter YAML contendo `name` e `description`.
3. Coloque materiais auxiliares em subpastas como `references/`, `scripts/` ou `assets/`.
4. Atualize este catálogo.

## Uso

Para instalar uma skill localmente no Codex, copie a pasta da skill escolhida para `~/.codex/skills/`. As skills PKT incluem suas próprias referências para continuar portáveis quando copiadas individualmente. A disponibilidade após a cópia depende de recarregar ou reiniciar o Codex.






