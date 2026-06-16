"""Helpers for the bundled ``project-starter`` plugin."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class TemplateSpec:
    key: str
    label: str
    summary: str
    stack: tuple[str, ...]
    directories: tuple[str, ...]
    bootstrap_commands: tuple[str, ...]
    milestones: tuple[tuple[str, tuple[str, ...]], ...]
    first_tasks: tuple[str, ...]
    success_metrics: tuple[str, ...]
    guardrails: tuple[str, ...]


@dataclass(frozen=True)
class ProjectBlueprint:
    name: str
    slug: str
    idea: str
    template_key: str
    template_label: str
    summary: str
    stack: tuple[str, ...]
    directories: tuple[str, ...]
    bootstrap_commands: tuple[str, ...]
    milestones: tuple[tuple[str, tuple[str, ...]], ...]
    first_tasks: tuple[str, ...]
    success_metrics: tuple[str, ...]
    guardrails: tuple[str, ...]
    workspace_root: str


class ProjectCommandError(RuntimeError):
    """Raised when `/project` input is invalid."""


class _ProjectArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - exercised indirectly
        raise ProjectCommandError(message)


_TEMPLATES: dict[str, TemplateSpec] = {
    "nextjs-saas": TemplateSpec(
        key="nextjs-saas",
        label="Next.js SaaS",
        summary="Best for multi-page products with auth, billing, dashboards, and growth loops.",
        stack=(
            "Next.js 15 + TypeScript",
            "Tailwind CSS + shadcn/ui",
            "Prisma + PostgreSQL",
            "Auth.js / session-based auth",
            "Stripe billing",
            "Vitest + Playwright",
        ),
        directories=("app", "components", "lib", "prisma", "tests/e2e", "tests/unit", "docs"),
        bootstrap_commands=(
            "npx create-next-app@latest . --ts --tailwind --app",
            "pnpm add @prisma/client prisma next-auth zod stripe",
            "pnpm add -D vitest @playwright/test",
        ),
        milestones=(
            ("Foundation", ("Initialize app shell", "Set up env vars", "Define DB schema and migrations")),
            ("Core product", ("Build auth flows", "Create dashboard shell", "Implement first user workflow")),
            ("Monetization", ("Add billing plans", "Gate premium features", "Instrument conversion funnel")),
            ("Ship", ("Add tests", "Polish onboarding", "Prepare deploy checklist")),
        ),
        first_tasks=(
            "Define the one-sentence customer outcome for v1.",
            "Choose the first dashboard workflow users must complete in under 5 minutes.",
            "Model users, organizations, and subscriptions in Prisma before building UI.",
        ),
        success_metrics=(
            "A new user can sign up and reach the core workflow in under 5 minutes.",
            "The first paid plan can be activated without manual ops work.",
            "Core happy-path flow is covered by one end-to-end test.",
        ),
        guardrails=(
            "Keep the v1 data model small and migration-friendly.",
            "Prefer server actions / route handlers over ad-hoc client state when possible.",
            "Do not build billing before the first repeatable user workflow exists.",
        ),
    ),
    "fastapi-service": TemplateSpec(
        key="fastapi-service",
        label="FastAPI Service",
        summary="Best for APIs, internal platforms, webhooks, jobs, and service integrations.",
        stack=(
            "Python 3.12",
            "FastAPI + Pydantic",
            "SQLAlchemy + Alembic",
            "PostgreSQL",
            "pytest + httpx",
            "Ruff + mypy",
        ),
        directories=("app/api", "app/core", "app/db", "app/models", "app/services", "tests", "docs"),
        bootstrap_commands=(
            "uv init --package .",
            "uv add fastapi uvicorn sqlalchemy alembic pydantic-settings psycopg[binary]",
            "uv add --dev pytest pytest-asyncio httpx ruff mypy",
        ),
        milestones=(
            ("Foundation", ("Create app package layout", "Configure settings", "Set up DB session + migrations")),
            ("API surface", ("Define request/response schemas", "Implement first endpoints", "Add auth or API key guard")),
            ("Reliability", ("Add tests for happy path + failure path", "Add logging and error handling", "Document contracts")),
            ("Ship", ("Create deploy config", "Add health checks", "Freeze v1 changelog")),
        ),
        first_tasks=(
            "Write the first three API contracts before coding handlers.",
            "Choose a clear error envelope and use it everywhere.",
            "Keep business logic in services, not directly in routes.",
        ),
        success_metrics=(
            "The main endpoint family is covered by integration tests.",
            "A new environment can boot from docs without tribal knowledge.",
            "The service exposes health, config, and migration status clearly.",
        ),
        guardrails=(
            "Do not couple route handlers directly to ORM models.",
            "Prefer explicit config via environment variables over hidden defaults.",
            "Treat webhooks and background jobs as first-class flows, not afterthoughts.",
        ),
    ),
    "ai-agent": TemplateSpec(
        key="ai-agent",
        label="AI Agent Backend",
        summary="Best for copilots, assistants, automation loops, tool-using agents, and retrieval-heavy products.",
        stack=(
            "Python 3.12",
            "FastAPI",
            "OpenAI / compatible SDK",
            "Pydantic models for prompts and tool contracts",
            "Background jobs / queues for long-running work",
            "pytest + synthetic eval fixtures",
        ),
        directories=("app/api", "app/agents", "app/prompts", "app/tools", "app/memory", "tests", "docs/evals"),
        bootstrap_commands=(
            "uv init --package .",
            "uv add fastapi uvicorn openai pydantic-settings tiktoken",
            "uv add --dev pytest pytest-asyncio ruff mypy",
        ),
        milestones=(
            ("Problem framing", ("Define user outcome", "Choose first agent loop", "Write tool contract inventory")),
            ("Agent core", ("Implement system prompts", "Add tool wrappers", "Create deterministic eval cases")),
            ("Productization", ("Persist runs and artifacts", "Add retries and guardrails", "Capture telemetry + costs")),
            ("Ship", ("Document failure modes", "Add operator playbook", "Gate rollout with eval thresholds")),
        ),
        first_tasks=(
            "Choose one narrow workflow the agent can complete end-to-end before adding breadth.",
            "Write tool schemas and expected outputs before wiring the model.",
            "Create 5-10 deterministic eval prompts that represent real user tasks.",
        ),
        success_metrics=(
            "The agent completes the first core workflow on representative evals.",
            "Each tool call has clear input/output logging for debugging.",
            "Fallback and escalation behavior is documented before launch.",
        ),
        guardrails=(
            "Keep prompts versioned and colocated with tests.",
            "Separate model orchestration from tool implementation.",
            "Never ship the agent without eval fixtures for its main tasks.",
        ),
    ),
    "python-cli": TemplateSpec(
        key="python-cli",
        label="Python CLI Tool",
        summary="Best for internal devtools, automation CLIs, wrappers, and local workflows.",
        stack=(
            "Python 3.12",
            "Typer or argparse",
            "Rich for UX",
            "Pydantic for config",
            "pytest",
            "Ruff",
        ),
        directories=("src", "tests", "docs", "scripts"),
        bootstrap_commands=(
            "uv init --package .",
            "uv add typer rich pydantic",
            "uv add --dev pytest ruff",
        ),
        milestones=(
            ("Foundation", ("Define main commands", "Set up config loading", "Create entrypoint")),
            ("Core workflows", ("Implement one useful command end-to-end", "Add helpful output", "Handle errors clearly")),
            ("Hardening", ("Add fixtures and tests", "Document common recipes", "Package install flow")),
            ("Ship", ("Polish help text", "Add examples", "Cut first release")),
        ),
        first_tasks=(
            "Write the top 3 command examples before implementing the parser.",
            "Decide what the CLI prints on success, warning, and failure.",
            "Design for composability: flags should be script-friendly.",
        ),
        success_metrics=(
            "A teammate can install and use the CLI from one quickstart doc.",
            "The primary command path is covered by tests.",
            "Output is readable both interactively and in CI logs.",
        ),
        guardrails=(
            "Keep command verbs short and predictable.",
            "Prefer structured config over ad-hoc environment branching.",
            "Do not hide destructive actions behind ambiguous flags.",
        ),
    ),
}

_TEMPLATE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ai-agent", ("agent", "assistant", "copilot", "rag", "llm", "ai ", "chatbot", "automation")),
    ("nextjs-saas", ("saas", "dashboard", "portal", "webapp", "landing", "tenant", "subscription")),
    ("fastapi-service", ("api", "backend", "service", "webhook", "integration", "worker")),
    ("python-cli", ("cli", "terminal", "developer tool", "devtool", "command line")),
)

_ROOT_MARKERS = (
    ".git",
    "package.json",
    "pnpm-workspace.yaml",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "uv.lock",
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "new-project"


def _derive_name(idea: str, explicit_name: str | None = None) -> str:
    if explicit_name and explicit_name.strip():
        return explicit_name.strip()

    cleaned = re.sub(r"\s+", " ", idea).strip(" .")
    if not cleaned:
        return "New Project"

    lower = cleaned.lower()
    for splitter in (" for ", " para ", " that ", " con ", " with "):
        if splitter in lower:
            cleaned = cleaned[: lower.index(splitter)].strip(" .,:;-")
            break

    words = re.findall(r"[A-Za-z0-9]+", cleaned)
    if not words:
        return "New Project"
    return " ".join(word.capitalize() for word in words[:4])


def _find_workspace_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    candidates = [current, *current.parents]
    for candidate in candidates:
        for marker in _ROOT_MARKERS:
            if (candidate / marker).exists():
                return candidate
    return current


def _infer_template(idea: str, explicit_template: str | None = None) -> TemplateSpec:
    if explicit_template:
        key = explicit_template.strip().lower()
        if key not in _TEMPLATES:
            raise ProjectCommandError(
                f"Unknown template '{explicit_template}'. Use `templates` to list valid options."
            )
        return _TEMPLATES[key]

    lowered = f" {idea.lower()} "
    for template_key, keywords in _TEMPLATE_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return _TEMPLATES[template_key]
    return _TEMPLATES["nextjs-saas"]


def build_project_blueprint(
    idea: str,
    *,
    name: str | None = None,
    template: str | None = None,
    workspace_root: Path | None = None,
) -> ProjectBlueprint:
    trimmed_idea = idea.strip()
    if not trimmed_idea:
        raise ProjectCommandError("Please provide an idea, e.g. `/project init AI CRM for clinics`.")

    template_spec = _infer_template(trimmed_idea, explicit_template=template)
    project_name = _derive_name(trimmed_idea, explicit_name=name)
    slug = _slugify(project_name)
    root = _find_workspace_root(workspace_root)
    summary = f"Build {project_name} as a {template_spec.label.lower()} for: {trimmed_idea}."

    return ProjectBlueprint(
        name=project_name,
        slug=slug,
        idea=trimmed_idea,
        template_key=template_spec.key,
        template_label=template_spec.label,
        summary=summary,
        stack=template_spec.stack,
        directories=template_spec.directories,
        bootstrap_commands=template_spec.bootstrap_commands,
        milestones=template_spec.milestones,
        first_tasks=template_spec.first_tasks,
        success_metrics=template_spec.success_metrics,
        guardrails=template_spec.guardrails,
        workspace_root=str(root),
    )


def _render_project_md(blueprint: ProjectBlueprint) -> str:
    pages = _suggest_pages(blueprint)
    features = _suggest_features(blueprint)
    lines = [
        f"# {blueprint.name}",
        "",
        "## Brief",
        f"- Idea: {blueprint.idea}",
        f"- Recommended template: {blueprint.template_label} (`{blueprint.template_key}`)",
        f"- Working summary: {blueprint.summary}",
        "",
        "## V1 Outcome",
        "- Deliver one end-to-end workflow that proves the product's value quickly.",
        "- Keep the initial scope narrow enough to ship in days, not weeks.",
        "",
        "## Target Users",
        "- Primary user: define the first buyer/operator who feels the pain most often.",
        "- Secondary user: define who reviews output, configures the system, or pays for it.",
        "",
        "## Core Product Features",
    ]
    lines.extend(f"- {feature}" for feature in features)
    lines.extend([
        "",
        "## Core Screens / Surfaces",
    ])
    lines.extend(f"- {page}" for page in pages)
    lines.extend([
        "",
        "## Suggested Success Metrics",
    ])
    lines.extend(f"- {metric}" for metric in blueprint.success_metrics)
    lines.extend([
        "",
        "## First Product Questions",
        "- What is the one job this product must complete better than the manual alternative?",
        "- What should a new user accomplish in the first 5 minutes?",
        "- What can wait until v2 without hurting validation?",
    ])
    return "\n".join(lines) + "\n"


def _render_architecture_md(blueprint: ProjectBlueprint) -> str:
    entities = _suggest_entities(blueprint)
    lines = [
        f"# {blueprint.name} Architecture",
        "",
        "## Recommended Stack",
    ]
    lines.extend(f"- {item}" for item in blueprint.stack)
    lines.extend([
        "",
        "## Starter Directories",
    ])
    lines.extend(f"- `{directory}`" for directory in blueprint.directories)
    lines.extend([
        "",
        "## Bootstrap Commands",
    ])
    lines.extend(f"- `{command}`" for command in blueprint.bootstrap_commands)
    lines.extend([
        "",
        "## Core Data / Domain Entities",
    ])
    lines.extend(f"- {entity}" for entity in entities)
    lines.extend([
        "",
        "## Guardrails",
    ])
    lines.extend(f"- {item}" for item in blueprint.guardrails)
    lines.extend([
        "",
        "## Initial Technical Shape",
        "- Keep core business logic separate from adapters (HTTP, CLI, UI, jobs).",
        "- Add one smoke test for the main user path before expanding features.",
        "- Record env vars, external services, and seed data assumptions early.",
    ])
    return "\n".join(lines) + "\n"


def _render_tasks_md(blueprint: ProjectBlueprint) -> str:
    lines = [f"# {blueprint.name} Task Plan", ""]
    lines.append("## First Tasks")
    lines.extend(f"- [ ] {task}" for task in blueprint.first_tasks)
    for title, tasks in blueprint.milestones:
        lines.extend(["", f"## {title}"])
        lines.extend(f"- [ ] {task}" for task in tasks)
    lines.extend([
        "",
        "## Review Cadence",
        "- [ ] Re-evaluate scope after the first usable workflow exists.",
        "- [ ] Convert unclear tasks into concrete acceptance criteria before implementation.",
    ])
    return "\n".join(lines) + "\n"


def _render_agents_md(blueprint: ProjectBlueprint) -> str:
    builder_outputs = _builder_output_names()
    lines = [
        f"# {blueprint.name} Agent Guide",
        "",
        "## Mission",
        f"- {blueprint.summary}",
        "",
        "## Working Mode",
        f"- Preferred starter template: `{blueprint.template_key}`",
        "- Optimize for shipping a narrow, demonstrable v1 quickly.",
        "- Keep changes small, reversible, and documented.",
        "",
        "## Key Directories",
    ]
    lines.extend(f"- `{directory}` — planned project area" for directory in blueprint.directories)
    lines.extend([
        "",
        "## Delivery Priorities",
    ])
    lines.extend(f"- {task}" for task in blueprint.first_tasks)
    lines.extend([
        "",
        "## Builder Handoff Artifacts",
    ])
    lines.extend(f"- `{name}`" for name in builder_outputs)
    lines.extend([
        "",
        "## Quality Bar",
        "- Add tests for the main happy path before widening scope.",
        "- Document assumptions in `PROJECT.md` or `ARCHITECTURE.md` when they change.",
        "- Prefer explicit interfaces and typed data contracts over hidden magic.",
    ])
    return "\n".join(lines) + "\n"


def _primary_user(blueprint: ProjectBlueprint) -> str:
    if blueprint.template_key == "ai-agent":
        return "Operator or knowledge worker who wants AI to complete a repetitive workflow with oversight."
    if blueprint.template_key == "fastapi-service":
        return "Developer or integration owner who needs a reliable API/service to automate a business process."
    if blueprint.template_key == "python-cli":
        return "Developer or internal operator who wants a repeatable command-line workflow."
    return "Business user who needs a fast, polished product workflow in the browser."


def _secondary_user(blueprint: ProjectBlueprint) -> str:
    if blueprint.template_key == "ai-agent":
        return "Team lead or admin who configures tools, reviews outputs, and monitors safety/cost."
    if blueprint.template_key == "fastapi-service":
        return "Platform owner who manages environments, auth, logs, and deployment health."
    if blueprint.template_key == "python-cli":
        return "Tech lead who reviews adoption, onboarding, and maintainability."
    return "Admin, founder, or ops owner who configures the product and monitors usage."


def _suggest_features(blueprint: ProjectBlueprint) -> tuple[str, ...]:
    common = (
        "A clear first-run onboarding path that gets the user to value quickly.",
        "A single primary workflow optimized for speed and clarity.",
        "Simple admin/configuration controls for the operator or owner.",
    )
    by_template = {
        "nextjs-saas": (
            "Authentication and role-aware dashboard access.",
            "Subscription-aware product gating and account settings.",
            "Operational dashboard with the main workflow front and center.",
        ),
        "fastapi-service": (
            "Health, auth, and error-handled API endpoints for the main workflow.",
            "Structured logging and status visibility for operators.",
            "Admin-facing configuration for integrations, secrets, and retry behavior.",
        ),
        "ai-agent": (
            "A guided workflow where the AI performs one narrow, high-value job well.",
            "Human review / approval point before high-impact actions.",
            "Run history with prompts, outputs, and tool traces for debugging.",
        ),
        "python-cli": (
            "One high-value command path optimized for repeat daily use.",
            "Readable terminal output with clear success/error states.",
            "Config and presets that reduce repeated manual input.",
        ),
    }
    return by_template.get(blueprint.template_key, common) + common


def _suggest_pages(blueprint: ProjectBlueprint) -> tuple[str, ...]:
    by_template = {
        "nextjs-saas": (
            "Marketing / landing page",
            "Sign in / sign up",
            "Main dashboard",
            "Primary workflow page",
            "Account / billing settings",
            "Admin or team settings",
        ),
        "fastapi-service": (
            "API docs / developer portal",
            "Health / status surface",
            "Admin settings for integrations and credentials",
            "Run logs / job history",
        ),
        "ai-agent": (
            "Chat or task input surface",
            "Run details / output review",
            "Tool / knowledge configuration",
            "History / saved runs",
            "Admin guardrails and settings",
        ),
        "python-cli": (
            "CLI entrypoint and help output",
            "Config / profile setup flow",
            "Logs or report output surface",
        ),
    }
    return by_template.get(blueprint.template_key, ("Main workflow surface", "Settings", "History"))


def _suggest_entities(blueprint: ProjectBlueprint) -> tuple[str, ...]:
    by_template = {
        "nextjs-saas": (
            "User",
            "Workspace / Organization",
            "Subscription / Plan",
            "Primary domain record for the core workflow",
            "Activity / Audit log",
        ),
        "fastapi-service": (
            "Account / API consumer",
            "Integration / Credential",
            "Job / Event / Request record",
            "Retry / Delivery status",
            "Audit log",
        ),
        "ai-agent": (
            "User / Operator",
            "Agent run",
            "Prompt / configuration profile",
            "Tool execution record",
            "Approval / feedback event",
        ),
        "python-cli": (
            "Config profile",
            "Run / command invocation",
            "Primary workflow artifact",
            "Output summary / report",
        ),
    }
    return by_template.get(blueprint.template_key, ("User", "Primary record", "Settings"))


def _ui_style_direction(blueprint: ProjectBlueprint) -> tuple[str, ...]:
    if blueprint.template_key == "ai-agent":
        return (
            "Modern, calm, high-signal interface with strong hierarchy and minimal clutter.",
            "Chat/task surfaces should feel operational, not gimmicky.",
            "Use cards, side panels, and run-status badges to make AI activity legible.",
        )
    if blueprint.template_key == "fastapi-service":
        return (
            "Developer-friendly UI with clean tables, logs, and status indicators.",
            "Prioritize readability and operational trust over flashy visuals.",
            "Make errors, health, and configuration discoverable in one glance.",
        )
    if blueprint.template_key == "python-cli":
        return (
            "CLI UX should be concise, readable, and automation-friendly.",
            "Prefer explicit command names and predictable output formatting.",
            "Any companion docs should use short examples and copy-paste commands.",
        )
    return (
        "Polished SaaS aesthetic with strong contrast, generous spacing, and responsive layouts.",
        "Keep the first-run experience friendly and momentum-building.",
        "Prioritize one obvious primary CTA per screen.",
    )


def _builder_non_goals(blueprint: ProjectBlueprint) -> tuple[str, ...]:
    return (
        "Do not build every possible feature for v1.",
        "Do not introduce heavy admin complexity before the main workflow is smooth.",
        "Do not optimize for edge cases until the core path is usable end-to-end.",
        f"Do not drift away from the selected starter template (`{blueprint.template_key}`) without a clear reason.",
    )


def _acceptance_criteria(blueprint: ProjectBlueprint) -> tuple[str, ...]:
    first_page = _suggest_pages(blueprint)[0]
    return (
        "A new user can understand the product from the first screen without extra explanation.",
        f"The core flow from `{first_page}` to the main outcome is obvious and testable.",
        "The generated UI contains realistic placeholders, states, and empty-state guidance.",
        "The first v1 workflow can be demoed without hand-waving key missing pieces.",
    )


def _builder_output_names() -> tuple[str, ...]:
    return ("BUILD_BRIEF.md", "V0_PROMPT.md", "CODEX_PROMPT.md")


def _render_build_brief_md(blueprint: ProjectBlueprint) -> str:
    pages = _suggest_pages(blueprint)
    features = _suggest_features(blueprint)
    entities = _suggest_entities(blueprint)
    style = _ui_style_direction(blueprint)
    non_goals = _builder_non_goals(blueprint)
    acceptance = _acceptance_criteria(blueprint)

    lines = [
        f"# {blueprint.name} Builder Brief",
        "",
        "## Product Goal",
        f"- {blueprint.idea}",
        f"- {blueprint.summary}",
        "",
        "## Users",
        f"- Primary: {_primary_user(blueprint)}",
        f"- Secondary: {_secondary_user(blueprint)}",
        "",
        "## Must-Have Features",
    ]
    lines.extend(f"- {feature}" for feature in features)
    lines.extend([
        "",
        "## Pages / Screens",
    ])
    lines.extend(f"- {page}" for page in pages)
    lines.extend([
        "",
        "## Core Entities",
    ])
    lines.extend(f"- {entity}" for entity in entities)
    lines.extend([
        "",
        "## UX / Visual Direction",
    ])
    lines.extend(f"- {item}" for item in style)
    lines.extend([
        "",
        "## Non-Goals",
    ])
    lines.extend(f"- {item}" for item in non_goals)
    lines.extend([
        "",
        "## Acceptance Criteria",
    ])
    lines.extend(f"- {item}" for item in acceptance)
    lines.extend([
        "",
        "## Suggested Stack",
    ])
    lines.extend(f"- {item}" for item in blueprint.stack)
    return "\n".join(lines) + "\n"


def _render_builder_prompt(blueprint: ProjectBlueprint, *, target: str) -> str:
    pages = _suggest_pages(blueprint)
    features = _suggest_features(blueprint)
    entities = _suggest_entities(blueprint)
    style = _ui_style_direction(blueprint)
    acceptance = _acceptance_criteria(blueprint)
    non_goals = _builder_non_goals(blueprint)

    intro = (
        f"Create a production-style v1 for `{blueprint.name}` using a `{blueprint.template_label}` approach."
        if target == "v0"
        else f"Build `{blueprint.name}` as a real repo-ready v1 with clean structure, sensible defaults, and an implementable first workflow."
    )

    lines = [
        f"# {'V0' if target == 'v0' else 'Codex'} Prompt for {blueprint.name}",
        "",
        intro,
        "",
        "## Product Context",
        f"- Idea: {blueprint.idea}",
        f"- Goal: {blueprint.summary}",
        f"- Primary user: {_primary_user(blueprint)}",
        f"- Secondary user: {_secondary_user(blueprint)}",
        "",
        "## Build This",
    ]
    lines.extend(f"- {feature}" for feature in features)
    lines.extend([
        "",
        "## Required Screens",
    ])
    lines.extend(f"- {page}" for page in pages)
    lines.extend([
        "",
        "## Core Data / Objects",
    ])
    lines.extend(f"- {entity}" for entity in entities)
    lines.extend([
        "",
        "## UX / Visual Direction",
    ])
    lines.extend(f"- {item}" for item in style)
    lines.extend([
        "",
        "## Constraints",
        f"- Stay close to this stack direction: {', '.join(blueprint.stack[:4])}.",
        "- Optimize for a convincing first demo and a coherent information architecture.",
        "- Make the primary CTA and first-run path extremely obvious.",
        "",
        "## Non-Goals",
    ])
    lines.extend(f"- {item}" for item in non_goals)
    if target == "codex":
        lines.extend([
            "",
            "## Implementation Requirements",
            "- Create the actual project structure and scaffold the main files, not just a mockup.",
            "- Favor a minimal but working vertical slice for the first workflow.",
            "- Add clear TODO boundaries only where deeper implementation is intentionally deferred.",
            "- Include at least one validation path (test, smoke check, or runnable verification) for the main flow.",
        ])
    lines.extend([
        "",
        "## Acceptance Criteria",
    ])
    lines.extend(f"- {item}" for item in acceptance)
    lines.extend([
        "",
        "## Output Expectations",
        "- Include realistic empty states, loading states, and success states.",
        "- Use sensible sample data / placeholder content to make the interface feel real.",
        "- Keep the scope focused on one shippable v1 workflow.",
    ])
    return "\n".join(lines) + "\n"


def _metadata_payload(blueprint: ProjectBlueprint) -> dict:
    payload = asdict(blueprint)
    payload["stack"] = list(blueprint.stack)
    payload["directories"] = list(blueprint.directories)
    payload["bootstrap_commands"] = list(blueprint.bootstrap_commands)
    payload["success_metrics"] = list(blueprint.success_metrics)
    payload["guardrails"] = list(blueprint.guardrails)
    payload["first_tasks"] = list(blueprint.first_tasks)
    payload["milestones"] = [
        {"title": title, "tasks": list(tasks)} for title, tasks in blueprint.milestones
    ]
    return payload


def _target_files(output_dir: Path) -> dict[str, str]:
    return {
        "AGENTS.md": "AGENTS.md",
        "PROJECT.md": "PROJECT.md",
        "ARCHITECTURE.md": "ARCHITECTURE.md",
        "TASKS.md": "TASKS.md",
        "BUILD_BRIEF.md": "BUILD_BRIEF.md",
        "V0_PROMPT.md": "V0_PROMPT.md",
        "CODEX_PROMPT.md": "CODEX_PROMPT.md",
        "metadata": str(Path(".hermes") / "project-starter.json"),
    }


def _write_blueprint(
    blueprint: ProjectBlueprint,
    *,
    output_dir: Path,
    force: bool = False,
) -> list[Path]:
    targets = _target_files(output_dir)
    paths = {
        name: output_dir / relative_path
        for name, relative_path in targets.items()
    }

    conflicts = [
        path for path in paths.values()
        if path.exists() and not force
    ]
    if conflicts:
        joined = ", ".join(str(path.relative_to(output_dir)) for path in conflicts)
        raise ProjectCommandError(
            f"Refusing to overwrite existing files without --force: {joined}"
        )

    for directory in blueprint.directories:
        (output_dir / directory).mkdir(parents=True, exist_ok=True)

    paths["metadata"].parent.mkdir(parents=True, exist_ok=True)

    paths["AGENTS.md"].write_text(_render_agents_md(blueprint), encoding="utf-8")
    paths["PROJECT.md"].write_text(_render_project_md(blueprint), encoding="utf-8")
    paths["ARCHITECTURE.md"].write_text(_render_architecture_md(blueprint), encoding="utf-8")
    paths["TASKS.md"].write_text(_render_tasks_md(blueprint), encoding="utf-8")
    paths["BUILD_BRIEF.md"].write_text(_render_build_brief_md(blueprint), encoding="utf-8")
    paths["V0_PROMPT.md"].write_text(_render_builder_prompt(blueprint, target="v0"), encoding="utf-8")
    paths["CODEX_PROMPT.md"].write_text(_render_builder_prompt(blueprint, target="codex"), encoding="utf-8")
    paths["metadata"].write_text(
        json.dumps(_metadata_payload(blueprint), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return [
        paths["AGENTS.md"],
        paths["PROJECT.md"],
        paths["ARCHITECTURE.md"],
        paths["TASKS.md"],
        paths["BUILD_BRIEF.md"],
        paths["V0_PROMPT.md"],
        paths["CODEX_PROMPT.md"],
        paths["metadata"],
    ]


def _format_templates() -> str:
    lines = ["Available project templates:"]
    for spec in _TEMPLATES.values():
        lines.append(f"- `{spec.key}` — {spec.summary}")
    return "\n".join(lines)


def _format_blueprint_preview(blueprint: ProjectBlueprint, output_dir: Path, *, dry_run: bool) -> str:
    lines = [
        "[project-starter] " + ("Dry run for" if dry_run else "Created blueprint for") + f" {blueprint.name}",
        f"Workspace: {output_dir}",
        f"Template: {blueprint.template_label} (`{blueprint.template_key}`)",
        f"Summary: {blueprint.summary}",
        "",
        "Files:",
        "- `AGENTS.md`",
        "- `PROJECT.md`",
        "- `ARCHITECTURE.md`",
        "- `TASKS.md`",
        "- `BUILD_BRIEF.md`",
        "- `V0_PROMPT.md`",
        "- `CODEX_PROMPT.md`",
        "- `.hermes/project-starter.json`",
        "",
        "Starter directories:",
    ]
    lines.extend(f"- `{directory}`" for directory in blueprint.directories)
    lines.extend([
        "",
        "Bootstrap commands:",
    ])
    lines.extend(f"- `{command}`" for command in blueprint.bootstrap_commands)
    lines.extend([
        "",
        "Next steps:",
        "- Paste `V0_PROMPT.md` into v0 for UI generation.",
        "- Use `CODEX_PROMPT.md` when you want Codex to scaffold and implement the repo.",
        "- Review `BUILD_BRIEF.md` and tighten the v1 scope before generating code.",
        "- Review `TASKS.md` and turn the first phase into tickets or Kanban cards.",
        "- Use `AGENTS.md` as the working contract for future coding sessions.",
    ])
    return "\n".join(lines)


def _resolve_output_dir(raw_value: str | None) -> Path:
    if raw_value:
        return Path(raw_value).expanduser().resolve()
    return _find_workspace_root()


def _coerce_text(value: str | Sequence[str] | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return " ".join(value).strip() or None


def _run_init(args: argparse.Namespace) -> tuple[int, str]:
    idea = " ".join(args.idea).strip()
    output_dir = _resolve_output_dir(getattr(args, "output_dir", None))
    blueprint = build_project_blueprint(
        idea,
        name=_coerce_text(getattr(args, "name", None)),
        template=getattr(args, "template", None),
        workspace_root=output_dir,
    )
    if getattr(args, "dry_run", False):
        return 0, _format_blueprint_preview(blueprint, output_dir, dry_run=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_blueprint(blueprint, output_dir=output_dir, force=bool(getattr(args, "force", False)))
    return 0, _format_blueprint_preview(blueprint, output_dir, dry_run=False)


def _run_templates(_args: argparse.Namespace) -> tuple[int, str]:
    return 0, _format_templates()


def _build_parser(parser_cls: type[argparse.ArgumentParser] = argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser = parser_cls(
        prog="project",
        description="Bootstrap project blueprints and execution plans quickly.",
    )
    subs = parser.add_subparsers(dest="project_command")

    init_p = subs.add_parser("init", help="Generate project docs and starter structure")
    init_p.add_argument("idea", nargs="+", help="Natural-language project idea")
    init_p.add_argument("--template", choices=tuple(_TEMPLATES.keys()), help="Force a specific starter template")
    init_p.add_argument("--name", nargs="+", help="Override the generated project name")
    init_p.add_argument("--output-dir", help="Directory where files should be written (defaults to workspace root)")
    init_p.add_argument("--dry-run", action="store_true", help="Show the generated plan without writing files")
    init_p.add_argument("--force", action="store_true", help="Overwrite existing blueprint files")
    init_p.set_defaults(_runner=_run_init)

    templates_p = subs.add_parser("templates", help="List available project templates")
    templates_p.set_defaults(_runner=_run_templates)
    return parser


def _dispatch_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> tuple[int, str]:
    runner = getattr(args, "_runner", None)
    if runner is None:
        return 0, parser.format_help().rstrip()
    return runner(args)


def handle_project_slash(raw_args: str) -> str:
    argv = shlex.split(raw_args or "")
    parser = _build_parser(_ProjectArgumentParser)
    try:
        args = parser.parse_args(argv)
        _code, text = _dispatch_args(args, parser)
        return text
    except ProjectCommandError as exc:
        if str(exc):
            return f"{exc}\n\n{parser.format_help().rstrip()}"
        return parser.format_help().rstrip()


def register_cli(subparser: argparse.ArgumentParser) -> None:
    subparser.description = "Bootstrap project blueprints and execution plans quickly."
    subs = subparser.add_subparsers(dest="project_command")

    init_p = subs.add_parser("init", help="Generate project docs and starter structure")
    init_p.add_argument("idea", nargs="+", help="Natural-language project idea")
    init_p.add_argument("--template", choices=tuple(_TEMPLATES.keys()), help="Force a specific starter template")
    init_p.add_argument("--name", nargs="+", help="Override the generated project name")
    init_p.add_argument("--output-dir", help="Directory where files should be written (defaults to workspace root)")
    init_p.add_argument("--dry-run", action="store_true", help="Show the generated plan without writing files")
    init_p.add_argument("--force", action="store_true", help="Overwrite existing blueprint files")

    subs.add_parser("templates", help="List available project templates")
    subparser.set_defaults(func=project_command)


def project_command(args: argparse.Namespace) -> int:
    parser = _build_parser()
    try:
        code, text = _dispatch_args(args, parser)
    except ProjectCommandError as exc:
        print(f"{exc}\n")
        print(parser.format_help().rstrip())
        return 2
    if text:
        print(text)
    return code
