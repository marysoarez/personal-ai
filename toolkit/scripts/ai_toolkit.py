#!/usr/bin/env python3
"""Local AI engineering harness. Core functionality uses only Python's standard library."""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from shutil import which

SKIP_DIRS = {".git", ".ai-toolkit", "node_modules", ".dart_tool", ".gradle", "build", "dist", "coverage", ".venv", "venv", "vendor", ".next", ".turbo"}
SENSITIVE_PATH = re.compile(r"(^|/)(\.env(?:\.[^/]*)?|\.npmrc|\.pypirc|\.netrc|[^/]+\.(?:pem|key|p12|pfx)|id_rsa|id_ed25519|credentials(?:\.json)?|service-account[^/]*\.json|serviceAccountKey\.json)$", re.I)
PLACEHOLDER = re.compile(r"(?i)(example|sample|dummy|placeholder|changeme|replace.?me|your[_ -].*(key|token|secret)|<[^>]+>|\*{3,}|x{6,})")
SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("stripe-secret", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{20,}\b")),
    ("sendgrid-token", re.compile(r"\bSG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b")),
    ("cloud-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("generic-assignment", re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd|secret)\b\s*[:=]\s*['\"]([^'\"\s]{12,})['\"]")),
    ("bearer-token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{24,}={0,2}")),
]
MAX_FILE_BYTES = 1_000_000
MAX_OUTPUT_BYTES = 200_000


class ToolkitError(Exception):
    """Expected configuration or usage error."""


def safe_json(path: Path) -> dict:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def package_manager(root: Path, package: dict | None = None) -> str:
    for lock, manager in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("bun.lock", "bun"), ("bun.lockb", "bun"), ("package-lock.json", "npm")):
        if (root / lock).exists():
            return manager
    declared = (package or {}).get("packageManager", "")
    return declared.split("@")[0] if declared else "npm"


def workspace_patterns(root: Path) -> list[str]:
    patterns: list[str] = []
    pkg = safe_json(root / "package.json")
    workspaces = pkg.get("workspaces", [])
    if isinstance(workspaces, dict):
        workspaces = workspaces.get("packages", [])
    if isinstance(workspaces, list):
        patterns.extend(item for item in workspaces if isinstance(item, str))
    pnpm = root / "pnpm-workspace.yaml"
    if pnpm.exists():
        in_packages = False
        for line in pnpm.read_text(encoding="utf-8", errors="replace").splitlines():
            if re.match(r"^packages\s*:", line):
                in_packages = True
                continue
            if in_packages:
                match = re.match(r"^\s*-\s*['\"]?([^#'\"]+)['\"]?\s*$", line)
                if match:
                    patterns.append(match.group(1).strip())
                elif line and not line[0].isspace():
                    break
    lerna = safe_json(root / "lerna.json")
    if isinstance(lerna.get("packages"), list):
        patterns.extend(x for x in lerna["packages"] if isinstance(x, str))
    config = safe_json(root / "ai-toolkit.json")
    if isinstance(config.get("packages"), list):
        patterns.extend(x for x in config["packages"] if isinstance(x, str))
    return list(dict.fromkeys(patterns))


def discover_package_dirs(root: Path, max_depth: int = 5) -> list[Path]:
    """Discover bounded package roots, never following symlinks outside root."""
    root = root.resolve()
    patterns = workspace_patterns(root)
    found: set[Path] = set()
    if patterns:
        excludes = [pattern[1:] for pattern in patterns if pattern.startswith("!")]
        for pattern in patterns:
            if pattern.startswith("!"):
                continue
            pattern_path = Path(pattern)
            if pattern_path.is_absolute() or ".." in pattern_path.parts:
                continue
            for candidate in root.glob(pattern):
                relative = candidate.relative_to(root).as_posix() if within(candidate, root) else ""
                if any(fnmatch.fnmatch(relative, exclusion) for exclusion in excludes):
                    continue
                if candidate.is_dir() and within(candidate, root) and not (set(candidate.parts) & SKIP_DIRS):
                    if (candidate / "package.json").is_file() or (candidate / "pubspec.yaml").is_file():
                        found.add(candidate.resolve())
    else:
        for base, dirs, files in os.walk(root, followlinks=False):
            current = Path(base)
            rel = current.relative_to(root)
            depth = len(rel.parts)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (current / d).is_symlink()]
            if depth > max_depth:
                dirs[:] = []
                continue
            if current != root and ("package.json" in files or "pubspec.yaml" in files):
                found.add(current.resolve())
            if len(found) >= 500:
                break
    return sorted(found, key=lambda p: str(p).casefold())


