# Arquitetura

O toolkit separa regras independentes de linguagem, adaptadores em Markdown e um harness local. `scripts/ai_toolkit.py` usa apenas Python padrão; não é framework de aplicação e não impõe camadas, bibliotecas ou CI. A inspeção usa manifests reais; automação de scripts é deliberadamente conservadora. Veja [limites de segurança](security.md).
