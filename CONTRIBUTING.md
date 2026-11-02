# Contributing

Thanks for your interest. This is research code for a single paper, so the scope is narrow,
but bug reports and suggestions are welcome.

## Reporting a problem

Open an issue using one of the templates:

- **Bug report:** something in the code does not work as documented.
- **Experiment:** a proposal or question about an experiment, model or dataset.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pre-commit install
```

## Branches

- `main`: stable, always passes tests. Changes only via pull request.
- `dev`: integration branch. Feature branches merge here first.
- `feat/<phase>-<topic>`: new work, for example `feat/p1-rendering`.
- `fix/<topic>`, `docs/<topic>`: small fixes and documentation.
- `exp/<name>`: exploratory work that may be thrown away.

Open pull requests against `dev`, not `main`.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`,
`docs:`, `refactor:`, `chore:`, `ci:`. Keep each commit small and focused.

## Before opening a pull request

- `pytest` passes.
- `pre-commit run --all-files` passes (ruff, file checks, secret scan, notebook output strip).
- New code has short docstrings and, where it makes sense, a test.
- Experiment settings live in `configs/`, not hard-coded.
- Fill in the pull request template: what, why, how tested.

## What must never be committed

- Secrets: `.env`, `kaggle.json`, API or Hugging Face tokens. Use `.env.example` for names only.
- Generated data (`data/`) and raw results (`results/scores/`, `results/tables/`,
  `results/figures/`). Provide scripts that regenerate them instead.
- Notebook outputs (stripped automatically by `nbstripout`).
- Personal information or local absolute paths.
