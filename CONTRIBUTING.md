# Contributing to Stock Manager Pro

Thanks for your interest in improving Stock Manager Pro! This guide covers how to
set up the project, the branch/release workflow, and the conventions we follow.

## Project layout

The application lives under [`stock-manager/`](stock-manager/) at the repo root:

```
stock-manager/
  src/files/          # entry point (main.py) and app/ package
  requirements.txt    # runtime + build dependencies
```

The app uses a strict layered architecture — **UI → Services → Repositories → Models → Core**.
UI never imports repositories directly; services never import UI. See
[`stock-manager/CLAUDE.md`](stock-manager/CLAUDE.md) for the full architecture guide.

## Local setup

```bash
# from the repo root
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r stock-manager/requirements.txt

# run in development
cd stock-manager/src/files
python main.py
```

Requires **Python 3.11+** on **Windows 10/11**.

## Branch & release workflow

We use a `dev`-based integration flow:

1. Branch from **`dev`** (e.g. `feat/po-export`, `fix/barcode-scan`).
2. Open your PR **against `dev`**. CI (`.github/workflows/ci.yml`) runs ruff +
   pytest on every push/PR to `dev` and `main`.
3. Once merged into `dev` and ready to ship, a maintainer cuts a release by
   pushing a `vX.Y.Z` tag. `.github/workflows/release.yml` then builds the signed
   Windows executable with PyInstaller, extracts the matching `CHANGELOG.md`
   entry, and publishes the GitHub Release.

**Do not** push feature work directly to `main` — `main` only advances through the
release flow.

## Coding conventions

- `from __future__ import annotations` at the top of every module.
- Type hints on all function signatures; dataclasses for models.
- f-strings over `.format()`/`%`.
- All user-facing text goes through `t("key")` with **EN, DE, and AR** added to
  `app/core/i18n.py` — never hardcode display strings.
- Colors come from the theme `Tokens` — never hardcode colors in widgets.
- Target: keep files under ~500 lines; extract widgets/pages rather than growing
  monoliths.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Keep the subject under
72 characters and explain the *why* in the body when it isn't obvious.

## Before you open a PR

- [ ] `ruff check app --select E9,F821,F811` passes (run from `stock-manager/src/files`)
- [ ] `pytest` passes
- [ ] New UI strings added in all three languages
- [ ] `CHANGELOG.md` updated under the unreleased/next-version heading

## Reporting bugs & requesting features

Use the issue templates under **New issue**. For security issues, follow
[`SECURITY.md`](SECURITY.md) instead of opening a public issue.
