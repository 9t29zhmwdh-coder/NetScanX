# Contributing to NetScanX

## Getting Started

### Prerequisites

- Python 3.11+
- [Docker](https://docker.com) (optional)

### Setup

1. Fork the repository
2. `git clone https://github.com/YOUR_USERNAME/NetScanX`
3. `cd NetScanX`
4. `python -m venv .venv && source .venv/bin/activate`
5. `pip install -e ".[dev]"`

## Development Workflow

1. Create a feature branch: `git checkout -b feature/xyz`
2. Make your changes
3. Run tests: `pytest`
4. Run linter: `ruff check .`
5. Commit: `git commit -m "[feat] description"`
6. Push and open a Pull Request

## Code Style

- Python: `ruff format .` + `ruff check .`
- Follow PEP 8

## Commit Convention

`[type] description` — where type is:
- `[feat]` — new feature
- `[fix]` — bug fix
- `[docs]` — documentation only
- `[refactor]` — code cleanup
- `[test]` — tests only

## Release Checklist

Before pushing a version tag (which triggers `.github/workflows/release.yml`):

1. `pytest -v` and `ruff check .` both pass.
2. CHANGELOG.md and ROADMAP.md are up to date, version bumped in `pyproject.toml`.
3. Build the portable launcher locally for at least one OS and validate it manually: `pyinstaller build/netscanx-<os>.spec --workpath build/_work`, then run the resulting binary from an empty folder outside the dev environment (simulating the USB use case). Confirm `discover`, `services`, and `dashboard` all work, and that the dashboard's static assets load (no 404s). PyInstaller's dependency detection misses some dynamically-imported modules (see the `hiddenimports` comments in `build/*.spec`); a build that succeeds does not guarantee it runs.
4. After the tag-triggered release build completes, download the macOS and Linux binaries from the GitHub Release and smoke-test them on real (or CI-adjacent) machines at least once before announcing the release, since PyInstaller does not cross-compile and those platforms cannot be validated from this dev environment.

## Questions?

Open an issue or discussion on GitHub.
