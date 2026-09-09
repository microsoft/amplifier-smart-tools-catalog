# Amplifier Tools Smart Catalog

A folder-based catalog and one shared discovery skill for local coding agents.

The product consists of source pointers in `tools/<slug>/source.json`, exact
generated `SMART_TOOL.md` snapshots with provenance, and the
`discover-smart-tools` skill. Tools keep their own manifests and usage help.
Skill installation uses existing host tooling such as `npx skills add`.
This repo does not provide an installer or validation kit.

Browse the entries in [tools/](tools/). All current entries omit `ref`, selecting
`main`. Entries in multi-tool repositories specify their distribution root
with `path`; omitting `path` selects the repository root.
The shared [discovery skill](skills/discover-smart-tools/SKILL.md) verifies and
uses snapshots before following a selected tool's own installation guidance and
help. The `refresh-manifests` GitHub Actions workflow refreshes snapshots daily
and on manual dispatch, and also when a source pointer or refresh implementation
changes on `main`. Each snapshot records its own last successful refresh time;
that timestamp is not a claim that it is currently fresh. Failed source refreshes
preserve the last successful snapshot and are reported in the action logs.
The snapshot-first skill has not yet been exercised across hosts.

## Use the skill

### Choose agents explicitly

For Claude Code, Codex, and GitHub Copilot, name the agents directly.

```bash
npx skills add robotdad/amplifier-tools-smart-catalog \
  --skill discover-smart-tools \
  --agent claude-code codex github-copilot
```

Keep only the agents you use. For example, to select just Codex, use
`--agent codex`. This skips agent selection, but other setup prompts may remain.
Add `--yes` if you want to accept the remaining defaults without prompts.

The default is project scope. Run the command from the project where you want
the skill available. Add `--global` for user-wide availability across projects.

### Choose interactively

If you prefer to choose through prompts, omit `--agent`.

```bash
npx skills add robotdad/amplifier-tools-smart-catalog
```

The CLI detects installed agents and guides you through target selection and
setup. Omitting `--agent` does not mean installing to every supported agent.

For a local checkout, replace the repository argument with its directory path.

### Amplifier

Amplifier is not a target supported by the skills CLI.
For Amplifier, copy or link `skills/discover-smart-tools/` into
`.amplifier/skills/` or `~/.amplifier/skills/` and enable its skills capability.

### Ask for a tool

Ask the host to find a Smart Tool for a task or explain how to install one.
The skill normally reads the catalog from GitHub. To use an unpublished local
catalog, explicitly give the host the checkout path.
Adding the skill does not install Smart Tools or configure their credentials.

## Update the skill

For a project installation, run this from that project.

```bash
npx skills update discover-smart-tools -p
```

For a user-wide installation, use global scope.

```bash
npx skills update discover-smart-tools --global
```

Without a scope flag, `npx skills update discover-smart-tools` prompts for scope.
Start a fresh coding-agent session after updating so it loads the new instructions.

For Amplifier's manual placement, update the source checkout and copy the skill
again if needed. A symlink uses the updated checkout directly.

Skill updates are separate from catalog refreshes. The GitHub Action refreshes
catalog snapshots; updating the skill gets changes to the discovery instructions.

## Product direction

- [Vision](docs/VISION.md)
- [Catalog source contract](contracts/catalog-source.v1.md)
- [Discovery contract](contracts/discovery.v1.md)