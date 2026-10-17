# Repository Guidelines

## Project Structure & Module Organization

This Python project prepares bag-video RGB-D observations and mesh assets for material correspondence research. Registration and tracking remain planned work.

- `scripts/`: import (`prepare_data.py`), derive (`bootstrap.py`), validate (`validate.py`), and shared I/O (`common.py`).
- `configs/`: JSON import paths, frame selections, units, and download plans.
- `schemas/`: material-anchor and correspondence JSON schemas.
- `data/annotations/` and `data/manifests/`: tracked annotation templates and provenance records.
- `data/raw/`, `data/derived/`, and `outputs/`: ignored inputs, generated assets, previews, and reports.
- `docs/`: Chinese planning, technical-route, and annotation guides; start with `README.md`.

## Build, Test, and Development Commands

Use Python 3.10/3.11. Run from the repository root; PowerShell setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-bootstrap.txt
```

- `python -B scripts/prepare_data.py --dry-run`: inspect selected imports without copying.
- `python -B scripts/prepare_data.py`: copy inputs and verify hashes. Use `--source-root <path>` when importing from a relocated upstream repository.
- `python -B scripts/bootstrap.py`: regenerate RGB frames, point clouds, topology arrays, previews, and missing annotation templates.
- `python -B scripts/validate.py`: check prepared data and write `outputs/bootstrap/validation_report.json`.

Run import, bootstrap, and validation sequentially. Registration dependencies are optional: `python -m pip install -r requirements-registration.txt`.

## Coding Style & Naming Conventions

Follow existing Python style: four-space indentation, `snake_case` functions and variables, `UPPER_CASE` constants, and short module docstrings. Use `pathlib` and helpers in `scripts/common.py` for portable paths and atomic JSON writes. JSON uses two-space indentation. Save text as UTF-8 with LF endings, matching `.gitattributes`. No formatter or linter is configured.

## Testing Guidelines

`validate.py` is the current integration check; no unit-test framework or coverage threshold is configured. Run it after changing preprocessing, geometry, configuration, or annotations. It checks hashes, frame completeness, projection consistency, mesh indices, and landmark anchors. Extend relevant checks when adding invariants. A passing integrity report does not establish correspondence accuracy or completed human review.

## Commit & Pull Request Guidelines

The sole existing commit uses `chore: ...`; the README demonstrates `feat: ...`. Continue concise, type-prefixed subjects. PRs should describe the change, affected data/configuration, validation commands and results, and linked issues when applicable. Include previews for visual changes.

## Data & Annotation Integrity

Never overwrite raw inputs or existing manual annotations. Preserve source OBJ vertex/face order and mesh SHA-256 fingerprints. Keep positions in meters, pixels in `(x, y)`, and face indices zero-based. Treat historical hints as unverified. Commit code, documentation, configuration, manifests, and annotations; keep bulk data and generated outputs excluded.
