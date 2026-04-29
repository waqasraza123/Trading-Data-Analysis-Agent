# Agent Instructions

This file is the durable entry point for future Codex sessions in this repository. Keep it small, stable, and useful.

Before making implementation decisions:

1. Read `docs/project-state.md`.
2. Read `docs/_local/current-session.md` if it exists.
3. Treat `docs/project-state.md` as durable repo memory.
4. Treat `docs/_local/current-session.md` as local working memory.

Memory rules:

- Update `docs/project-state.md` only when long-term architecture, roadmap, constraints, or important decisions change.
- Update `docs/_local/current-session.md` at the end of every meaningful task.
- Never store secrets, credentials, tokens, private keys, or sensitive user data in either file.
- Keep both files concise and useful.
- Prefer exact next steps, constraints, changed files, and verification commands over long prose.
- Avoid noisy, speculative, or stale notes.

Working rules:

- Follow existing repository architecture and conventions.
- Preserve unrelated user changes.
- Do not add comments in code.
- Use descriptive and consistent names.
- Prefer reusable modules over large multi-purpose files.
- Write production-grade code with maintainable structure, strong typing, validation, and error handling.
- Do not guess missing requirements; state assumptions explicitly when needed.
- Avoid hardcoded values, hacks, tightly coupled logic, and shortcuts.
- Keep code modular, testable, and scalable.
- Keep commit messages under 140 characters.
- Commit and push completed work when requested or when a task explicitly includes publishing changes.
- Keep context-management docs practical for Codex in VS Code and CLI.
- Keep this `AGENTS.md` small and durable.
