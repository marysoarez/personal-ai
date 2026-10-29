---
name: lgpd
description: Analyze and improve software, data flows, and product processes for LGPD privacy concerns. Use for personal-data mapping, legal basis, data minimization, retention, data-subject requests, processors, incidents, privacy by design, and product/privacy reviews in Brazil.
---

# LGPD e privacidade de dados

## Objetivo e limites

Apoie a identificação de requisitos de privacidade e sua tradução em controles de produto e tecnologia. Não conclua sozinho que um tratamento é legal, escolha uma base legal sem fatos suficientes, nem substitua o encarregado, jurídico ou avaliação profissional. Separe fatos confirmados, premissas e questões que precisam de validação.

## Fluxo de análise

1. Entenda o produto, as finalidades do tratamento, os sistemas envolvidos e a solicitação. Leia políticas, contratos, avisos, instruções do repositório e registros existentes antes de propor mudanças.
2. Mapeie cada operação relevante: categorias de dados, titulares, origem, finalidade, sistemas/países, destinatários e operadores, acesso, retenção e descarte. Classifique controlador, operador e suboperador pelos papéis reais e decisões de cada parte; não confie apenas nos rótulos de um contrato.
3. Identifique dados pessoais e dados pessoais sensíveis. Avalie necessidade, proporcionalidade, transparência, riscos aos titulares e alternativas que usem menos dados.
4. Para cada finalidade, registre a hipótese legal indicada pelo controlador ou responsável. Se ela não estiver documentada ou os fatos forem insuficientes, sinalize a decisão para validação do encarregado/jurídico; não a infira apenas pela conveniência técnica.
5. Traduza os requisitos confirmados em controles: coleta mínima, acesso por função e recurso, isolamento entre usuários/tenants, criptografia, trilha de auditoria sem conteúdo sensível, retenção e eliminação verificáveis.
6. Considere direitos dos titulares e processos para confirmação, acesso, correção, anonimização, bloqueio, eliminação, portabilidade quando aplicável, informação sobre compartilhamento e revisão de decisões automatizadas. Registre dependências e exceções para avaliação responsável.
7. Avalie operadores, integrações, analytics, logs, backups, transferências internacionais e resposta a incidentes. Não presuma que um fornecedor ou SDK pode receber dados sem avaliação e instruções adequadas.
8. Apresente achados com evidência, risco, recomendação técnica, responsável por decidir e questões em aberto. Diferencie requisito jurídico confirmado de recomendação técnica. Para direitos dos titulares, RIPD, papéis dos agentes e incidentes, leia as fontes oficiais em `references/official-sources.md`; confirme a regra vigente antes de afirmar prazos ou obrigações.

## Implementação e segurança

- Não leia, imprima, copie ou inclua em testes dados reais de titulares, credenciais ou tokens. Use exemplos sintéticos e ambientes locais/emuladores.
- Não registre CPF completo, dados de saúde, biometria, credenciais ou conteúdo pessoal em logs, analytics, notificações ou relatórios de erro.
- Faça autorização no servidor por usuário, recurso e tenant; não confie em IDs, consentimentos ou papéis declarados pelo cliente sem validação.
- Documente a finalidade e os campos coletados. Evite coleta "para uso futuro" sem justificativa e aprovação responsável.
- Defina políticas e mecanismos para retenção, descarte, exportação e propagação de exclusões a provedores e sistemas derivados.
- Use criptografia em trânsito e em repouso e controles de acesso proporcionais ao risco; mantenha chaves e segredos em mecanismos apropriados.
- Para Firebase, revise Auth, Security Rules, Storage e acessos via Admin SDK: serviços privilegiados não ficam protegidos pelas regras de cliente e precisam de IAM e autorização no backend.
- Faça verificações de segurança apenas em ambientes autorizados, com dados sintéticos; não contate titulares, fornecedores ou autoridades sem autorização explícita.
- Escale imediatamente incidentes suspeitos ao controlador e ao encarregado/responsável interno; não decida sozinho a notificação externa nem espere a análise técnica terminar para iniciar o fluxo interno de resposta.
- Considere tratamento de dados de crianças e adolescentes, dados sensíveis e usos de IA/decisões automatizadas como contextos que exigem avaliação específica, sem presumir que o fluxo geral seja suficiente.

## Entrega

Estruture a resposta em:

1. **Escopo e fatos** — sistemas, dados e finalidades analisados.
2. **Achados** — risco, evidência e prioridade, sem transformar hipótese em conclusão.
3. **Ações técnicas** — controles e mudanças concretas sugeridas ou implementadas.
4. **Decisões a validar** — base legal, papéis, prazos, transferências ou exceções que dependem do controlador/encarregado/jurídico.
5. **Verificação** — testes e evidências realmente obtidos; nunca declare conformidade integral sem uma avaliação adequada.

Considere o texto vigente da LGPD e orientações atuais da ANPD para questões normativas. Sempre confirme alterações recentes em fontes oficiais antes de orientar sobre prazos, procedimentos ou obrigações específicas.