def stack_of(root: Path) -> tuple[list[str], dict]:
    stacks: list[str] = []
    info: dict = {"manifests": [], "package_manager": None, "scripts": {}, "config_files": [], "config_errors": []}
    pubspec = root / "pubspec.yaml"
    if pubspec.is_file():
        text = pubspec.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_BYTES]
        if not re.search(r"(?m)^name:\s*[a-zA-Z0-9_-]+\s*$", text):
            info["config_errors"].append("pubspec.yaml sem campo name válido")
        is_flutter = bool(re.search(r"(?m)^\s*(?:flutter|flutter_test|flutter_lints):", text)) or bool(re.search(r"(?m)^\s*sdk:\s*flutter\s*$", text))
        stacks.append("flutter" if is_flutter else "dart")
        info["manifests"].append("pubspec.yaml")
    package_file = root / "package.json"
    pkg = safe_json(package_file)
    if package_file.is_file():
        stacks.append("node")
        info["manifests"].append("package.json")
        try:
            if package_file.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("package.json excede 1 MB")
            json.loads(package_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            info["config_errors"].append("package.json inválido ou ilegível")
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if any(name in deps for name in ("react", "react-dom", "next")):
            stacks.append("react")
        info["package_manager"] = package_manager(root, pkg)
        info["scripts"] = pkg.get("scripts", {}) if isinstance(pkg.get("scripts", {}), dict) else {}
    toolkit_config = root / "ai-toolkit.json"
    if toolkit_config.is_file():
        try:
            if toolkit_config.stat().st_size > MAX_FILE_BYTES: raise ValueError("ai-toolkit.json excede 1 MB")
            parsed = json.loads(toolkit_config.read_text(encoding="utf-8"))
            if not isinstance(parsed, dict): raise ValueError("ai-toolkit.json deve conter um objeto JSON")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            info["config_errors"].append("ai-toolkit.json inválido ou ilegível")
    for name in ("tsconfig.json", "analysis_options.yaml", "vite.config.ts", "vite.config.js", "next.config.js", "next.config.mjs", "next.config.ts", "eslint.config.js", "eslint.config.mjs", "biome.json", "jest.config.js", "vitest.config.ts", "pubspec.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "pnpm-workspace.yaml"):
        if (root / name).exists():
            info["config_files"].append(name)
    return list(dict.fromkeys(stacks)), info


def available_tools() -> dict[str, str | None]:
    return {name: which(name) for name in ("git", "python", "python3", "node", "npm", "pnpm", "yarn", "bun", "flutter", "dart", "gitleaks")}


def validators_for(root: Path, stacks: list[str], info: dict, level: str, allow_scripts: bool) -> list[dict]:
    checks: list[dict] = []
    if "flutter" in stacks:
        checks.append({"name": "dart-format", "command": ["dart", "format", "--output=none", "--set-exit-if-changed", "."], "required": True, "tool": "dart", "reason": "Flutter/Dart formatting check"})
        checks.append({"name": "flutter-analyze", "command": ["flutter", "analyze"], "required": True, "tool": "flutter", "reason": "Flutter project static analysis"})
        if level in ("standard", "strict"):
            checks.append({"name": "flutter-test", "command": ["flutter", "test"], "required": True, "tool": "flutter", "reason": "Flutter test suite"})
    elif "dart" in stacks:
        checks.extend([
            {"name": "dart-format", "command": ["dart", "format", "--output=none", "--set-exit-if-changed", "."], "required": True, "tool": "dart", "reason": "Dart formatting check"},
            {"name": "dart-analyze", "command": ["dart", "analyze"], "required": True, "tool": "dart", "reason": "Dart static analysis"},
        ])
        if level in ("standard", "strict") and "test" in (info.get("scripts") or {}):
            checks.append({"name": "dart-test", "command": ["dart", "test"], "required": True, "tool": "dart", "reason": "Dart test suite"})
    if "node" in stacks:
        scripts = info.get("scripts", {})
        manager = info.get("package_manager") or "npm"
        wanted = ["lint"] if level == "basic" else ["lint", "typecheck", "type-check", "test", "build"]
        found: set[str] = set()
        for script in wanted:
            if script in scripts and script not in found:
                found.add(script)
                checks.append({"name": script, "command": [manager, "run", script], "required": True, "tool": manager, "reason": f"Script existente do package.json; execução {('autorizada' if allow_scripts else 'depende de --allow-project-scripts')}"})
        if not found:
            checks.append({"name": "project-scripts", "command": [], "required": False, "status": "skipped", "reason": "Nenhum script lint/typecheck/test/build conhecido declarado no package.json"})
        if not allow_scripts:
            for check in checks:
                if check.get("tool") == manager and check.get("command", [None])[0] == manager:
                    check["status"] = "not_run"
                    check["reason"] = "Scripts do projeto executam código definido pelo repositório; autorize explicitamente com --allow-project-scripts após revisar package.json"
        canonical = ["lint"] if level == "basic" else ["lint", "typecheck", "test", "build"]
        for name in canonical:
            aliases = ("typecheck", "type-check") if name == "typecheck" else (name,)
            if not any(alias in scripts for alias in aliases):
                checks.append({"name": name, "command": [], "required": False, "status": "skipped", "reason": f"Script {name} não definido no package.json"})
    if level == "strict":
        checks.append({"name": "gitleaks", "command": ["gitleaks", "dir", ".", "--redact", "--no-banner"], "required": False, "tool": "gitleaks", "reason": "Scanner externo opcional; varredura de arquivos locais, sem histórico Git"})
    if not checks:
        checks.append({"name": "stack-validation", "command": [], "required": False, "status": "skipped", "reason": "Nenhum adaptador de validação aplicável para as stacks detectadas"})
    return checks


def inspect(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ToolkitError(f"Raiz do projeto não é um diretório: {root}")
    package_dirs = discover_package_dirs(root)
    packages = []
    for directory in package_dirs:
        stacks, info = stack_of(directory)
        package_data = safe_json(directory / "package.json")
        dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
        packages.append({"name": (package_data.get("name") or directory.name), "path": directory.relative_to(root).as_posix(), "stacks": stacks, "manifests": info["manifests"], "scripts": sorted(info["scripts"]), "package_manager": info["package_manager"], "config_errors": info["config_errors"], "dependency_names": sorted(dependencies)})
    package_names = {item["name"]: item["path"] for item in packages}
    for item in packages:
        item["dependencies"] = sorted(package_names[name] for name in item.pop("dependency_names") if name in package_names and package_names[name] != item["path"])
    root_stacks, root_info = stack_of(root)
    is_mono = bool(packages and (len(packages) > 1 or workspace_patterns(root) or (root / "pnpm-workspace.yaml").exists()))
    if is_mono:
        all_stacks = list(dict.fromkeys(stack for package in packages for stack in package["stacks"]))
    else:
        all_stacks = root_stacks
        if packages:
            all_stacks = list(dict.fromkeys(all_stacks + [s for p in packages for s in p["stacks"]]))
    if not all_stacks:
        all_stacks = ["toolkit" if (root / "toolkit").is_dir() else "unknown"]
    commands = validators_for(root, root_stacks, root_info, "standard", True)
    for check in commands:
        executable = check.get("tool")
        if executable and not which(executable) and not check.get("status"):
            check["availability"] = "not_run"
            check["availability_reason"] = f"Ferramenta ausente: {executable}"
    if is_mono:
        commands = []
    instruction_files = []
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if "AGENTS.md" in files:
            instruction_files.append((Path(base) / "AGENTS.md").relative_to(root).as_posix())
        if len(instruction_files) >= 1000: break
    configured_skills = resolve_skills_root(root)
    skills = skill_index(configured_skills or root)
    return {"root": str(root), "stack": all_stacks, "is_monorepo": is_mono, "project_type": "monorepo" if is_mono else ("application" if root_stacks else ("toolkit" if "toolkit" in all_stacks else "unknown")), "packages": packages, "manifests": root_info["manifests"], "package_manager": root_info["package_manager"], "scripts": root_info["scripts"], "config_files": root_info["config_files"], "config_errors": root_info["config_errors"], "instruction_files": sorted(instruction_files), "available_tools": available_tools(), "checks_available": commands, "skills": skills}


SKILL_AREAS = {
    "flutter-development": "flutter", "flutter-architecture": "flutter", "criar-projeto-flutter": "flutter",
    "react-frontend": "react", "node-architecture": "node", "firebase-development": "firebase",
    "code-review": "review", "pkt-personal-code-review": "review", "criar-testes": "testing",
    "attack-defense": "security", "data-security": "privacy", "lgpd": "privacy",
    "escalabilidade": "performance", "criar-feature": "feature", "pkt-personal-feature": "feature",
    "pkt-personal-architecture": "architecture", "impeccable": "frontend-design",
}

SKILL_FLOWS = {
    "flutter-development": ["Flutter implementation", "debugging", "review"],
    "flutter-architecture": ["architecture decisions when Modular/MobX exists or is requested"],
    "criar-projeto-flutter": ["Flutter project bootstrap"],
    "criar-feature": ["end-to-end feature implementation"],
    "firebase-development": ["Firebase integration, rules, auth, indexes, Functions"],
    "node-architecture": ["Node.js backend changes"], "react-frontend": ["React UI and frontend changes"],
    "impeccable": ["UI design, UX, accessibility, visual refinement"],
    "code-review": ["general diff and pull request review"],
    "pkt-personal-code-review": ["PKT Personal review only"],
    "attack-defense": ["threat modeling and application security"],
    "data-security": ["personal/sensitive data handling"], "lgpd": ["Brazilian LGPD privacy analysis"],
    "criar-testes": ["test strategy and implementation"], "escalabilidade": ["performance, capacity, availability, cost"],
    "pkt-personal-architecture": ["PKT Personal architecture decisions only"],
    "pkt-personal-feature": ["PKT Personal feature implementation only"],
}

INTENT_TERMS = {
    "feature": {"feature", "funcionalidade", "implement", "criar", "adicionar", "endpoint", "fluxo"},
    "review": {"review", "revisao", "revisar", "code-review", "diff", "pull", "request"},
    "test": {"test", "teste", "tests", "cobertura", "regression"},
    "architecture": {"architecture", "arquitetura", "migrate", "migrar", "camadas", "modular", "mobx"},
    "bootstrap": {"bootstrap", "criar-projeto", "iniciar", "setup", "inicializar"},
    "ui": {"ui", "ux", "design", "layout", "interface", "visual", "acessibilidade", "frontend"},
    "security": {"security", "seguranca", "threat", "ameaça", "ataque", "auth", "authorization", "autorizacao"},
    "privacy": {"privacy", "privacidade", "lgpd", "pessoal", "sensivel", "titular", "retencao", "exclusao"},
    "firebase": {"firebase", "firestore", "functions", "flutterfire", "security-rules", "regras"},
    "scale": {"performance", "escalabilidade", "capacidade", "latencia", "disponibilidade", "custo", "scaling"},
}


def resolve_skills_root(project_root: Path, configured: str | None = None) -> Path | None:
    project_root = project_root.resolve()
    config = safe_json(project_root / "ai-toolkit.json")
    setting = configured or os.environ.get("AI_TOOLKIT_SKILLS_DIR") or config.get("skills_dir")
    candidate = Path(setting).expanduser() if setting else project_root / "skills"
    if not candidate.is_absolute():
        candidate = project_root / candidate
    candidate = candidate.resolve()
    return candidate if candidate.is_dir() and any(candidate.glob("*/SKILL.md")) else None


def skill_index(root: Path, query: str = "", stack: list[str] | None = None, pkt_project: bool | None = None) -> dict:
    """Read existing skill metadata instead of claiming skills from names alone."""
    root = root.resolve()
    skills_root = root / "skills" if (root / "skills").is_dir() else root if any(root.glob("*/SKILL.md")) else root / "skills"
    items = []
    if skills_root.is_dir():
        for skill_file in sorted(skills_root.glob("*/SKILL.md")):
            if not within(skill_file, root) or skill_file.stat().st_size > MAX_FILE_BYTES:
                continue
            with skill_file.open("r", encoding="utf-8", errors="replace") as source:
                content = source.read(12_000)
            if not content.startswith("---\n") and not content.startswith("---\r\n"):
                continue
            frontmatter = content.split("---", 2)[1]
            name_match = re.search(r"(?m)^name:\s*(.+?)\s*$", frontmatter)
            desc_match = re.search(r"(?m)^description:\s*(.+?)\s*$", frontmatter)
            name = name_match.group(1).strip().strip("\"'") if name_match else skill_file.parent.name
            description = desc_match.group(1).strip().strip("\"'") if desc_match else ""
            skill_dir = skill_file.parent
            resource_files = []
            for base, dirs, files in os.walk(skill_dir, followlinks=False):
                current = Path(base); dirs[:] = [d for d in dirs if not (current / d).is_symlink()]
                for filename in files:
                    item_path = current / filename
                    if filename != "SKILL.md" and within(item_path, skill_dir) and item_path.stat().st_size <= MAX_FILE_BYTES:
                        resource_files.append(item_path.relative_to(skill_dir).as_posix())
                    if len(resource_files) >= 500: break
                if len(resource_files) >= 500: break
            references = sorted(p for p in resource_files if "references" in Path(p).parts)
            scripts = sorted(p for p in resource_files if "scripts" in Path(p).parts)
            items.append({"name": name, "path": skill_file.relative_to(root).as_posix(), "area": SKILL_AREAS.get(name, "general"), "description": description, "conditions": description, "flows": SKILL_FLOWS.get(name, []), "references": references, "scripts": scripts, "supporting_files": sorted(resource_files), "found": True, "metadata_read": True, "loaded": False})
    return {"root": str(root), "count": len(items), "skills": items}


def project_is_pkt(root: Path) -> bool:
    if root.name.casefold().startswith("pkt-personal"):
        return True
    pubspec = root / "pubspec.yaml"
    if pubspec.is_file() and pubspec.stat().st_size <= MAX_FILE_BYTES:
        body = pubspec.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?mi)^name:\s*['\"]?pkt[_-]personal(?:['\"])?\s*$", body):
            return True
    readme = root / "README.md"
    if readme.is_file():
        first_lines = "\n".join(readme.read_text(encoding="utf-8", errors="replace").splitlines()[:12])
        return bool(re.search(r"(?mi)^#\s+PKT Personal(?:\s+app)?\s*$", first_lines))
    return False


def project_features(root: Path, stacks: list[str]) -> set[str]:
    features = set(stacks)
    pkg = safe_json(root / "package.json")
    pubspec = root / "pubspec.yaml"
    text = pubspec.read_text(encoding="utf-8", errors="replace") if pubspec.is_file() and pubspec.stat().st_size <= MAX_FILE_BYTES else ""
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    if any("firebase" in name.casefold() for name in deps) or re.search(r"(?m)^\s*(?:cloud_firestore|firebase_\w+|firebase-admin):", text):
        features.add("firebase")
    if {"flutter_modular", "mobx", "flutter_mobx"} & set(deps) or re.search(r"(?m)^\s*(?:flutter_modular|mobx|flutter_mobx):", text):
        features.add("flutter-modular-mobx")
    if project_is_pkt(root):
        features.add("pkt")
    return features


def relevant_skills(project_root: Path, task: str = "", skills_root: Path | None = None) -> dict:
    project_root = project_root.resolve()
    inspection = inspect(project_root)
    skills_root = skills_root or resolve_skills_root(project_root)
    if not skills_root:
        return {"skills_root": None, "count": 0, "skills": [], "warning": "Nenhum diretório de skills configurado/encontrado; configure ai-toolkit.json skills_dir ou --skills-root."}
    features = project_features(project_root, inspection["stack"])
    tokens = set(re.findall(r"[a-z0-9_-]{3,}", task.casefold()))
    intents = {intent for intent, terms in INTENT_TERMS.items() if tokens & terms}
    selected: dict[str, set[str]] = {}
    def add(name: str, why: str):
        selected.setdefault(name, set()).add(why)
    if "flutter" in features or "dart" in features:
        add("flutter-development", "stack Flutter/Dart detectada")
        if "architecture" in intents and ("modular" in tokens or "mobx" in tokens or "flutter-modular-mobx" in features): add("flutter-architecture", "arquitetura Modular/MobX solicitada ou identificada")
        if "bootstrap" in intents: add("criar-projeto-flutter", "tarefa de bootstrap Flutter")
    if "react" in features: add("react-frontend", "stack React detectada")
    if "node" in features: add("node-architecture", "stack Node.js detectada")
    if "firebase" in features or "firebase" in intents: add("firebase-development", "Firebase detectado ou mencionado")
    if "feature" in intents:
        add("criar-feature", "implementação ponta a ponta solicitada")
        add("criar-testes", "feature requer estratégia de testes contextual")
        add("code-review", "revisão final do diff da implementação")
    if "test" in intents: add("criar-testes", "estratégia ou implementação de testes solicitada")
    if "review" in intents: add("code-review", "revisão de alterações solicitada")
    if "ui" in intents and "react" in features: add("impeccable", "design/UX/frontend visual solicitado")
    if "security" in intents: add("attack-defense", "segurança ou modelagem de ameaças solicitada")
    if "privacy" in intents: add("data-security", "dados pessoais ou sensíveis no escopo") ; add("lgpd", "privacidade/LGPD no escopo")
    if "scale" in intents: add("escalabilidade", "desempenho/capacidade/disponibilidade no escopo")
    if "pkt" in features:
        add("pkt-personal-architecture", "repositório PKT Personal identificado")
        if "feature" in intents: add("pkt-personal-feature", "feature PKT Personal solicitada")
        if "review" in intents: add("pkt-personal-code-review", "revisão PKT Personal solicitada")
        if "review" in intents: selected.pop("code-review", None)
    indexed = {item["name"]: item for item in skill_index(skills_root)["skills"]}
    result = []
    for name, reasons in selected.items():
        if name in indexed:
            result.append({**indexed[name], "reasons": sorted(reasons), "loaded": False})
    return {"project_root": str(project_root), "skills_root": str(skills_root.resolve()), "project_features": sorted(features), "task_intents": sorted(intents), "count": len(result), "skills": result}


def read_skill(skills_root: Path, name: str) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", name):
        raise ToolkitError("Nome de skill inválido")
    path = (skills_root / name / "SKILL.md").resolve()
    if not within(path, skills_root.resolve()) or not path.is_file():
        raise ToolkitError(f"Skill não encontrada: {name}")
    if SENSITIVE_PATH.search(path.name) or path.stat().st_size > MAX_FILE_BYTES:
        raise ToolkitError("Arquivo skill não permitido ou excede 1 MB")
    body = path.read_text(encoding="utf-8", errors="replace")
    skill_dir = path.parent
    resources = sorted(p.relative_to(skill_dir).as_posix() for p in skill_dir.rglob("*") if p.is_file() and p.name != "SKILL.md" and within(p, skill_dir) and p.stat().st_size <= MAX_FILE_BYTES)
    return {"name": name, "path": path.relative_to(skills_root.resolve()).as_posix(), "content": body, "references_available": [p for p in resources if "references" in Path(p).parts], "scripts_available": [p for p in resources if "scripts" in Path(p).parts], "supporting_files_available": resources, "loaded": True}


def read_skill_reference(skills_root: Path, name: str, relative_path: str) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", name):
        raise ToolkitError("Nome de skill inválido")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ToolkitError("Caminho de referência inválido")
    skill_dir = (skills_root / name).resolve()
    target = (skill_dir / relative).resolve()
    if not within(target, skill_dir) or not target.is_file() or target.stat().st_size > MAX_FILE_BYTES or SENSITIVE_PATH.search(target.name):
        raise ToolkitError("Referência não encontrada ou não permitida")
    content = target.read_text(encoding="utf-8", errors="replace")
    return {"skill": name, "path": relative.as_posix(), "content": content, "bytes": target.stat().st_size, "found_and_read": True}


def project_context(root: Path, task: str = "", skills_root: Path | None = None, max_files: int = 20, max_total_chars: int = 160_000) -> dict:
    root = root.resolve()
    if max_files < 1 or max_files > 100:
        raise ToolkitError("max_files precisa estar entre 1 e 100")
    inspection = inspect(root)
    picks: list[Path] = []
    for rel in ("AGENTS.md", "README.md", "CONTRIBUTING.md", "ARCHITECTURE.md", "docs/architecture.md", "ai-toolkit.json", "package.json", "pubspec.yaml", "analysis_options.yaml", "tsconfig.json"):
        path = root / rel
        if path.is_file(): picks.append(path)
    for rel in inspection["instruction_files"]:
        path = root / rel
        if path not in picks: picks.append(path)
    terms = {term for term in re.findall(r"[a-z0-9_-]{3,}", task.casefold()) if term not in {"feature", "task", "please", "implement", "create", "fix"}}
    candidates = []
    for base, dirs, files in os.walk(root, followlinks=False):
        current = Path(base)
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not (current / name).is_symlink()]
        if len(current.relative_to(root).parts) > 7:
            dirs[:] = []; continue
        for filename in files:
            if not filename.casefold().endswith((".py", ".dart", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yaml", ".yml")):
                continue
            path = current / filename
            if path.name == "SKILL.md" or SENSITIVE_PATH.search(path.name) or path.is_symlink() or path.stat().st_size > 80_000:
                continue
            relative = path.relative_to(root).as_posix()
            lowered = relative.casefold()
            priority = 0
            if any(key in lowered for key in ("test", "spec")): priority += 2
            if any(term in lowered for term in terms): priority += 4
            if any(part in lowered for part in ("src/", "lib/", "app/", "pages/", "features/")): priority += 1
            if priority: candidates.append((priority, relative, path))
    for _, _, path in sorted(candidates, key=lambda item: (-item[0], item[1])):
        if path not in picks: picks.append(path)
    files_out, omitted = [], []
    remaining = max_total_chars
    for path in picks:
        if len(files_out) >= max_files or remaining <= 0: break
        if not within(path, root) or not path.is_file() or path.stat().st_size > 80_000: continue
        relative = path.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in Path(relative).parts) or SENSITIVE_PATH.search(relative):
            omitted.append({"path": relative, "reason": "caminho excluído/sensível"}); continue
        content = path.read_text(encoding="utf-8", errors="replace")
        if scan_secret_text(content):
            omitted.append({"path": relative, "reason": "padrão de segredo suspeito; conteúdo omitido"}); continue
        content = content[:remaining]
        files_out.append({"path": relative, "content": content})
        remaining -= len(content)
    selected = relevant_skills(root, task, skills_root) if skills_root else relevant_skills(root, task)
    return {"project": {"root": str(root), "stack": inspection["stack"], "is_monorepo": inspection["is_monorepo"], "packages": inspection["packages"]}, "task": task, "instruction_hierarchy": ["requisitos explícitos e segurança de maior prioridade", "instruções do repositório", "especificação da tarefa", "skills especializadas selecionadas", "adaptador de stack", "recomendações gerais do toolkit"], "files": files_out, "omitted": omitted, "skills_to_load_progressively": [{"name": item["name"], "path": item["path"], "reasons": item["reasons"], "references": item["references"], "scripts": item["scripts"]} for item in selected["skills"]], "limits": {"max_files": max_files, "max_total_chars": max_total_chars, "secrets": "conteúdo com padrões suspeitos omitido; heurístico"}}
    if query:
        terms = set(re.findall(r"[a-z0-9_-]{3,}", query.casefold()))
        for item in items:
            searchable = f"{item['name']} {item['area']} {item['description']}".casefold()
            item["relevance"] = sum(term in searchable for term in terms)
        items.sort(key=lambda item: (-item.get("relevance", 0), item["name"]))
    return {"root": str(skills_root), "count": len(items), "skills": items}


def _reader(pipe, chunks: deque, max_bytes: int, total: list[int]):
    while True:
        data = pipe.read(8192)
        if not data:
            break
        total[0] += len(data)
        remaining = max_bytes - sum(len(c) for c in chunks)
        if remaining > 0:
            chunks.append(data[:remaining])


def _windows_kill_job(process) -> object:
    """Create a Windows Job Object that kills the process tree on close."""
    import ctypes
    from ctypes import wintypes

    class BasicLimit(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimit(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimit), ("IoInfo", IoCounters), ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.Thread32First.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel.OpenThread.restype = wintypes.HANDLE
    kernel.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
    settings = ExtendedLimit()
    settings.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(job, 9, ctypes.byref(settings), ctypes.sizeof(settings)):
        error = ctypes.get_last_error(); kernel.CloseHandle(job)
        raise OSError(error, "SetInformationJobObject failed")
    if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(process._handle)):
        error = ctypes.get_last_error(); kernel.CloseHandle(job)
        raise OSError(error, "AssignProcessToJobObject failed")
    class ThreadEntry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD), ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG), ("dwFlags", wintypes.DWORD)]
    snapshot = kernel.CreateToolhelp32Snapshot(0x00000004, 0)  # TH32CS_SNAPTHREAD
    entry = ThreadEntry(); entry.dwSize = ctypes.sizeof(entry)
    found = False
    if snapshot and kernel.Thread32First(snapshot, ctypes.byref(entry)):
        while True:
            if entry.th32OwnerProcessID == process.pid:
                thread = kernel.OpenThread(0x0002, False, entry.th32ThreadID)  # THREAD_SUSPEND_RESUME
                if thread:
                    kernel.ResumeThread(thread); kernel.CloseHandle(thread); found = True; break
            if not kernel.Thread32Next(snapshot, ctypes.byref(entry)): break
    if snapshot: kernel.CloseHandle(snapshot)
    if not found:
        error = ctypes.get_last_error(); kernel.CloseHandle(job)
        raise OSError(error, "Could not resume suspended process")
    return (kernel, job)


