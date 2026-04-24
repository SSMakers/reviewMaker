# Copilot Coding Agent Instructions

Before changing code in this repository:

1. Read `Index.md`.
2. Read `docs/release-process.md`.
3. Inspect only the files relevant to the requested change.

Working rules:

- Preserve the existing PyQt6 desktop app structure.
- Keep business logic outside UI classes where possible.
- Update `Index.md` when adding, deleting, or changing module responsibilities.
- For deployable code changes, update `version.py` using the release process rules.
- Do not leave `IS_DEBUG=True` on `main`.
- Include test or verification notes in every PR.

PR body must include:

```text
Change type: bugfix | feature | breaking | docs | internal
Version bump: patch | minor | major | none
Current version: x.y.z
Next version: x.y.z
Tested:
- ...
Release notes:
- ...
Risk:
- ...
```
