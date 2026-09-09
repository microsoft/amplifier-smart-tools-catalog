---
smart_tool_format: 1
name: team-pulse
version: 0.1.0
description: >
  Reads the Team Pulse lens API -- a knowledge base mined for a team (decision/meeting
  wikis, code/repo wikis, roster, reflection questions) -- as structured data, plus a
  model-backed answer that retrieves and cites its sources. Use for factual questions
  about a team's decisions, what shipped, who owns what, why something happened, or how
  something works.
use_cases:
  - Answer "what did we decide about X" / "who owns Y" / "why did we do Z" with citations
  - Search or browse a team's mined corpus (decision wikis, code/repo wikis)
  - Look up the team roster or a reflection question by id
  - Bulk-download the corpus for offline analysis (embeddings, grep, your own agents)
  - Record a session-mined answer to a reflection question
platforms:
  - linux
  - macos
requires:
  - name: network access to the lens API
    purpose: >
      The configured Team Pulse endpoint URL must be reachable over HTTPS.
      Without it, no capability can run.
    install: docs/network.md
  - name: team-pulse credentials
    purpose: >
      Every capability needs either a per-user Azure AD bearer token (az login)
      or a shared API key. Without either, every capability raises with a remedy.
    install: docs/auth.md
  - name: model provider credentials
    purpose: >
      Only `answer` needs OPENAI_API_KEY or ANTHROPIC_API_KEY. Every deterministic
      capability runs with no provider configured at all.
    optional: true
    install: docs/auth.md
---

# team-pulse

Team Pulse lens API as structured data, plus `answer` -- a model-backed capability
that retrieves from the corpus and cites its sources. One library, one thin
`team-pulse` CLI.

## Sharp edges

- **`answer` costs tokens.** It runs a bounded model-backed loop (default up to 6
  steps) using YOUR configured provider (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`).
  It is not `ask` (see below).
- **`ask` spends the SERVER's model budget, not yours.** It calls the Team
  Pulse server's own LLM (`POST /api/lens/ask`) and is a *different*
  capability from `answer`. Do not combine the two in one workflow.
- **`get` refuses very large pages by design.** Index/overview/log pages can
  be hundreds of KB; a full `get` on one can overflow a caller's context.
  `get` raises `ResourceTooLarge` above 200,000 bytes, naming `search`/`prefix`
  as the remedy. Pass `allow_large=True` (library) / `--allow-large` (CLI) to
  override.
- **Writes need confirmation.** `submit_answer` and `configure` both raise
  `ConfirmationRequired` unless called with `confirmed=True` (or `--confirmed`
  on the CLI) -- checked before any network call or credential resolution.
  `download_corpus` is NOT fenced: it is a local, reversible disk write.
- **The retrieval strategy is the source bundle's own text**, shipped verbatim
  in `prompts/retrieval-strategy.md` and used as `answer`'s system prompt.
  Nothing in this tool paraphrases it.
- **The Amplifier adapter mounts only three tools**: `team_pulse_answer`,
  `team_pulse_read` (an `op=` dispatcher over the read verbs), and
  `team_pulse_write` (`op=` over `submit_answer`/`download_corpus`/`configure`).
  `ask` is library/CLI-only, to keep it from being confused with `answer`.

## Worked invocations

```bash
team-pulse doctor
team-pulse info
team-pulse search --q "renamed service" --collection docs
team-pulse prefix --prefix projects
team-pulse get --id projects/team-pulse
team-pulse resources --type question --status active
team-pulse graph
team-pulse whoami
team-pulse status
team-pulse ask --prompt "What is team-pulse?"
team-pulse download-corpus --dest-dir ./corpus
team-pulse submit-answer --user-id jdoe --question-id higher-level-work --answer "..." --confirmed
team-pulse configure --url https://team-pulse.example.com --confirmed
team-pulse answer --question "What did we decide about the rename?"
team-pulse manifest
```
