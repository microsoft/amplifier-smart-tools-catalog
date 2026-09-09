# Amplifier Tools Smart Catalog

A folder-based catalog and one shared discovery skill for local coding agents.

The product consists of source pointers in `tools/<slug>/source.json` and the
`discover-smart-tools` skill. Tools keep their own manifests and usage help.
Skill installation uses existing host tooling such as `npx skills add`.
This repo does not provide an installer or validation kit.

The catalog contains [tmux](tools/tmux/source.json) and
[Digital Twin Universe](tools/digital-twin-universe/source.json).
Both omit `ref` and `path`, selecting `main` and the repository root.
The shared [discovery skill](skills/discover-smart-tools/SKILL.md) reads these
pointers and follows each tool's own manifest, installation guidance, and help.
Cross-host operation has not been tested yet.

## Use the skill

Once this repository is published, add the skill with existing skills tooling.

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