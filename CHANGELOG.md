# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-28

### Added

- Signal texts when a Hermes turn pauses, fails or is interrupted (`on_session_end`).
- Signal texts when Hermes waits on a clarify question, an approval or a sudo prompt
  (`on_human_input_request`).
- A preview of the final reply in the pause text (`post_llm_call`), capped by
  `reply_chars`.
- Settings: `recipient`, `notify_on`, `skip_platforms`, `reply_chars`.
- Skips Signal-origin, cron and subagent turns by default.
- Sends identical texts within 60 seconds only once, and sends one text per turn even
  when the CLI exit path reports the turn again.
- Community docs, issue and PR templates, CI with pinned actions, Dependabot and an
  OpenSSF Scorecard workflow.

[Unreleased]: https://github.com/dbrosnan/hermes-signal-notify/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/dbrosnan/hermes-signal-notify/releases/tag/v1.0.0
