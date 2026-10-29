# Servidor MCP opcional

`toolkit/mcp_server.py` implementa um servidor local usando o SDK oficial Python e transporte stdio. O núcleo CLI permanece sem dependência MCP; instale `toolkit/requirements-mcp.txt` apenas em ambiente virtual próprio. O SDK oficial documenta o servidor stdio e a API Python em [Python SDK](https://github.com/modelcontextprotocol/python-sdk) e [execução de servidores](https://py.sdk.modelcontextprotocol.io/run/).

Configure caminhos absolutos no cliente a partir de [mcp-client.example.json](../mcp-client.example.json). Cada `--allow-root` autoriza uma raiz de projeto ou skills. A raiz da biblioteca de skills deve estar autorizada separadamente quando fora do projeto.

Ferramentas expostas: `get_toolkit_capabilities`, `inspect_project`, `validate_project`, `validate_spec`, `review_changes`, `summarize_validation`, `list_skills`, `find_relevant_skills`, `read_skill`, `read_skill_reference` e `get_project_context`. Skills são selecionadas e carregadas progressivamente, não copiadas para uma segunda biblioteca.

O servidor valida roots e caminhos resolvidos, restringe tamanho de entrada/saída, não oferece shell genérico, não autoriza scripts `package.json` e não grava arquivos do projeto. `validate_project` executa validadores catalogados do sistema, limitados por tempo; esses validadores podem gerar caches/artefatos e não são isolados por sandbox do sistema operacional. `--disable-validation` desliga essa ferramenta. O transporte stdio herda o contexto de segurança do processo que inicia o servidor.

Verificação local realizada: testes de integração iniciaram o servidor stdio e chamaram ferramentas por meio do cliente oficial do SDK. Isso verifica protocolo e limites cobertos pelas fixtures, não substitui testes em cada cliente MCP ou uma auditoria de segurança. A dependência é opcional e sua ausência não quebra a CLI.
