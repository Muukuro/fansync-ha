# Contributing to FanSync Bluetooth

Thanks for contributing.

## Before You Start
- Open an issue first for non-trivial changes.
- Keep changes focused and small.
- Follow the existing architecture and protocol guardrails in `AGENTS.md`.

## Development Setup
- Python: `3.13`
- Preferred: Pipenv

```bash
pipenv install --dev
pipenv run ruff check .
pipenv run black --check .
pipenv run pytest -q
```

## Coding Guidelines
- Keep BLE sessions short-lived (connect, read/write, disconnect).
- Preserve unchanged frame fields in control writes.
- Avoid broad refactors unless discussed in an issue.
- Add tests for behavior changes and bug fixes.

## Pull Request Checklist
- [ ] Linked to an issue (or explains why not).
- [ ] `ruff`, `black --check`, and `pytest` pass.
- [ ] New behavior is covered by tests.
- [ ] Docs updated if user-facing behavior changed.

## Commit Style
- Use clear, imperative commit messages.
- Keep one logical change per commit when possible.

## Release Notes
- For user-visible changes, include a short summary in the PR description:
- `What changed`
- `Why`
- `Risk/rollback notes`
