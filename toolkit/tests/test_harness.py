import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).parents[1] / "scripts" / "ai_toolkit.py"
spec = importlib.util.spec_from_file_location("ai_toolkit", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

VALID_SPEC = """# SPEC-42 Exportar dados
## Problema
Titulares precisam obter seus dados.
## Objetivo
Exportar um arquivo JSON para a conta autenticada.
## Escopo
Exportação sob demanda.
## Fora de escopo
Migração dos dados.
## Requisitos funcionais
- RF1: Exportar dados do titular.
## Critérios de aceitação
- Given titular autenticado When solicita exportação Then recebe arquivo JSON apenas da própria conta.
## Estratégia de testes
- Testar autorização e resposta vazia.
## Segurança e privacidade
- Autorizar por usuário no servidor.
## Riscos
- Volume grande de dados.
## Dependências
- Repositório de dados.
## Plano de implementação
- Etapa 1: serviço e endpoint.
## Estratégia de validação
- Teste automatizado de autorização.
"""


class HarnessTests(unittest.TestCase):
    def test_shared_guidance_files_are_present_and_nonempty(self):
        shared = SCRIPT.parents[1] / "instructions" / "shared"
        expected = {"AGENTS.md", "specification.md", "context-engineering.md", "feature-development.md", "code-review.md", "refactoring.md", "testing.md", "security.md", "firebase.md", "privacy-lgpd.md", "scalability.md"}
        for name in expected:
            path = shared / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(len(path.read_text(encoding="utf-8").strip()), 100, name)

    def test_skill_index_reads_metadata_and_lists_real_auxiliaries(self):
        catalog = tool.skill_index(SCRIPT.parents[2])
        self.assertEqual(17, catalog["count"])
        by_name = {item["name"]: item for item in catalog["skills"]}
        self.assertTrue(by_name["lgpd"]["metadata_read"])
        self.assertFalse(by_name["lgpd"]["loaded"])
        self.assertIn("references/official-sources.md", by_name["lgpd"]["references"])
        loaded = tool.read_skill(SCRIPT.parents[2] / "skills", "lgpd")
        self.assertTrue(loaded["loaded"])
        self.assertIn("LGPD", loaded["content"])

    def test_skill_selection_is_stack_and_intent_aware_and_pkt_is_specific(self):
        skills_root = SCRIPT.parents[2] / "skills"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"dependencies": {"react": "19"}}))
            selected = tool.relevant_skills(root, "design and improve accessible interface", skills_root)
            names = {item["name"] for item in selected["skills"]}
            self.assertIn("react-frontend", names)
            self.assertIn("impeccable", names)
            self.assertNotIn("pkt-personal-architecture", names)
            (root / "README.md").write_text("# PKT Personal\n")
            selected = tool.relevant_skills(root, "review feature", skills_root)
            names = {item["name"] for item in selected["skills"]}
            self.assertIn("pkt-personal-code-review", names)
            self.assertNotIn("code-review", names)

    def test_detects_react_scripts_and_manager(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"dependencies": {"react": "^19"}, "scripts": {"test": "vitest"}}))
            (root / "pnpm-lock.yaml").write_text("")
            result = tool.inspect(root)
            self.assertIn("react", result["stack"])
            self.assertEqual("pnpm", result["package_manager"])
            self.assertEqual("test", result["checks_available"][0]["name"] if result["checks_available"] else "test")

    def test_project_scripts_require_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"scripts": {"test": "node -e process.exit(0)"}}))
            _, details = tool.stack_of(root)
            safe = tool.validators_for(root, ["node"], details, "standard", False)
            self.assertEqual("not_run", next(c for c in safe if c["name"] == "test")["status"])
            enabled = tool.validators_for(root, ["node"], details, "standard", True)
            self.assertNotIn("status", next(c for c in enabled if c["name"] == "test"))

    def test_unknown_project_and_missing_tools_are_not_run(self):
        with tempfile.TemporaryDirectory() as directory:
            result = tool.validate_project(Path(directory))
            self.assertEqual("not_run", result["summary"]["status"])
            self.assertEqual(".", result["packages"][0]["package"])

    def test_flutter_and_dart_are_distinguished(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pubspec.yaml").write_text("name: plain_dart\n")
            self.assertEqual(["dart"], tool.stack_of(root)[0])
            (root / "pubspec.yaml").write_text("name: flutter_app\ndependencies:\n  flutter:\n    sdk: flutter\n")
            self.assertEqual(["flutter"], tool.stack_of(root)[0])

    def test_workspace_discovers_mixed_stacks_and_excludes_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"private": True, "workspaces": ["apps/*", "services/*"]}))
            web = root / "apps" / "web"; web.mkdir(parents=True)
            (web / "package.json").write_text(json.dumps({"name": "web", "dependencies": {"react": "19"}, "scripts": {"test": "vitest"}}))
            api = root / "services" / "api"; api.mkdir(parents=True)
            (api / "package.json").write_text(json.dumps({"name": "api", "scripts": {"test": "node test.js"}}))
            junk = web / "node_modules" / "bad"; junk.mkdir(parents=True)
            (junk / "package.json").write_text("{}")
            result = tool.inspect(root)
            self.assertTrue(result["is_monorepo"])
            self.assertEqual({"apps/web", "services/api"}, {p["path"] for p in result["packages"]})
            self.assertEqual({"react", "node"}, {s for p in result["packages"] for s in p["stacks"]})

    def test_custom_package_outside_root_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root, other = Path(directory), Path(outside)
            (other / "package.json").write_text("{}")
            (root / "ai-toolkit.json").write_text(json.dumps({"packages": [str(other)]}))
            self.assertEqual([], tool.discover_package_dirs(root))

    def test_validate_spec_checks_content_and_verifiable_criteria(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spec.md"
            path.write_text(VALID_SPEC)
            self.assertEqual("passed", tool.validate_spec(path)["status"])
            path.write_text(VALID_SPEC.replace("recebe arquivo JSON apenas da própria conta", "o recurso funciona"))
            result = tool.validate_spec(path)
            self.assertTrue(result["warnings"])
            self.assertEqual("passed", result["status"])
            path.write_text("# Spec\n## Problema\n")
            self.assertEqual("failed", tool.validate_spec(path)["status"])

    def test_aggregate_states_and_exit_code_for_failed_validation(self):
        self.assertEqual("passed", tool.aggregate([{"status": "passed"}, {"status": "skipped"}])["status"])
        self.assertEqual("not_run", tool.aggregate([{"status": "not_run"}])["status"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pubspec.yaml").write_text("name: app\ndependencies:\n  flutter:\n    sdk: flutter\n")
            result = tool.run_checks(root, [{"name": "failure", "command": [sys.executable, "-c", "raise SystemExit(7)"], "required": True}], 10)
            self.assertEqual("failed", result[0]["status"])
            self.assertEqual(7, result[0]["exit_code"])

    def test_scanner_redacts_secrets_and_ignores_placeholders(self):
        fake = "ghp_" + "A" * 36
        results = tool.scan_secret_text(f'token = "{fake}"\napi_key = "YOUR_API_KEY_HERE"\n')
        self.assertEqual(1, len(results))
        self.assertNotIn(fake, results[0]["message"])

    def test_architecture_rules_are_repository_declared_and_report_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {"architecture_rules": {"forbidden_imports": [{"files": "lib/features/**/*.dart", "patterns": [r"package:flutter_modular/"]}]}}
            (root / "ai-toolkit.json").write_text(json.dumps(config))
            source = root / "lib/features/login/controller.dart"
            source.parent.mkdir(parents=True)
            source.write_text("import 'package:flutter_modular/flutter_modular.dart';\n")
            result = tool.architecture_check(root)
            self.assertEqual("failed", result["status"])
            self.assertEqual("lib/features/login/controller.dart", result["findings"][0]["path"])
            self.assertEqual(1, result["findings"][0]["line"])
            source.write_text("import 'package:provider/provider.dart';\n")
            self.assertEqual("passed", tool.architecture_check(root)["status"])

    def test_process_timeout_and_output_cap(self):
        result = tool.run_process([sys.executable, "-c", "import time; print('start', flush=True); time.sleep(4)"], Path.cwd(), 1, 64)
        self.assertEqual("failed", result["status"])
        self.assertEqual(124, result["exit_code"])
        output = tool.run_process([sys.executable, "-c", "print('x'*10000)"], Path.cwd(), 10, 64)
        self.assertIn("truncada", output["stdout"])

    def test_cli_exit_codes_and_json(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.md"; bad.write_text("# empty\n")
            result = subprocess.run([sys.executable, str(SCRIPT), "validate-spec", str(bad), "--json"], text=True, capture_output=True)
            self.assertEqual(1, result.returncode)
            parsed = json.loads(result.stdout)
            self.assertEqual("failed", parsed["status"])
            inspect = subprocess.run([sys.executable, str(SCRIPT), "inspect", directory, "--json"], text=True, capture_output=True)
            self.assertEqual(0, inspect.returncode)
            self.assertEqual("unknown", json.loads(inspect.stdout)["project_type"])


if __name__ == "__main__":
    unittest.main()
