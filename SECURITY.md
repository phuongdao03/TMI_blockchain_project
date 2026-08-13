# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities through this repository's private GitHub
Security Advisory flow. Include affected components, reproduction steps and
impact where possible.

Do not disclose vulnerabilities, credentials, personal documents or production
configuration in public issues, discussions or pull requests.

## Supported version

Security updates currently target the latest revision of the default branch.

## Secret handling

Provider credentials, private keys and environment-specific values must be held
in approved secret-management systems. Example environment files contain
placeholders only and must never be populated with real credentials in Git.
