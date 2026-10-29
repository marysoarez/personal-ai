# Evals e observabilidade

`evals/cases/*.json` contém fixtures determinísticas para fluxo de trabalho, validação de especificação, limites arquiteturais declarados, regras de privacidade, padrões React, segredos, rastreabilidade de critérios e detecção de stack. Rode `python toolkit/evals/run_evals.py`; o runner imprime JSON e retorna código diferente de zero se um caso falhar. As entradas sensíveis de casos de segurança/review são representadas no relatório por hash e tamanho, sem reproduzir seu conteúdo.

As fixtures de arquitetura criam um diretório temporário e usam as regras explícitas do projeto. Um exemplo preserva a arquitetura Provider e outro detecta import Modular não solicitado. Os casos React e privacidade usam regex de exemplo: não constituem análise semântica ou prova de acessibilidade/conformidade.

O harness unittest cobre execução limitada de processos, limites de saída, detecção/seleção de skills, formatos de estado, validação de spec e testes de protocolo MCP quando a dependência opcional está instalada. Em ambiente sem SDK MCP, os testes de protocolo são marcados como skipped.

Essas avaliações exercitam o código/regras do toolkit em fixtures sintéticas. Não avaliam comportamento oculto de agente, qualidade geral de modelos, nem substituem revisão humana. Evals LLM continuam uma extensão futura: probabilísticas, com provedor configurável, fixtures versionadas e aprovação humana.