def run_process(command: list[str], cwd: Path, timeout: int, max_output: int = MAX_OUTPUT_BYTES) -> dict:
    started = time.monotonic()
    kwargs = {"cwd": cwd, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "shell": False}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000004  # CREATE_SUSPENDED until assigned to a kill-on-close job
    else:
        kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(command, **kwargs)
    except FileNotFoundError:
        return {"status": "not_run", "reason": f"Ferramenta ausente: {command[0]}", "exit_code": None, "stdout": "", "stderr": "", "duration_seconds": 0}
    except OSError as exc:
        return {"status": "error", "reason": f"Não foi possível iniciar o processo ({type(exc).__name__})", "exit_code": None, "stdout": "", "stderr": "", "duration_seconds": round(time.monotonic() - started, 2)}
    job = None
    if os.name == "nt":
        try:
            job = _windows_kill_job(process)
        except OSError as exc:
            process.kill(); process.wait()
            return {"status": "error", "reason": f"Não foi possível controlar a árvore de processos ({type(exc).__name__})", "exit_code": None, "stdout": "", "stderr": "", "duration_seconds": round(time.monotonic() - started, 2)}
    out_chunks: deque[bytes] = deque()
    err_chunks: deque[bytes] = deque()
    out_total, err_total = [0], [0]
    out_thread = threading.Thread(target=_reader, args=(process.stdout, out_chunks, max_output, out_total), daemon=True)
    err_thread = threading.Thread(target=_reader, args=(process.stderr, err_chunks, max_output, err_total), daemon=True)
    out_thread.start(); err_thread.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
        process.wait(timeout=5)
    except KeyboardInterrupt:
        try:
            if os.name == "nt":
                job[0].CloseHandle(job[1])
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        finally:
            process.stdout.close(); process.stderr.close()
        raise
    finally:
        if job:
            job[0].CloseHandle(job[1])
    out_thread.join(timeout=3); err_thread.join(timeout=3)
    process.stdout.close(); process.stderr.close()
    stdout = b"".join(out_chunks).decode("utf-8", errors="replace")
    stderr = b"".join(err_chunks).decode("utf-8", errors="replace")
    if out_total[0] > len(stdout.encode()): stdout += "\n[saída truncada]"
    if err_total[0] > len(stderr.encode()): stderr += "\n[saída truncada]"
    return {"status": "failed" if timed_out or process.returncode else "passed", "reason": f"Timeout após {timeout}s" if timed_out else None, "exit_code": 124 if timed_out else process.returncode, "stdout": stdout, "stderr": stderr, "duration_seconds": round(time.monotonic() - started, 2)}


