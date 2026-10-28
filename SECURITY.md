# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 1.x | Yes |
| Older | No |

Only the latest release gets fixes. The Hermes catalog pins one commit, so a fix reaches
catalog users after the pin is updated. See [docs/RELEASING.md](docs/RELEASING.md).

## Reporting a vulnerability

**Do not open a public issue.** Report privately through GitHub:
[Report a vulnerability](https://github.com/dbrosnan/hermes-signal-notify/security/advisories/new).

Please include what an attacker could do, how to reproduce it, and the versions of the
plugin, Hermes and signal-cli you used.

What to expect:

- An acknowledgement within 5 days.
- An assessment and a planned fix date within 14 days.
- Credit in the advisory and changelog, unless you'd rather stay anonymous.

## In scope

- Conversation text, prompts or credentials reaching anyone other than the configured
  signal-cli endpoint and recipient.
- Anything that lets a notification block, crash or change the behaviour of the Hermes
  agent loop.
- Settings or environment values being read from outside Hermes' `secret_scope`.

## Out of scope

- The security of signal-cli, the Signal service, or the network between Hermes and
  signal-cli. Use a loopback, private network or HTTPS address, as the README explains.
- Reply text in notifications. Sending up to `reply_chars` of it is documented behaviour.
  Set `reply_chars: 0` to turn it off.
