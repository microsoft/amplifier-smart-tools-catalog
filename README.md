# Amplifier Tools Smart Catalog

A folder-based catalog and one shared discovery skill for local coding agents.

The product consists of source pointers in `tools/<slug>/source.json` and the
`discover-smart-tools` skill. Tools keep their own manifests and usage help.
Skill installation uses existing host tooling such as `npx skills add`.
This repo does not provide an installer or validation kit.

The catalog entries and skill are not implemented yet.

## Product direction

- [Vision](docs/VISION.md)
- [Catalog source contract](contracts/catalog-source.v1.md)
- [Discovery contract](contracts/discovery.v1.md)