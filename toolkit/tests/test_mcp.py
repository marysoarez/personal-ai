"""Protocol-level MCP tests use the official Python SDK when installed."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest

try:
    from mcp import Client, StdioServerParameters
except ImportError:
    Client = None
    StdioServerParameters = None

ROOT = Path(__file__).parents[2].resolve()
SERVER = ROOT / "toolkit" / "mcp_server.py"


def result_data(result):
    if result.structured_content is not None:
        return result.structured_content
    blocks = [item.text for item in result.content if hasattr(item, "text")]
    return json.loads("\n".join(blocks))


@unittest.skipUnless(Client is not None, "Install optional toolkit/requirements-mcp.txt")
class McpProtocolTests(unittest.TestCase):
    def test_stdio_discovery_calls_and_path_restriction(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as outside:
                root = Path(allowed)
                (root / "package.json").write_text('{"name":"fixture","scripts":{"test":"node -e process.exit(1)"}}', encoding="utf-8")
                params = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--allow-root", str(root), "--allow-root", str(ROOT)], cwd=str(ROOT))
                async with Client(params, read_timeout_seconds=10) as client:
                    tools = await client.list_tools()
                    names = {item.name for item in tools.tools}
                    self.assertEqual({"list_skills", "find_relevant_skills", "read_skill", "read_skill_reference", "get_project_context", "inspect_project", "validate_project", "validate_spec", "review_changes", "summarize_validation", "get_toolkit_capabilities"}, names)
                    result = await client.call_tool("inspect_project", {"directory": str(root)})
                    self.assertFalse(result.is_error)
                    data = result_data(result)
                    self.assertIn("node", data["stack"])
                    skills = await client.call_tool("list_skills", {"directory": str(root), "skills_directory": str(ROOT / "skills")})
                    self.assertFalse(skills.is_error)
                    self.assertEqual(17, result_data(skills)["count"])
                    selected = await client.call_tool("find_relevant_skills", {"directory": str(root), "task": "review a Node API for security", "skills_directory": str(ROOT / "skills")})
                    self.assertFalse(selected.is_error)
                    self.assertIn("node-architecture", {skill["name"] for skill in result_data(selected)["skills"]})
                    read = await client.call_tool("read_skill", {"directory": str(root), "name": "lgpd", "skills_directory": str(ROOT / "skills")})
                    self.assertFalse(read.is_error)
                    self.assertIn("LGPD", result_data(read)["content"])
                    reference = await client.call_tool("read_skill_reference", {"directory": str(root), "name": "lgpd", "reference_path": "references/official-sources.md", "skills_directory": str(ROOT / "skills")})
                    self.assertFalse(reference.is_error)
                    traversal = await client.call_tool("read_skill_reference", {"directory": str(root), "name": "lgpd", "reference_path": "../../README.md", "skills_directory": str(ROOT / "skills")})
                    self.assertTrue(traversal.is_error)
                    context = await client.call_tool("get_project_context", {"directory": str(root), "task": "implement Node feature", "skills_directory": str(ROOT / "skills")})
                    self.assertFalse(context.is_error)
                    validation = await client.call_tool("validate_project", {"directory": str(root), "level": "standard"})
                    self.assertFalse(validation.is_error)
                    # package.json scripts are not run by MCP; absent opt-in is explicit.
                    statuses = {check["status"] for check in result_data(validation)["checks"]}
                    self.assertIn("not_run", statuses)
                    denied = await client.call_tool("inspect_project", {"directory": str(Path(outside))})
                    self.assertTrue(denied.is_error)
                    bad_level = await client.call_tool("validate_project", {"directory": str(root), "level": "danger"})
                    self.assertTrue(bad_level.is_error)
                    caps = await client.call_tool("get_toolkit_capabilities", {})
                    self.assertFalse(caps.is_error)
                    self.assertFalse(result_data(caps)["runs_package_scripts"])
        asyncio.run(exercise())

    def test_spec_tool_accepts_text_and_bounds_input(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as allowed:
                params = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--allow-root", allowed], cwd=str(ROOT))
                async with Client(params, read_timeout_seconds=10) as client:
                    result = await client.call_tool("validate_spec", {"specification": "# SPEC\n## Problema\n"})
                    self.assertFalse(result.is_error)
                    self.assertEqual("failed", result_data(result)["status"])
                    too_big = await client.call_tool("validate_spec", {"specification": "x" * 100_001})
                    self.assertTrue(too_big.is_error)
        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
