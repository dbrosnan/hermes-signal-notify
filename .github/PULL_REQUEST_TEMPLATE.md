## What this changes

<!-- One or two sentences, plus the issue it fixes: Fixes #123 -->

## How I tested it

<!-- Commands run, and what you saw. A real Signal text is a bonus, not a requirement. -->

## Checklist

- [ ] Tests added or updated, and `uvx --with pytest-cov pytest --cov=. tests` passes
- [ ] `uvx ruff check .` and `uvx ruff format --check .` pass
- [ ] `hermes plugins validate .` passes (if you have Hermes)
- [ ] `plugin.yaml` and the README's settings and disclosure sections match any new hook,
      setting or environment variable
- [ ] A line under **Unreleased** in `CHANGELOG.md`
