# signal-notify for Hermes Agent

Get a Signal text when your [Hermes Agent](https://github.com/NousResearch/hermes-agent)
needs you. Hermes texts you when:

| Event | Text |
|---|---|
| A turn finishes and Hermes is waiting for your next message | `⏸ Hermes paused [tui …a1b2c3d4]` plus the start of its reply |
| A turn fails or ends without finishing (an error, the iteration limit) | `❌ Hermes errored [...]` plus the exit reason |
| A turn is interrupted | `⏹ Hermes stopped [...]` plus the reason |
| Hermes asks a `clarify` question, needs an approval, or needs a sudo password | `❓ Hermes is asking [...]` plus the question |

Leave a long agent run going, walk away, and your phone tells you when it stops or has a
question.

## Requirements

- Hermes Agent 0.21.5 or newer.
- A running [signal-cli](https://github.com/AsamK/signal-cli) daemon with its HTTP endpoint
  on (`signal-cli daemon --http`), registered to a number Hermes sends from. If you already
  use Hermes' Signal gateway, you have this.
- These variables in `~/.hermes/.env`, which Hermes' Signal gateway also uses:
  - `SIGNAL_HTTP_URL`, for example `http://127.0.0.1:8080`. Use a loopback, private network
    (such as Tailscale) or HTTPS address: text travels to signal-cli as plain HTTP otherwise.
  - `SIGNAL_ACCOUNT`, the number signal-cli is registered to
  - `SIGNAL_HOME_CHANNEL`, the number to text. The `recipient` setting overrides it.

## Install

```bash
hermes plugins install https://github.com/dbrosnan/hermes-signal-notify
hermes plugins enable signal-notify
```

A running gateway picks up the hooks when the plugin is enabled. CLI and TUI sessions pick
them up the next time they start.

## Settings

Set these in the Desktop app under Settings → Plugins → signal-notify, or under
`plugins.entries.signal-notify.settings` in `config.yaml`:

| Setting | Default | Meaning |
|---|---|---|
| `recipient` | `""` | Number or UUID to text. Empty uses `SIGNAL_HOME_CHANNEL`. |
| `notify_on` | `[paused, failed, interrupted, question]` | Which events send a text. |
| `skip_platforms` | `[signal, cron, subagent]` | Turns from these platforms never text. Signal chats already show the reply, cron jobs have their own delivery, and subagent turns would be noise. |
| `reply_chars` | `300` | Characters of the reply or prompt to include. `0` sends no conversation text, only the event and session. |

Identical texts within 60 seconds are sent once, so a burst of the same prompt does not flood
your phone.

## What it sends and where (disclosure)

- **Network:** each event makes one HTTP POST to the signal-cli endpoint in
  `SIGNAL_HTTP_URL`, in plain HTTP unless that URL is `https://`. signal-cli then sends an end-to-end encrypted Signal message to the
  recipient. Nothing goes to any other service.
- **Conversation text, on by default:** up to `reply_chars` (300) characters of the final
  reply, the clarify question, or the approval or sudo command. Hermes redacts secrets from
  question and command text before the hook sees it. **Reply text is not redacted**, so
  anything the agent wrote in the first 300 characters of its reply reaches your phone. Set
  `reply_chars: 0` to send no conversation text.
- **Never sent:** sudo passwords and your answers to questions. Hermes does not give either
  to hooks.
- **Credentials:** reads `SIGNAL_HTTP_URL`, `SIGNAL_ACCOUNT` and `SIGNAL_HOME_CHANNEL`
  through Hermes' `secret_scope`. It stores nothing and never reads `.env` itself.
- **Memory:** keeps a preview of at most 64 recent replies, each clipped to `reply_chars`.
- **Background work:** each send runs on a short-lived daemon thread with a 20 second
  timeout, so a slow or offline signal-cli never blocks Hermes. Failures are logged and
  dropped.
- No shell commands, no files written, no telemetry, no self-updates.

The install security scan flags `sudo_usage` as a caution. That comes from the label for
Hermes' sudo prompt. The plugin never runs sudo.

## How it works

Three public Hermes hooks, with no core patching:

- `post_llm_call` keeps the latest reply for each session so the pause text can quote it.
- `on_session_end` fires when every turn finishes and decides whether the turn paused,
  failed or was interrupted.
- `on_human_input_request` fires right before Hermes blocks on a clarify, approval or sudo
  prompt.

## Development

```bash
uvx --with pytest-cov pytest --cov=. tests
hermes plugins validate .
```

Using Telegram instead? See
[telegram-notify](https://github.com/madpower2000/hermes-telegram-notify).

## License

MIT
