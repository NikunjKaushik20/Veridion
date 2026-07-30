# Contributing to Veridion

Thank you for your interest in contributing to Veridion — small, focused contributions are welcome (typo fixes, docs improvements, bug reports, or enhancements).

Please follow these simple guidelines to make the contribution process smooth:

- Fork the repository and create a feature branch from main with a clear name, e.g. `docs/add-contributing` or `chore/editorconfig`.
- Keep changes focused and minimal per pull request.

Development workflow

1. Clone your fork and create a branch:

```bash
git clone https://github.com/<your-username>/Veridion.git
cd Veridion
git checkout -b feat/description
```

2. Backend (Python) — run locally

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Seed local DB (optional)
python seed.py
# Start API
uvicorn main:app --reload --port 8000
```

3. Frontend (React + Vite) — run locally

From project root:

```bash
npm install
npm run dev
```

4. Formatting and linting

- This project includes basic EditorConfig settings to keep whitespace/indentation consistent.
- Use Prettier / your editor's formatting tools for frontend code. Keep TypeScript/JS files formatted with 2-space indentation.

Commit messages and PRs

- Use present-tense, short commit messages with a type prefix, for example:
  - `docs: fix typo in README`
  - `feat: add export to API`
  - `chore: add .editorconfig`
- Open a Pull Request against `main` and include a short description of the change and the motivation.

Reporting issues

- Please use GitHub Issues to report bugs or suggest enhancements. Provide steps to reproduce, expected vs. actual behavior, and any logs or errors.

Code of Conduct

- Be respectful and constructive. This repository follows standard open-source etiquette.

Thank you for helping improve Veridion!