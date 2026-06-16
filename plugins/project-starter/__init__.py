"""Bundled project-starter plugin."""

from .project_starter import handle_project_slash, project_command, register_cli


def register(ctx) -> None:
    ctx.register_command(
        "project",
        handler=handle_project_slash,
        description="Turn an idea into a project blueprint and execution plan.",
        args_hint="init <idea>",
    )
    ctx.register_cli_command(
        name="project",
        help="Bootstrap project blueprints and execution plans",
        setup_fn=register_cli,
        handler_fn=project_command,
        description=(
            "Generate AGENTS.md, project docs, architecture notes, and a "
            "phase-based task list from a single idea."
        ),
    )
