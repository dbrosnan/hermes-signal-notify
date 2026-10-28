# Contributing to signal-notify

Thanks for helping. This is a small plugin, so the process is light.

## Ways to help

- **Report a bug.** Open an issue with the bug template. Include your Hermes version
  (`hermes --version`), your signal-cli version, and the `signal-notify` lines from
  `~/.hermes/logs/agent.log`. Remove phone numbers before posting.
- **Suggest a feature.** Open an issue with the feature template first, so we can agree on
  the shape before you write code.
- **Send a pull request.** Bug fixes, tests and docs are always welcome.
- **Security problems** go through private reporting, never public issues. See
  [SECURITY.md](SECURITY.md).

## Development setup

You need Python 3.11 or newer and [uv](https://docs.astral.sh/uv/). Hermes itself is only
needed for the final validation step.

```bash
git clone https://github.com/dbrosnan/hermes-signal-notify
cd hermes-signal-notify
uvx --with pytest-cov pytest --cov=. tests   # tests, no Hermes or Signal needed
uvx ruff check .                             # lint
hermes plugins validate .                    # the same check the Hermes catalog runs
```

To try a change against your own Hermes, copy `plugin.yaml` and `__init__.py` into
`~/.hermes/plugins/signal-notify/`, then run
`hermes plugins disable signal-notify && hermes plugins enable signal-notify`.

## Pull request checklist

- One change per PR, with a clear title in
  [Conventional Commits](https://www.conventionalcommits.org/) form (`fix: ...`,
  `feat: ...`, `docs: ...`).
- Tests for any behaviour change. CI requires 80% coverage, and the project sits above 90%.
- `uvx ruff check .` and the tests pass.
- `hermes plugins validate .` passes, if you have Hermes installed.
- If you add a hook, setting or environment variable, update `plugin.yaml` (declared
  capabilities must match what the code registers) and the README's settings and
  disclosure sections.
- Add a line under **Unreleased** in [CHANGELOG.md](CHANGELOG.md).

## Rules the code has to keep

These come from the
[Hermes catalog admission rules](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission),
and a PR that breaks one can't be released to the catalog:

- Use public Hermes hooks only. Never patch Hermes code at runtime.
- Read credentials only through `agent.secret_scope.get_secret`. Never read `.env` or other
  credential files.
- No self-updating code, telemetry, or compiled files.
- No new network destinations. The plugin talks only to the user's own signal-cli.
- A failed send must never raise into the agent loop or block it.

## Code style

Standard library only, keyword arguments for hook callbacks, small functions, and comments
only where the reason isn't obvious. Ruff settings are in `pyproject.toml`.

## Conduct

Everyone taking part agrees to the [Code of Conduct](CODE_OF_CONDUCT.md).