def run_checks(root: Path, checks: list[dict], timeout: int, max_output: int = MAX_OUTPUT_BYTES, continue_packages: bool = False, deadline: float | None = None) -> list[dict]:
    results = []
    stop = False
    for check in checks:
        if check.get("status") in ("skipped", "not_run"):
            results.append({**check, "exit_code": None, "stdout": "", "stderr": ""})
            continue
        if stop:
            results.append({**check, "status": "not_run", "reason": "Uma verificação obrigatória anterior falhou", "exit_code": None, "stdout": "", "stderr": ""})
            continue
        command = check.get("command", [])
        if not command:
            results.append({**check, "status": "skipped", "reason": check.get("reason", "Comando não configurado"), "exit_code": None, "stdout": "", "stderr": ""})
            continue
        if not which(command[0]):
            results.append({**check, "status": "not_run", "reason": f"Ferramenta ausente: {command[0]}", "exit_code": None, "stdout": "", "stderr": ""})
            continue
        if deadline and deadline <= time.monotonic():
            results.append({**check, "status": "not_run", "reason": "Tempo limite global da validação esgotado", "exit_code": None, "stdout": "", "stderr": ""})
            continue
        remaining = min(timeout, max(1, int(deadline - time.monotonic()))) if deadline else timeout
        result = run_process(command, root, remaining, max_output)
        results.append({**check, **result})
        if result["status"] in ("failed", "error") and check.get("required", True) and not continue_packages:
            stop = True
    return results


