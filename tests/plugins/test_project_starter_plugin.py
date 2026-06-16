"""Tests for the bundled project-starter plugin."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml


@pytest.fixture(autouse=True)
def _isolated_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    hermes_home = tmp_path / ".hermes-home"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    yield workspace, hermes_home


def _load_lib():
    repo_root = Path(__file__).resolve().parents[2]
    lib_path = repo_root / "plugins" / "project-starter" / "project_starter.py"
    spec = importlib.util.spec_from_file_location(
        "project_starter_under_test",
        lib_path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["project_starter_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_plugin_init():
    repo_root = Path(__file__).resolve().parents[2]
    plugin_dir = repo_root / "plugins" / "project-starter"
    spec = importlib.util.spec_from_file_location(
        "hermes_plugins.project_starter",
        plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)],
    )
    import types
    if "hermes_plugins" not in sys.modules:
        ns = types.ModuleType("hermes_plugins")
        ns.__path__ = []
        sys.modules["hermes_plugins"] = ns
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "hermes_plugins.project_starter"
    mod.__path__ = [str(plugin_dir)]
    sys.modules["hermes_plugins.project_starter"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestTemplateInference:
    def test_infers_ai_agent_template(self):
        mod = _load_lib()
        blueprint = mod.build_project_blueprint("AI agent for SDR outbound research")
        assert blueprint.template_key == "ai-agent"

    def test_infers_fastapi_service_template(self):
        mod = _load_lib()
        blueprint = mod.build_project_blueprint("Webhook API service for ecommerce returns")
        assert blueprint.template_key == "fastapi-service"


class TestSlashCommand:
    def test_templates_lists_available_options(self):
        mod = _load_lib()
        text = mod.handle_project_slash("templates")
        assert "nextjs-saas" in text
        assert "ai-agent" in text

    def test_init_dry_run_does_not_write_files(self, _isolated_workspace):
        workspace, _ = _isolated_workspace
        mod = _load_lib()

        text = mod.handle_project_slash(
            'init "AI support copilot for ecommerce stores" --dry-run'
        )

        assert "Dry run" in text
        assert "AGENTS.md" in text
        assert "V0_PROMPT.md" in text
        assert "CODEX_PROMPT.md" in text
        assert not (workspace / "AGENTS.md").exists()
        assert not (workspace / ".hermes" / "project-starter.json").exists()

    def test_init_writes_blueprint_files(self, _isolated_workspace):
        workspace, _ = _isolated_workspace
        mod = _load_lib()

        text = mod.handle_project_slash(
            'init "AI support copilot for ecommerce stores" --name Support Pilot'
        )

        assert "Created blueprint" in text
        assert (workspace / "AGENTS.md").exists()
        assert (workspace / "PROJECT.md").exists()
        assert (workspace / "ARCHITECTURE.md").exists()
        assert (workspace / "TASKS.md").exists()
        assert (workspace / "BUILD_BRIEF.md").exists()
        assert (workspace / "V0_PROMPT.md").exists()
        assert (workspace / "CODEX_PROMPT.md").exists()
        metadata = json.loads((workspace / ".hermes" / "project-starter.json").read_text(encoding="utf-8"))
        assert metadata["name"] == "Support Pilot"
        assert metadata["template_key"] == "ai-agent"
        assert "Required Screens" in (workspace / "V0_PROMPT.md").read_text(encoding="utf-8")
        assert "Must-Have Features" in (workspace / "BUILD_BRIEF.md").read_text(encoding="utf-8")
        assert "Implementation Requirements" in (workspace / "CODEX_PROMPT.md").read_text(encoding="utf-8")

    def test_init_requires_force_to_overwrite(self, _isolated_workspace):
        workspace, _ = _isolated_workspace
        mod = _load_lib()
        (workspace / "PROJECT.md").write_text("existing\n", encoding="utf-8")

        text = mod.handle_project_slash('init "Internal ops dashboard"')

        assert "Refusing to overwrite existing files" in text


class TestBundledPluginDiscovery:
    def test_bundled_plugin_registers_slash_and_cli(self, _isolated_workspace, monkeypatch):
        _workspace, hermes_home = _isolated_workspace
        cfg_path = hermes_home / "config.yaml"
        cfg_path.write_text(
            yaml.safe_dump({"plugins": {"enabled": ["project-starter"]}}),
            encoding="utf-8",
        )

        from hermes_cli.plugins import PluginManager

        _load_plugin_init()
        mgr = PluginManager()
        mgr.discover_and_load()

        assert "project-starter" in mgr._plugins
        assert "project" in mgr._plugin_commands
        assert "project" in mgr._cli_commands
