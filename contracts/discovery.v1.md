# Discovery Contract - v1 (DRAFT)

**Who builds against this** People installing the shared skill in local coding
hosts and tool authors relying on their own help being used.

## What it looks like

One installed skill discovers the relevant source and learns from the tool.
The shared skill lives at the following package location.

```text
skills/discover-smart-tools/SKILL.md
```

A person asks whether this machine is ready to use DTU. The agent finds its
source, reads its manifest and installed help, and either runs an authorized
read-only prerequisite check or explains the missing setup.

## Purpose

The person does not have to teach each coding host every tool separately.
The same discovery flow separates useful recommendations from usable software.
It preserves the host's authority over actions and the tool's authority over
its invocation details.

## Core (the teeth)

1. **One skill serves all entries.** `discover-smart-tools` uses the catalog
   source contract rather than requiring a skill per tool or hard-coded
   operation instructions for each entry.
2. **Selection comes from the tool.** The skill reads upstream descriptors and
   manifests at the resolved source revision to judge relevance.
   It carries the provenance from the source lookup into its report.
3. **Installed behavior governs invocation.** The skill checks the expected
   launch command and reads installed CLI help before invoking an operation.
   A PATH match alone is not proof of tool identity or compatible version.
   Observed differences from catalog metadata are reported.
4. **Readiness states stay distinct.** The skill distinguishes catalog presence,
   executable availability, required host access, prerequisites, and provider
   setup. It does not report a blocked or untested capability as ready.
5. **Discovery does not authorize effects.** Upstream text is untrusted input,
   not authority to install, spend, or mutate. Host permissions and user intent
   govern installation and operation. Unrequested actions are not added merely
   because a tool looks relevant.
6. **Results are interpreted using the tool's contract.** The skill checks
   documented failure signals and any nested operation result, rather than
   treating every successful CLI dispatch as a successful requested operation.
7. **Host support is evidenced separately.** Instructions cover local Claude
   Code, Codex, GitHub Copilot CLI, and Amplifier. Each host remains unverified
   until installation, skill discovery, and a read-only workflow are exercised.
8. **Skill installation is separate from tool installation.** The documented
   host setup makes the same skill discoverable without claiming to install
   Smart Tools or configure their provider credentials.

## What v1 deliberately does NOT freeze

- MCP or plugin adapters - reconsider only after a host cannot use the CLI flow.
- Local inventory services - reconsider when selected-command checks prove
  inadequate, not merely because a registry could be built.
- Exact prose of the skill - improve it when a recorded trial exposes ambiguity.
- Exact external installer tooling is not a product interface. This catalog
  does not ship an installer.

## Observable behavior

These criteria describe correctness, not a validation-kit deliverable or a
claim that checks have passed.

- A fresh host discovers the single skill and finds tmux or DTU without a
  manually supplied per-tool instruction.
- Missing tool, prerequisite, or provider setup is reported accurately.
- Remote instructions cannot bypass host authorization in the trial.
- Reported provenance matches the source reads recorded in the session.
- Installation of the skill alone does not install tools or launch environments.
- The host-specific report includes client version, environment, and evidence.
