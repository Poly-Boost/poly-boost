# Repository Guidelines

## Project Structure & Module Organization
- `poly_boost/` — Python package: `core/` (logic, logging, config), `services/`, `api/` (`routes/`, `schemas/`), `bot/`, `cli.py`.
- `frontend/` — Vite + React + TypeScript app (`npm run dev|build|lint`).
- `config/` — Runtime config (`config.yaml`, `config.example.yaml`).
- `tests/` and root `test_*.py` — Script-style tests and tools.
- `scripts/`, `examples/`, `docs/`, `rest/` (`*.http` API requests).

## Build, Test, and Development Commands
- Python deps: `uv sync` (recommended) or `pip install -r requirements.txt`.
- API (dev): `python run_api.py` → FastAPI on `http://localhost:8000`.
- CLI: `python run_cli.py`.
- Telegram Bot: `python run_bot.py`.
- Frontend (dev): `./start_frontend.sh` or `start_frontend.bat` (Windows) → `frontend/` `npm run dev`.
- Frontend build: `cd frontend && npm run build`; lint: `npm run lint`.
- Tests: run script tests directly, e.g. `python tests/test_message_queue.py`, `python tests/test_logging.py`. API checks: `python test_api_endpoints.py` (ensure API running first).

## Coding Style & Naming Conventions
- Python 3.13+, 4-space indent, type hints, module-level docstrings.
- Names: `snake_case` for functions/vars/modules, `PascalCase` for classes.
- Logging: use `poly_boost.core.logger.setup_logger`; avoid `print` in library code.
- Frontend: TypeScript, React components in `PascalCase`, keep modules small and typed; fix ESLint warnings before PR.

## Testing Guidelines
- Prefer small, focused script tests under `tests/` named `test_<area>.py`.
- For API, use `rest/*.http` or `curl` against local server; update `TEST_WALLET_ADDRESS` in `test_api_endpoints.py` as needed.
- Add reproducible steps and expected output in test docstrings.

## Commit & Pull Request Guidelines
- Conventional commits (seen in history): `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`.
- PRs must include: clear description, linked issues, how to run/validate, screenshots (frontend), sample logs (backend), and config notes if applicable.

## Security & Configuration Tips
- Never commit private keys; use `.env` and `config/config.yaml` placeholders (`config.example.yaml` available).
- Do not hardcode endpoints or secrets; prefer env vars and loader in `poly_boost.core.config_loader`.

## Agent-Specific Notes
- Keep changes minimal and localized; do not rename public APIs casually.
- Mirror existing patterns (services/core separation, API in `routes/`, tests as runnable scripts).