def aggregate(checks: list[dict]) -> dict:
    counts = {state: sum(1 for item in checks if item.get("status") == state) for state in ("passed", "failed", "skipped", "not_run", "error")}
    counts["status"] = "error" if counts["error"] else "failed" if counts["failed"] else "not_run" if counts["passed"] == 0 and (counts["not_run"] or counts["skipped"]) else "partial" if counts["not_run"] else "passed"
    return counts


def architecture_check(root: Path) -> dict:
    """Evaluate only repository-declared import boundaries; no universal architecture is imposed."""
    config = safe_json(root / "ai-toolkit.json")
    rules = config.get("architecture_rules", {})
    boundary_rules = rules.get("forbidden_imports", []) if isinstance(rules, dict) else []
    if not boundary_rules:
        return {"applicable": False, "status": "skipped", "reason": "Nenhuma regra arquitetural local declarada", "findings": []}
    normalized = []
    try:
        for item in boundary_rules:
            if not isinstance(item, dict) or not isinstance(item.get("files"), str) or not isinstance(item.get("patterns"), list):
                raise ValueError("cada regra requer files e patterns")
            normalized.append((item["files"], [re.compile(pattern, re.I) for pattern in item["patterns"] if isinstance(pattern, str)]))
    except (ValueError, re.error) as exc:
        return {"applicable": True, "status": "error", "reason": f"architecture_rules inválido ({type(exc).__name__})", "findings": []}
    findings = []
    scanned = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        current = Path(base); dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not (current / name).is_symlink()]
        for filename in files:
            path = current / filename
            if path.is_symlink() or path.stat().st_size > MAX_FILE_BYTES or SENSITIVE_PATH.search(filename): continue
            relative = path.relative_to(root).as_posix()
            matching = [patterns for glob, patterns in normalized if fnmatch.fnmatch(relative, glob)]
            if not matching: continue
            scanned += 1
            if scanned > 10_000:
                return {"applicable": True, "status": "error", "reason": "Limite de 10.000 arquivos de arquitetura excedido", "findings": findings}
            content = path.read_text(encoding="utf-8", errors="replace")
            for line_number, line in enumerate(content.splitlines(), 1):
                for patterns in matching:
                    for pattern in patterns:
                        if pattern.search(line):
                            findings.append({"path": relative, "line": line_number, "rule": pattern.pattern, "message": "Import/padrão viola regra arquitetural declarada neste repositório"})
    return {"applicable": True, "status": "failed" if findings else "passed", "scanned_files": scanned, "findings": findings}


