"""Optional MCP stdio server. Launch with: python -m toolkit.mcp_server --allow-root PATH"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Keep module imports reliable when the server is launched by absolute script path
# from a client whose working directory is another authorized project.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from mcp.server import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError as exc:  # pragma: no cover - covered by CLI capability test
    raise SystemExit("MCP opcional indisponível. Instale toolkit/requirements-mcp.txt em ambiente isolado.") from exc

from toolkit.scripts import ai_toolkit as core

MAX_INPUT_CHARS = 100_000
MAX_OUTPUT_CHARS = 60_000
MAX_VALIDATION_SECONDS = 300


def create_server(allowed_roots: list[Path], allow_validation: bool = True):
    roots = [root.resolve(strict=True) for root in allowed_roots if root.exists() and root.is_dir()]
    if not roots:
        raise ValueError("Informe pelo menos um --allow-root existente")
    server = MCPServer("AI Engineering Toolkit", instructions="Ferramentas locais read-only para inspecionar projetos e relatórios. Diretórios limitados aos roots explicitamente permitidos. Não executa scripts de package.json nem modifica arquivos.")

    def authorize(directory: str) -> Path:
        if not isinstance(directory, str) or len(directory) > 4096:
            raise ToolError("directory deve ser um caminho curto")
        candidate = Path(directory)
        if not candidate.is_absolute():
            raise ToolError("directory precisa ser absoluto")
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise ToolError("Diretório inexistente ou inacessível") from exc
        if not resolved.is_dir() or not any(core.within(resolved, root) for root in roots):
            raise ToolError("Diretório não autorizado")
        return resolved

    def authorize_skills_root(project: Path, skills_directory: str = "") -> Path:
        if skills_directory:
            candidate = Path(skills_directory)
            if not candidate.is_absolute():
                candidate = project / candidate
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                raise ToolError("Diretório de skills inexistente ou inacessível") from exc
            if not resolved.is_dir() or not any(core.within(resolved, allowed) for allowed in roots):
                raise ToolError("Diretório de skills não autorizado")
            return resolved
        resolved = core.resolve_skills_root(project)
        if resolved and any(core.within(resolved, allowed) for allowed in roots):
            return resolved
        raise ToolError("Skills não encontradas em root autorizado; use skills_directory ou configure ai-toolkit.json")

    def bounded(result):
        serialized = json.dumps(result, ensure_ascii=False)
        if len(serialized) <= MAX_OUTPUT_CHARS:
            return result
        return {"truncated": True, "message": "Saída excedeu limite MCP; use a CLI local para o relatório completo.", "preview": serialized[:MAX_OUTPUT_CHARS]}

    @server.tool()
    def inspect_project(directory: str) -> dict:
        """Inspeciona stack, pacotes e ferramentas disponíveis dentro de um root autorizado."""
        root = authorize(directory)
        result = core.inspect(root)
        result["instruction_files"] = result["instruction_files"][:100]
        result["packages"] = result["packages"][:200]
        return bounded(result)

    @server.tool()
    def list_skills(directory: str, skills_directory: str = "") -> dict:
        """Lista as skills efetivamente encontradas, seus gatilhos e recursos auxiliares sem ler os corpos."""
        project = authorize(directory)
        source = authorize_skills_root(project, skills_directory)
        return bounded(core.skill_index(source))

    @server.tool()
    def find_relevant_skills(directory: str, task: str, skills_directory: str = "") -> dict:
        """Seleciona skills por stack e intenção; retorna caminhos/referências e não carrega corpos."""
        if len(task) > 10_000:
            raise ToolError("task excede 10 KB")
        project = authorize(directory)
        source = authorize_skills_root(project, skills_directory)
        return bounded(core.relevant_skills(project, task, source))

    @server.tool()
    def read_skill(directory: str, name: str, skills_directory: str = "") -> dict:
        """Lê o SKILL.md selecionado; materiais auxiliares continuam sob demanda."""
        project = authorize(directory)
        source = authorize_skills_root(project, skills_directory)
        try:
            return bounded(core.read_skill(source, name))
        except core.ToolkitError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool()
    def read_skill_reference(directory: str, name: str, reference_path: str, skills_directory: str = "") -> dict:
        """Lê uma referência específica da skill, validando caminho e limite de tamanho."""
        project = authorize(directory)
        source = authorize_skills_root(project, skills_directory)
        try:
            return bounded(core.read_skill_reference(source, name, reference_path))
        except core.ToolkitError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool()
    def get_project_context(directory: str, task: str = "", skills_directory: str = "") -> dict:
        """Monta contexto seletivo com instruções/arquivos relevantes e skills para carregamento progressivo."""
        if len(task) > 10_000:
            raise ToolError("task excede 10 KB")
        project = authorize(directory)
        source = authorize_skills_root(project, skills_directory)
        return bounded(core.project_context(project, task, source, max_files=12, max_total_chars=50_000))

    @server.tool()
    def validate_project(directory: str, level: str = "basic", package: str = "", affected: bool = False) -> dict:
        """Executa apenas validadores catalogados; scripts de projeto não são autorizados pelo servidor."""
        root = authorize(directory)
        if not allow_validation:
            raise ToolError("Execução de validadores desabilitada neste servidor")
        if level not in ("basic", "standard", "strict"):
            raise ToolError("level deve ser basic, standard ou strict")
        report = core.validate_project(root, level=level, timeout=120, allow_scripts=False, selected_package=package or None, affected=affected, total_timeout=MAX_VALIDATION_SECONDS)
        for check in report["checks"]:
            check.pop("stdout", None); check.pop("stderr", None)
        return bounded(report)

    @server.tool()
    def validate_spec(spec_path: str = "", specification: str = "") -> dict:
        """Valida texto enviado ou um arquivo spec dentro de um root autorizado."""
        if len(specification) > MAX_INPUT_CHARS:
            raise ToolError("specification excede 100 KB")
        if specification:
            result = core.validate_spec(Path("<provided-text>"), specification)
        elif spec_path:
            path = Path(spec_path)
            if not path.is_absolute():
                raise ToolError("spec_path precisa ser absoluto")
            if not any(core.within(path, root) for root in roots):
                raise ToolError("Arquivo spec fora dos diretórios autorizados")
            if not path.is_file():
                raise ToolError("Arquivo spec não encontrado")
            if path.stat().st_size > core.MAX_FILE_BYTES:
                raise ToolError("Arquivo spec excede 1 MB")
            result = core.validate_spec(path.resolve())
        else:
            raise ToolError("Informe specification ou spec_path")
        return bounded(result)

    @server.tool()
    def review_changes(directory: str, scope: list[str] | None = None, spec_path: str = "") -> dict:
        """Analisa status/diff sem executar comandos encontrados nas alterações."""
        root = authorize(directory)
        if scope and (len(scope) > 100 or any(len(item) > 512 for item in scope)):
            raise ToolError("scope excede os limites permitidos")
        spec = Path(spec_path).resolve() if spec_path else None
        if spec and not spec.is_file():
            raise ToolError("Arquivo spec não encontrado")
        if spec and not any(core.within(spec, allowed) for allowed in roots):
            raise ToolError("spec_path fora dos diretórios autorizados")
        result = core.validate_change_scope(root, core.changed_entries(root), scope, spec)
        return bounded(result)

    @server.tool()
    def summarize_validation(directory: str) -> dict:
        """Consulta e resume o último relatório salvo pelo toolkit, omitindo logs de processos."""
        root = authorize(directory)
        path = root / ".ai-toolkit" / "validation-report.json"
        if not path.is_file():
            return {"status": "not_run", "reason": "Relatório de validação não encontrado"}
        if path.stat().st_size > 5_000_000:
            raise ToolError("Relatório excede limite de 5 MB")
        report = core.safe_json(path)
        report.pop("checks", None)
        for package_result in report.get("packages", []):
            for check in package_result.get("checks", []):
                check.pop("stdout", None); check.pop("stderr", None)
        return bounded(report)

    @server.tool()
    def get_toolkit_capabilities() -> dict:
        """Retorna capacidades habilitadas e limitações reais deste servidor."""
        return {"server": "AI Engineering Toolkit", "transport": "stdio", "tools": ["list_skills", "find_relevant_skills", "read_skill", "read_skill_reference", "get_project_context", "inspect_project", "validate_project", "validate_spec", "review_changes", "summarize_validation", "get_toolkit_capabilities"], "validation_enabled": allow_validation, "allowed_roots": [str(root) for root in roots], "writes_project_files": False, "runs_package_scripts": False, "limitations": ["Scanner de segredos local é heurístico", "Validadores dependem das ferramentas nativas disponíveis e podem criar caches do SDK", "Sem sandbox de sistema operacional", "Saídas MCP limitadas a 60 KB"]}

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Servidor MCP local read-only do AI Engineering Toolkit")
    parser.add_argument("--allow-root", action="append", required=True, help="Diretório autorizado; pode repetir. Inclua também o checkout das skills se estiver separado")
    parser.add_argument("--disable-validation", action="store_true", help="Desabilita execução dos validadores catalogados")
    args = parser.parse_args(argv)
    try:
        server = create_server([Path(item) for item in args.allow_root], allow_validation=not args.disable_validation)
        server.run()  # stdio é o transporte padrão do SDK oficial.
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Falha ao iniciar MCP: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
