# project-starter

Bundled Hermes plugin for turning a rough idea into a structured project
blueprint quickly.

## What it adds

- `/project templates` — list recommended starter templates
- `/project init <idea>` — generate:
  - `AGENTS.md`
  - `PROJECT.md`
  - `ARCHITECTURE.md`
  - `TASKS.md`
  - `BUILD_BRIEF.md`
  - `V0_PROMPT.md`
  - `CODEX_PROMPT.md`
  - `.hermes/project-starter.json`

The goal is to produce output that feels close to a handoff you could paste
into `v0`, plus a companion prompt you can hand to `Codex` for real repo
implementation work.

## CLI

After enabling the plugin, the same flow is available as:

```bash
hermes project templates
hermes project init "AI support copilot for ecommerce stores"
```

## Enable

Bundled standalone plugins are opt-in. Add this to `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - project-starter
```