def validate_project(root: Path, level: str = "standard", timeout: int = 600, allow_scripts: bool = False, selected_package: str | None = None, affected: bool = False, total_timeout: int = 1800) -> dict:
    info = inspect(root)
    root = root.resolve()
    packages = info["packages"]
    targets: list[tuple[str, Path]] = []
    if selected_package:
        match = next((p for p in packages if p["path"] == selected_package or p["name"] == selected_package), None)
        if not match:
            raise ToolkitError(f"Pacote não encontrado: {selected_package}")
        targets = [(match["path"], (root / match["path"]).resolve())]
    elif info["is_monorepo"]:
        changed = set(changed_files(root)) if affected else None
        root_configs = {"package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json", "bun.lock", "bun.lockb", "pnpm-workspace.yaml", "lerna.json", "ai-toolkit.json", "pubspec.yaml"}
        affected_paths = {p["path"] for p in packages if changed is None or any(f == p["path"] or f.startswith(p["path"] + "/") for f in changed)}
        if affected and any(file in root_configs for file in changed or set()):
            affected_paths = {p["path"] for p in packages}
        # A changed dependency invalidates its in-repository consumers as well.
        dependency_map = {p["path"]: set(p.get("dependencies", [])) for p in packages}
        changed_dependencies = True
        while changed_dependencies:
            changed_dependencies = False
            for consumer, dependencies in dependency_map.items():
                if dependencies & affected_paths and consumer not in affected_paths:
                    affected_paths.add(consumer); changed_dependencies = True
        for package in packages:
            package_root = (root / package["path"]).resolve()
            if not within(package_root, root):
                continue
            if package["path"] in affected_paths:
                targets.append((package["path"], package_root))
    else:
        targets = [(".", root)]
    package_results = []
    deadline = time.monotonic() + total_timeout
    for label, package_root in targets:
        stacks, details = stack_of(package_root)
        if details["config_errors"]:
            errors = [{"name": "project-configuration", "status": "error", "required": True, "reason": issue, "exit_code": None, "stdout": "", "stderr": ""} for issue in details["config_errors"]]
            package_results.append({"package": label, "root": str(package_root), "stack": stacks, "checks": errors, "summary": aggregate(errors)})
            continue
        checks = validators_for(package_root, stacks, details, level, allow_scripts)
        results = run_checks(package_root, checks, timeout, continue_packages=info["is_monorepo"], deadline=deadline)
        package_results.append({"package": label, "root": str(package_root), "stack": stacks, "checks": results, "summary": aggregate(results)})
        if (package_root / "ai-toolkit.json").is_file():
            architecture = architecture_check(package_root)
            if architecture["applicable"]:
                package_results[-1]["checks"].append({"name": "architecture-boundaries", "status": architecture["status"], "required": True, "reason": architecture.get("reason"), "findings": architecture["findings"], "exit_code": 1 if architecture["status"] == "failed" else 0 if architecture["status"] == "passed" else None, "stdout": "", "stderr": ""})
                package_results[-1]["summary"] = aggregate(package_results[-1]["checks"])
    if (root / "ai-toolkit.json").is_file():
        architecture = architecture_check(root)
        if architecture["applicable"] and (len(packages) > 1 or info["is_monorepo"]):
            check = {"name": "workspace-architecture-boundaries", "status": architecture["status"], "required": True, "reason": architecture.get("reason"), "findings": architecture["findings"], "exit_code": 1 if architecture["status"] == "failed" else 0 if architecture["status"] == "passed" else None, "stdout": "", "stderr": ""}
            package_results.append({"package": "(workspace rules)", "root": str(root), "stack": info["stack"], "checks": [check], "summary": aggregate([check])})
    flat = [check for package in package_results for check in package["checks"]]
    return {"project": {"root": str(root), "stack": info["stack"], "is_monorepo": info["is_monorepo"]}, "level": level, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "packages": package_results, "checks": flat, "summary": aggregate(flat)}


