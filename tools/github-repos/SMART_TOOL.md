---
smart_tool_format: 1
name: github-repos
version: 0.3.0
description: >
  Finds the most-starred GitHub repositories created in a recent window, optionally
  filtered by language, as structured data -- and can rank them against a stated goal
  using a model. Also manages the authenticated user's account: list your own
  repositories, create a new one, change a repository's visibility, list pending
  repository invitations, and accept or decline them. Use when you want to know
  what is gaining traction, which of several projects fits what you are trying to
  do, or you need to inspect or change your own GitHub repositories and act on
  pending collaboration invitations.
use_cases:
  - Find the fastest-growing repositories in a language right now
  - Shortlist candidate libraries for a specific job
  - Check whether a problem space already has a popular solution
  - List your own repositories, filtered by visibility or affiliation
  - Create a new repository (private by default) for yourself or an org
  - Change a repository from private to public, or back
  - Check for pending repository invitations
  - Accept or decline a pending collaboration invitation
platforms:
  - linux
  - macos
requires:
  - name: network access to api.github.com
    purpose: Source of the repository data. Without it, no capability can run.
    install: docs/network.md
  - name: GITHUB_TOKEN
    purpose: >
      Raises the GitHub search rate limit from 10 to 30 requests per minute for
      get_top_repos. Without it, deterministic fetching still works but may be
      rate-limited under repeated use. REQUIRED for the six account capabilities
      (my_repos, create_repo, set_repo_visibility, invitations, accept_invitation,
      decline_invitation) -- without it, each fails immediately with a remedy
      naming how to mint a token.
    optional: true
    install: docs/network.md
  - name: model provider credentials
    purpose: >
      Required only by the model-backed recommend capability. Without it,
      deterministic fetching still works and recommend fails with a remedy.
    optional: true
    install: docs/providers.md
---

# GitHub repositories

Reach for this when you want to know what is gaining traction on GitHub, which
of several candidate projects fits a stated goal, or you need to inspect or
change your own GitHub repositories.

`get_top_repos` is deterministic and needs no credentials. It searches for
repositories created within a recent window, sorted by stars, optionally
filtered by language.

`recommend` is model-backed. Hand it repositories and a goal, and it returns a
ranked shortlist with a one-line reason each -- structured, not prose. Without a
provider key it fails and names the remedy.

`list_my_repos`, `create_repo`, `set_repo_visibility`, `list_invitations`,
`accept_invitation`, and `decline_invitation` are account operations. All six
require `GITHUB_TOKEN`; without it, each fails immediately with a remedy.
`create_repo`, `set_repo_visibility`, `accept_invitation`, and
`decline_invitation` create or modify real data and additionally require
`confirmed=True` (or `--confirmed` on the CLI) -- checked before anything
else, including the token lookup.

## Sharp edges

- GitHub's search API rate-limits unauthenticated callers to 10 requests per
  minute. Set `GITHUB_TOKEN` for 30.
- "Trending" here means *created recently and highly starred*, which is not the
  same as GitHub's own trending page. It favours new projects over established
  ones gaining stars.
- `since_days` is clamped to 1..365, `limit` to 1..50 for get_top_repos; the
  account listing verbs (`my_repos`, `invitations`) clamp `limit` to 1..100 and
  fetch a single page -- they do not paginate.
- `create_repo` and `set_repo_visibility` write real data immediately once
  confirmed. There is no dry-run: the confirmation check IS the safety gate.
  `create_repo` defaults to `private=True`.
- `accept_invitation` is a real account action, gated behind `confirmed=True`
  just like the write verbs above -- it grants the inviter's chosen access to
  your account's collaboration graph immediately. `decline_invitation` is
  irreversible without a fresh invite from the repository owner. Both GitHub
  endpoints return HTTP 204 with no response body on success, so neither
  result carries repository details the API didn't hand back -- only the
  invitation id and a boolean confirming the action.

## Worked invocations

```bash
github-repos get-top-repos --language rust --since-days 30 --limit 10
github-repos recommend --goal "pick an HTTP client" --language rust
github-repos my-repos --visibility private --limit 20
github-repos create-repo --name my-new-repo --description "A test repo" --confirmed
github-repos set-visibility --full-name octocat/my-new-repo --visibility public --confirmed
github-repos invitations
github-repos accept-invitation --invitation-id 12345 --confirmed
github-repos decline-invitation --invitation-id 12345 --confirmed
github-repos manifest
```
