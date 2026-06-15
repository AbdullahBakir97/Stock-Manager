# Security Policy

## Supported versions

Security fixes are applied to the latest released version of Stock Manager Pro.
Please always run the most recent release from the
[Releases page](https://github.com/AbdullahBakir97/Stock-Manager/releases).

| Version | Supported |
|---------|-----------|
| Latest `2.6.x` | ✅ |
| Older releases | ❌ |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, use one of the following private channels:

- Open a private advisory via **GitHub → Security → Report a vulnerability**, or
- Email **abdullah.bakir.1997@gmail.com** with the details.

Please include:

- A description of the issue and its potential impact
- Steps to reproduce (proof-of-concept if possible)
- Affected version(s) and your environment

You can expect an initial acknowledgement within **5 business days**. Once the
issue is confirmed, we will work on a fix and coordinate a release. We will credit
reporters who wish to be acknowledged.

## Scope

Stock Manager Pro is an **offline-first desktop application**; data stays local by
default. Cloud sync (Turso/libSQL) is strictly opt-in. Reports concerning local
data handling, the auto-updater (SHA256 verification), and the optional sync layer
are all in scope.