def _normalize_heading(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def validate_spec(path: Path, text: str | None = None) -> dict:
    if text is None:
        if not path.is_file():
            return {"status": "error", "errors": [f"Arquivo não encontrado: {path}"], "warnings": []}
        if path.stat().st_size > MAX_FILE_BYTES:
            return {"status": "error", "errors": ["Especificação excede limite de tamanho de 1 MB"], "warnings": []}
        text = path.read_text(encoding="utf-8", errors="replace")
    sections: dict[str, str] = {}
    current = ""
    for line in text.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if heading:
            current = _normalize_heading(heading.group(1))
            sections[current] = ""
        elif current:
            sections[current] += line + "\n"
    aliases = {
        "problem": ("problema", "problem"), "objective": ("objetivo", "objective"),
        "scope": ("escopo", "scope"), "exclusions": ("fora de escopo", "fora do escopo", "exclusões", "out of scope"),
        "functional": ("requisitos funcionais", "functional requirements"),
        "nonfunctional": ("requisitos não funcionais", "requisitos nao funcionais", "non functional requirements"),
        "acceptance": ("critérios de aceitação", "criterios de aceitacao", "acceptance criteria"),
        "tests": ("estratégia de testes", "estrategia de testes", "test strategy", "testes"),
        "security": ("segurança e privacidade", "seguranca e privacidade", "segurança", "seguranca", "security and privacy"),
        "risks": ("riscos", "risks"), "dependencies": ("dependências", "dependencias", "dependencies"),
        "implementation": ("plano de implementação", "plano de implementacao", "implementation plan"),
        "validation": ("estratégia de validação", "estrategia de validacao", "validation strategy", "definição de pronto", "definicao de pronto"),
    }
    def find_section(names):
        for heading, body in sections.items():
            if any(_normalize_heading(name) == heading or _normalize_heading(name) in heading for name in names):
                return body
        return None
    required = ("problem", "objective", "scope", "exclusions", "functional", "acceptance", "tests", "security", "risks", "dependencies", "implementation", "validation")
    errors, warnings = [], []
    bodies = {}
    for key, names in aliases.items():
        bodies[key] = find_section(names)
    for key in required:
        body = bodies[key]
        meaningful = re.sub(r"(?i)\b(?:TODO|TBD|RF-?\d+|RNF-?\d+|CA-?\d+)\b|\[\s*\]|[\s*`_\-#:.]", "", body or "")
        meaningful = re.sub(r"(?i)(given|when|then|dado|quando|então|entao)", "", meaningful)
        meaningful = meaningful.replace("...", "").replace("…", "")
        if body is None or len(meaningful.strip()) < 3:
            errors.append(f"Seção obrigatória sem conteúdo: {key}")
    if not re.search(r"(?i)\b(?:SPEC|SPECIFICATION|ESPECIFICAÇÃO|ESPECIFICACAO)[-_ ]?\d+\b", text):
        errors.append("Identificador da especificação ausente (ex.: SPEC-123)")
    if bodies["nonfunctional"] is None:
        warnings.append("Considere requisitos não funcionais relevantes (performance, disponibilidade, acessibilidade, etc.)")
    criteria = bodies["acceptance"] or ""
    criterion_items = [line.strip(" -*[]0123456789.") for line in criteria.splitlines() if line.strip().startswith(("-", "*", "[", "Given", "Dado", "Quando", "Then", "Então"))]
    if not criterion_items:
        errors.append("Critérios de aceitação precisam incluir ao menos um item verificável")
    generic = [item for item in criterion_items if re.search(r"(?i)\b(funciona|correto|adequado|intuitivo|rápido|seguro|deve funcionar)\b", item) and not re.search(r"(?i)(given|dado|quando|then|então|assert|status|código|resultado|em até|no máximo|igual a|retorna)", item)]
    if generic:
        if len(generic) == len(criterion_items):
            errors.append("Critérios de aceitação sem condição claramente observável: " + "; ".join(generic[:3]))
        else:
            warnings.append("Critério(s) potencialmente subjetivo(s); adicione uma condição observável: " + "; ".join(generic[:3]))
    if len(text) < 300:
        warnings.append("Especificação curta; confirme se os requisitos e cenários têm detalhe suficiente")
    return {"status": "failed" if errors else "passed", "errors": errors, "warnings": warnings, "sections_found": [key for key, body in bodies.items() if body is not None]}


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    command = ["git", "-C", str(root), *args]
    if not which("git"):
        raise ToolkitError("Git não está instalado")
    result = run_process(command, root, 20, max_output=5_000_000)
    if result.get("status") == "not_run":
        raise ToolkitError(result.get("reason", "Git não disponível"))
    if "[saída truncada]" in result.get("stdout", ""):
        raise ToolkitError("Saída do Git ultrapassou 5 MB; análise interrompida com segurança")
    return subprocess.CompletedProcess(command, result.get("exit_code") or 0, result.get("stdout", ""), result.get("stderr", ""))


def changed_entries(root: Path) -> list[dict]:
    result = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if result.returncode:
        raise ToolkitError("Diretório não está em um repositório Git válido")
    if result.returncode:
        raise ToolkitError("Não foi possível consultar o status do Git")
    values = result.stdout.split("\0")
    entries = []
    i = 0
    while i < len(values) and values[i]:
        raw = values[i]; i += 1
        status = raw[:2]
        path = raw[3:].replace("\\", "/")
        if "R" in status or "C" in status:
            path = values[i].replace("\\", "/") if i < len(values) else path
            i += 1
        kind = "added" if "?" in status or "A" in status else "deleted" if "D" in status else "modified"
        entries.append({"path": path, "kind": kind, "git_status": status})
    return entries


def _redacted_finding(kind: str, value: str) -> str:
    digest = __import__("hashlib").sha256(value.encode()).hexdigest()[:10]
    return f"Possível segredo ({kind}; impressão digital sha256:{digest}); valor omitido"


def scan_secret_text(text: str) -> list[dict]:
    findings = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            value = match.group(match.lastindex) if match.lastindex else match.group(0)
            if PLACEHOLDER.search(value):
                continue
            findings.append({"line": line_number, "kind": kind, "confidence": "suspected", "message": _redacted_finding(kind, value)})
    return findings


def diff_findings(root: Path, entries: list[dict]) -> list[dict]:
    paths = [entry["path"] for entry in entries if entry["kind"] != "deleted"]
    findings = []
    for entry in entries:
        path = entry["path"]
        if SENSITIVE_PATH.search(path):
            findings.append({"path": path, "kind": "sensitive-path", "confidence": "suspected", "message": "Arquivo com nome sensível foi alterado; conteúdo não foi lido"})
        if re.search(r"(?i)(package\.json|.*lock|pubspec\.yaml|.*\.ya?ml|\.github/workflows/.*)", path):
            findings.append({"path": path, "kind": "dependency-or-config", "confidence": "review", "message": "Alteração em dependências ou configuração requer revisão"})
    diff = git(root, "diff", "HEAD", "--", *paths) if paths else None
    if diff and diff.returncode == 0:
        current = None; lineno = 0
        for line in diff.stdout.splitlines():
            if line.startswith("+++ b/"):
                current = line[6:]
            elif line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                lineno = int(match.group(1)) if match else 0
            elif line.startswith("+") and not line.startswith("+++"):
                for finding in scan_secret_text(line[1:]):
                    findings.append({"path": current, "line": lineno, **finding})
                lineno += 1
            elif not line.startswith("-"):
                lineno += 1
    for entry in entries:
        if entry["kind"] != "added" or SENSITIVE_PATH.search(entry["path"]):
            continue
        path = root / entry["path"]
        if not within(path, root) or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            continue
        if any(part in SKIP_DIRS for part in Path(entry["path"]).parts):
            continue
        try:
            findings.extend({"path": entry["path"], **finding} for finding in scan_secret_text(path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return findings


def validate_change_scope(root: Path, entries: list[dict], scopes: list[str] | None, spec_path: Path | None, ignore_secrets: list[str] | None = None) -> dict:
    findings = diff_findings(root, entries)
    ignored = []
    for allow in ignore_secrets or []:
        match = re.fullmatch(r"(.+):(\d+)", allow.replace("\\", "/"))
        if not match:
            raise ToolkitError(f"Supressão inválida; use path:line: {allow}")
        path = match.group(1)
        while path.startswith("./"):
            path = path[2:]
        path, line = path, int(match.group(2))
        before = len(findings)
        findings = [item for item in findings if not (item.get("path") == path and item.get("line") == line and item.get("kind") not in ("sensitive-path", "dependency-or-config", "out-of-scope"))]
        if len(findings) != before:
            ignored.append({"path": path, "line": line, "reason": "supressão explícita via CLI"})
    if scopes:
        normalized = [scope.replace("\\", "/").strip("/") for scope in scopes]
        for entry in entries:
            if not any(entry["path"] == prefix or entry["path"].startswith(prefix + "/") for prefix in normalized):
                findings.append({"path": entry["path"], "kind": "out-of-scope", "confidence": "confirmed", "message": "Arquivo fora do escopo informado"})
    if spec_path:
        spec_result = validate_spec(spec_path)
        if spec_result["status"] != "passed":
            findings.append({"path": str(spec_path), "kind": "invalid-reference-spec", "confidence": "confirmed", "message": "A especificação de referência não passou na validação estrutural"})
        else:
            spec_text = spec_path.read_text(encoding="utf-8", errors="replace").casefold()
            for entry in entries:
                tokens = [t for t in re.split(r"[^a-z0-9_-]+", Path(entry["path"]).stem.casefold()) if len(t) >= 5]
                if tokens and not any(token in spec_text for token in tokens):
                    findings.append({"path": entry["path"], "kind": "spec-alignment-review", "confidence": "review", "message": "Nome do arquivo não aparece na especificação; verificar aderência manualmente"})
    risky = any(f["confidence"] == "confirmed" or f["kind"] in {"private-key", "google-api-key", "stripe-secret", "sendgrid-token", "cloud-access-key", "github-token", "github-fine-grained-token", "slack-token", "generic-assignment", "bearer-token", "sensitive-path"} for f in findings)
    return {"files": entries, "findings": findings, "ignored_findings": ignored, "status": "attention" if risky else "passed", "summary": aggregate([{"status": "failed" if f["confidence"] == "confirmed" else "not_run"} for f in findings]) if findings else aggregate([])}


def markdown_report(report: dict) -> str:
    lines = ["# Relatório de validação", "", f"- Projeto: `{report['project']['root']}`", f"- Stack: {', '.join(report['project']['stack'])}", f"- Nível: {report['level']}", f"- Estado geral: **{report['summary']['status']}**", "", "| Pacote | Verificação | Estado | Código | Motivo |", "|---|---|---|---:|---|"]
    for package in report["packages"]:
        for check in package["checks"]:
            lines.append(f"| `{package['package']}` | {check['name']} | {check['status']} | {check.get('exit_code') if check.get('exit_code') is not None else '—'} | {check.get('reason') or ''} |")
    return "\n".join(lines) + "\n"


def print_json(value: dict):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI Engineering Toolkit CLI")
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("inspect", help="Detecta stack, pacotes, ferramentas e validadores disponíveis"); p.add_argument("project", nargs="?", default="."); p.add_argument("--json", action="store_true")
    p = sub.add_parser("validate", help="Executa validadores permitidos e grava relatório"); p.add_argument("project", nargs="?", default="."); p.add_argument("--timeout", type=int, default=600, help="Timeout por comando em segundos"); p.add_argument("--total-timeout", type=int, default=1800, help="Timeout global em segundos"); p.add_argument("--level", choices=("basic", "standard", "strict"), default="standard"); p.add_argument("--package"); p.add_argument("--affected", action="store_true"); p.add_argument("--allow-project-scripts", action="store_true", help="Autoriza executar scripts definidos no package.json; revise-os antes"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("validate-spec", help="Valida estrutura e verificabilidade básica de uma especificação"); p.add_argument("file"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("validate-changes", help="Inspeciona diff e executa apenas validadores do catálogo compatíveis com os pacotes afetados"); p.add_argument("project", nargs="?", default="."); p.add_argument("--scope", action="append"); p.add_argument("--spec"); p.add_argument("--ignore-secret", action="append", help="Suprime suspeita específica path:line após revisão explícita"); p.add_argument("--level", choices=("basic", "standard", "strict"), default="basic"); p.add_argument("--timeout", type=int, default=600); p.add_argument("--total-timeout", type=int, default=1800); p.add_argument("--allow-project-scripts", action="store_true", help="Autoriza scripts dos manifests, após revisão explícita"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("summarize", help="Gera resumo estruturado e retomável"); p.add_argument("project", nargs="?", default="."); p.add_argument("--objective", required=True); p.add_argument("--output", default=".ai-toolkit/task-summary.json"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("packages", help="Lista pacotes detectados"); p.add_argument("project", nargs="?", default="."); p.add_argument("--json", action="store_true")
    p = sub.add_parser("skills-index", help="Indexa skills encontradas e lidas no repositório"); p.add_argument("project", nargs="?", default="."); p.add_argument("--query", default=""); p.add_argument("--json", action="store_true")
    p = sub.add_parser("find-skills", help="Seleciona skills relevantes sem carregar seu conteúdo principal"); p.add_argument("project", nargs="?", default="."); p.add_argument("--task", required=True); p.add_argument("--skills-root"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("read-skill", help="Lê uma skill após sua seleção"); p.add_argument("name"); p.add_argument("--skills-root", required=True)
    p = sub.add_parser("read-skill-reference", help="Lê uma referência específica de uma skill"); p.add_argument("name"); p.add_argument("path"); p.add_argument("--skills-root", required=True)
    p = sub.add_parser("get-project-context", help="Monta contexto seletivo e lista skills para carregamento progressivo"); p.add_argument("project", nargs="?", default="."); p.add_argument("--task", default=""); p.add_argument("--skills-root"); p.add_argument("--max-files", type=int, default=20); p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "inspect":
            result = inspect(Path(args.project)); print_json(result) if args.json else print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
        if args.action == "packages":
            result = inspect(Path(args.project)); print_json({"root": result["root"], "is_monorepo": result["is_monorepo"], "packages": result["packages"]}); return 0
        if args.action == "skills-index":
            result = skill_index(Path(args.project), args.query); print_json(result); return 0
        if args.action == "find-skills":
            root = Path(args.project).resolve(); skills_root = resolve_skills_root(root, args.skills_root)
            result = relevant_skills(root, args.task, skills_root); print_json(result); return 0 if result["count"] or "warning" not in result else 2
        if args.action == "read-skill":
            print_json(read_skill(Path(args.skills_root).resolve(), args.name)); return 0
        if args.action == "read-skill-reference":
            print_json(read_skill_reference(Path(args.skills_root).resolve(), args.name, args.path)); return 0
        if args.action == "get-project-context":
            root = Path(args.project).resolve(); skills_root = resolve_skills_root(root, args.skills_root)
            result = project_context(root, args.task, skills_root, args.max_files); print_json(result); return 0
        if args.action == "validate-spec":
            result = validate_spec(Path(args.file)); print_json(result) if args.json else print("\n".join([f"Estado: {result['status']}"] + [f"ERRO: {e}" for e in result["errors"]] + [f"AVISO: {w}" for w in result["warnings"]])); return 0 if result["status"] == "passed" else 1
        root = Path(args.project).resolve()
        if args.action == "validate":
            if args.timeout < 1 or args.total_timeout < 1: raise ToolkitError("Timeouts precisam ser maiores que zero")
            report = validate_project(root, args.level, args.timeout, args.allow_project_scripts, args.package, args.affected, args.total_timeout)
            out = root / ".ai-toolkit" / "validation-report.json"; out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            out.with_suffix(".md").write_text(markdown_report(report), encoding="utf-8")
            if args.json: print_json(report)
            else: print(f"Validação: {report['summary']['status']} ({report['summary']['passed']} aprovadas, {report['summary']['failed']} reprovadas, {report['summary']['not_run']} não executadas, {report['summary']['skipped']} ignoradas, {report['summary']['error']} erros). Relatório: {out}")
            return {"passed": 0, "failed": 1, "error": 3, "partial": 4, "not_run": 4}[report["summary"]["status"]]
        if args.action == "validate-changes":
            entries = changed_entries(root); result = validate_change_scope(root, entries, args.scope, Path(args.spec).resolve() if args.spec else None, args.ignore_secret)
            if args.timeout < 1 or args.total_timeout < 1: raise ToolkitError("Timeouts precisam ser maiores que zero")
            result["validation"] = validate_project(root, args.level, args.timeout, args.allow_project_scripts, affected=True, total_timeout=args.total_timeout)
            if args.json: print_json(result)
            else:
                print(f"Arquivos inspecionados: {len(entries)}; achados: {len(result['findings'])}")
                for finding in result["findings"]: print(f"- [{finding['confidence']}] {finding['path']}: {finding['message']}")
            if result["status"] == "attention" or result["validation"]["summary"]["status"] in ("failed", "error"): return 1
            if result["validation"]["summary"]["status"] in ("partial", "not_run"): return 4
            return 0
        if args.action == "summarize":
            entries = changed_entries(root); validation_path = root / ".ai-toolkit" / "validation-report.json"
            validation = safe_json(validation_path) if validation_path.exists() else None
            change_report = validate_change_scope(root, entries, None, None)
            result = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "objective": args.objective, "summary": f"{len(entries)} arquivo(s) alterado(s); {len(change_report['findings'])} achado(s) de risco; validação {'disponível' if validation else 'não executada'}.", "files": entries, "validation": validation, "risks": change_report["findings"], "pending": ["Registrar decisões, limitações e pendências específicas da tarefa"], "evidence": ["Git status/diff lido localmente"], "next_actions": ["Executar validação aplicável e revisar os achados"]}
            output = (root / args.output).resolve()
            if not within(output, root): raise ToolkitError("Caminho de saída precisa ficar dentro do projeto")
            output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print_json(result) if args.json else print(f"Resumo salvo: {output}\n{result['summary']}")
            return 0
    except ToolkitError as exc:
        print(f"Erro de uso/configuração: {exc}", file=sys.stderr); return 2
    except KeyboardInterrupt:
        print("Interrompido pelo usuário", file=sys.stderr); return 130
    except Exception as exc:
        print(f"Erro interno do toolkit: {type(exc).__name__}: {exc}", file=sys.stderr); return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
