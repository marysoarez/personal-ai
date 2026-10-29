# SPEC-101 Exportar dados da conta

## Problema
O titular não consegue obter uma cópia dos dados da própria conta.
## Objetivo
Disponibilizar exportação JSON autenticada.
## Escopo
Exportar dados da conta ativa.
## Fora de escopo
Importação e migração entre contas.
## Requisitos funcionais
- RF-1: O servidor gera JSON para o usuário autenticado.
## Requisitos não funcionais
- RNF-1: A exportação conclui em até 30 segundos para contas dentro do limite configurado.
## Regras de negócio
Uma conta só pode solicitar os próprios dados.
## Restrições arquiteturais
Preservar o backend e os contratos de API atuais.
## Segurança e privacidade
Autorizar o usuário por identidade verificada no servidor e não registrar conteúdo exportado.
## Critérios de aceitação
- Given uma sessão autenticada When solicita exportação Then recebe HTTP 200 e JSON apenas dos dados associados à identidade verificada.
- Given uma identidade sem sessão When solicita exportação Then recebe HTTP 401 e nenhum dado.
## Cenários positivos e negativos
Conta com dados; conta vazia; sessão ausente; falha de repositório.
## Dependências
Repositório de dados e provedor de identidade já configurados.
## Estratégia de testes
Testes de unidade de mapeamento e integração de autorização.
## Riscos
Conjunto de dados acima do limite deve ser tratado sem resposta parcial.
## Plano de implementação
- Etapa 1: mapear os campos permitidos.
- Etapa 2: implementar serviço e rota no padrão existente.
## Estratégia de validação
- Executar lint, testes da rota e análise de autorização; registrar ferramentas ausentes.
## Definição de pronto
- Critérios de aceitação verificados e revisão do diff concluída.
