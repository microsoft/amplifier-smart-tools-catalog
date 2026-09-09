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

Add the skill with existing skills tooling.

```bash
npx skills add robotdad/amplifier-tools-smart-catalog
```

Follow the interactive prompts to select the target agents.
For a local checkout, replace the repository argument with its directory path.
The default is project scope; add `--global` for user scope.
For Amplifier, copy or link `skills/discover-smart-tools/` into
`.amplifier/skills/` or `~/.amplifier/skills/` and enable its skills capability.

Ask the host to find a Smart Tool for a task or explain how to install one.
The skill normally reads the catalog from GitHub. To use an unpublished local
catalog, explicitly give the host the checkout path.
Adding the skill does not install Smart Tools or configure their credentials.

## Product direction

- [Vision](docs/VISION.md)
- [Catalog source contract](contracts/catalog-source.v1.md)
- [Discovery contract](contracts/discovery.v1.md)