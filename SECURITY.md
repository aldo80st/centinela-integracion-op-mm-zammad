# Security handling and secret hygiene

## Working with this repository

This project is intended for demonstrations. Treat every `*.env.example` value as a nonfunctional placeholder and set **unique** credentials in your local `docker/.env` or secure deployment store.

- Never commit local `.env` files, private keys, access tokens, webhook URLs, or production infrastructure data.
- Do not use the example credentials in a network-accessible deployment.
- Docker Compose demonstration ports bind to `127.0.0.1` by default. Any external exposure must be an explicit, separately reviewed decision.
- Do not put real secret values in GitHub issue reports, CI logs, source files, or pull-request comments.
- Prefer runtime-injected variables and an appropriate secret manager for production.
- Enable GitHub's secret scanning and push protection in repository security settings. A local file guard cannot replace those controls.

## If a credential is exposed

1. Identify the system owner and affected environments without testing the suspected credential from an untrusted machine.
2. **Revoke/rotate the credential at its provider**: OpenProject PAT, Zammad token, Mattermost webhook, API key, or database password as applicable.
3. Update the legitimate secret store and active deployments, then verify normal operation with replacement credentials.
4. Inspect provider audit logs for unexpected access, and review related credentials for reuse.
5. Remove the values from the current tree, and only then coordinate a history-cleanup plan.
6. A deletion commit **does not erase Git history**. Before any force-push, coordinate clones, forks, pull requests, protected branches, backups, and incident-response evidence. See [GitHub's removal guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
7. If repository history is rewritten, ask GitHub Support about stale references and cached views when applicable; a force-push alone does not guarantee complete removal.

## Before publishing

Run `git status --short`, inspect staged file names, and double-check that runtime config and private keys are not staged. The `Security hygiene` GitHub Actions workflow blocks tracked environment files and a small set of known key patterns. It is a preventative guard, **not a comprehensive secret scanner**.

For wider coverage, use a dedicated scanner such as Gitleaks locally and configure GitHub secret scanning/push protection.
