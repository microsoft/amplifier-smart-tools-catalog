# Catalog Source Contract - v1 (DRAFT)

**Who builds against this** Catalog contributors and consumers that read source
pointers, including the shared discovery skill.

## What it looks like

A contributor adds one folder. The source pointer can float on main or identify
a specific revision without describing the tool a second time.

```text
tools/tmux/source.json
```

```json
{
  "repository": "https://github.com/microsoft/amplifier-smart-tool-tmux.git",
  "ref": "9a4a167101c92b803f7a693e6614a21a6d21cf5b"
}
```

## Purpose

Contributors and readers agree on where a tool comes from.
Defaults cannot silently change a lookup's meaning.
The catalog preserves the upstream tool as the owner of its description.

## Core (the teeth)

1. **The inventory is folder-based.** Entries live at `tools/<slug>/source.json`.
   Readers enumerate that directory without requiring a top-level inventory.
2. **A source pointer identifies a repository and optional location.**
   `repository` is a required HTTPS Git URL. Optional string `ref` identifies
   a branch, tag, or full commit SHA. Optional string `path` identifies the
   distribution root containing `smart-tool.json`.
3. **Omission has explicit defaults.** Missing `ref` means exactly `main`.
   Missing `path` means `.`. An unavailable main branch is an error, not a
   reason to substitute the repository's default branch.
4. **Revision and URL are separate.** `repository` uses HTTPS Git notation,
   not an installer-specific `git+https` URL containing a revision.
5. **A lookup uses one resolved commit.** A branch or tag is resolved once for
   each inspected source per discovery operation. Descriptor and manifest
   are read from that same commit. A full commit pin is honored.
6. **Provenance is reported.** Readers identify the repository, distribution
   path, requested or default ref, and resolved commit used for the lookup.
7. **The tool owns the manifest.** Readers follow upstream `smart-tool.json`
   to `SMART_TOOL.md`. An entry may contain only an exact generated
   `SMART_TOOL.md` snapshot plus provenance recording its source and refresh
   time; it must not contain an independently written or maintained tool
   description.
8. **A failed lookup is visible.** An inaccessible repository, unresolved ref,
   or missing descriptor or manifest produces a specific blocker for that
   entry, not invented metadata or a silent switch to another source.

## What v1 deliberately does NOT freeze

- Fetch library or GitHub API choice - reconsider when a transport limits use.
- Search summaries beyond exact generated manifest snapshots - reconsider when
  measured catalog size, latency, or offline use makes them necessary.
- Installation mechanisms remain owned by the tool and existing host tooling.
  This catalog does not ship an installer.

## Observable behavior

These criteria describe correctness, not a validation-kit deliverable or a
claim that checks have passed.

- Omitted fields resolve to main and the root; explicit nested paths work.
- A full commit pin is preserved and a moving branch is resolved only once.
- An unavailable main does not fall back to another branch.
- Descriptor and manifest provenance contains the same resolved commit.
- Missing source artifacts produce named blockers rather than substituted data.
- Generated snapshots, when present, preserve the upstream manifest bytes and
  record the repository, requested ref, distribution path, resolved commit,
  original manifest path, and successful refresh time.
