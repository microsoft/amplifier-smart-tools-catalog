# Smart Tools discovery with one shared skill

Draft for colleague review - September 9, 2026

Updated with agreed repository naming, folder layout, and source resolution decisions.

## What I want to try

I want to use the same Smart Tools from Codex, Claude Code, GitHub Copilot CLI,
and Amplifier without maintaining separate usage instructions for every tool
in every host.

The planned repository is `robotdad/amplifier-tools-smart-catalog`, containing
a folder-based tool inventory and one discovery skill. The skill finds a suitable tool, reads its
self-description, checks whether it is available in the current environment,
and uses its CLI. The tool owns the details of how to use it.

We have inspected the specification and the tmux and Digital Twin Universe
reference implementations. We have not built the discovery skill or tested
this workflow across hosts.

## Why this looks sufficient

Smart Tools already separates selection from invocation.

- `smart-tool.json` identifies the manifest location and the CLI launch prefix.
- `SMART_TOOL.md` describes the tool, its use cases, prerequisites, and operating
  guidance.
- CLI `--help` is intended to describe the capabilities, arguments, types, and
  results well enough for an agent to invoke them.

The descriptor works once the caller knows the tool's distribution root. It
does not locate tools across a machine. The Smart Tools roadmap explicitly
leaves host awareness and registry design open. [1][2]

A small inventory can supply the missing starting point. We should not need a
skill per tool if the tool's own description is sufficient. Where an agent
cannot work out how to use a tool, I would first look for missing information
in the manifest or help rather than add another instruction wrapper.

## Smallest useful version

Start with the two Microsoft reference implementations.

| Tool | Purpose | CLI |
| --- | --- | --- |
| tmux | Inspect and manage tmux sessions, with optional AI interpretation | `tmux-fleet` |
| Digital Twin Universe | Create and manage isolated test environments, with optional AI profile creation and diagnosis | `amplifier-digital-twin-universe` |

Both expose ordinary commands that need no model credentials and smart commands
that use an embedded model runtime. Neither inspected repository ships an MCP
server. [3][4]

The agreed starting layout uses one folder per tool.

```text
amplifier-tools-smart-catalog/
  tools/
    tmux/
      source.json
    digital-twin-universe/
      source.json
  skills/
    discover-smart-tools/
      SKILL.md
```

Each folder contains a source pointer, not a copied manifest or a separate
selection summary. The directory listing is the inventory. We do not need a
top-level `inventory.json` or a generator for the first version.

The skill reads each tool's upstream descriptor and manifest when needed.
This follows the specification's direction that a registry reads the manifest
from the tool rather than holding its own copy. [2] Detailed descriptions and
command instructions stay in the tool.

If catalog size or fetch latency becomes a problem, we can generate a top-level
search summary from those upstream manifests. Revision-pinned cached snapshots
could support offline access later. Neither is part of the starting version.

## Source pointer schema

`source.json` is our catalog metadata, separate from the Smart Tools
specification. It has three fields.

| Field | Required | Meaning |
| --- | --- | --- |
| `repository` | Yes | HTTPS Git repository URL |
| `ref` | No | Branch, tag, or full commit SHA. Defaults to `main`. |
| `path` | No | Relative path to the distribution root containing `smart-tool.json`. Defaults to `.`. |

A floating entry can omit both optional fields.

```json
{
  "repository": "https://github.com/microsoft/amplifier-smart-tool-tmux.git"
}
```

A pinned entry supplies the full commit SHA.

```json
{
  "repository": "https://github.com/microsoft/amplifier-smart-tool-tmux.git",
  "ref": "9a4a167101c92b803f7a693e6614a21a6d21cf5b"
}
```

For a tool inside a larger repository, `path` identifies its distribution root.
The following repository URL is illustrative.

```json
{
  "repository": "https://github.com/example/tool-collection.git",
  "ref": "main",
  "path": "tools/example-tool"
}
```

Use ordinary HTTPS Git URLs, not installer-specific `git+https` strings.
Repository identity and revision stay separate. The tool's own documentation
determines its installation route, which may use `git+https` for pip or uv.

An omitted `ref` means exactly `main`, not the repository's default branch.
If the requested ref cannot be resolved, report an error rather than choose
another branch. Resolve each branch or tag to a commit SHA once per discovery
operation, read its descriptor and manifest from that same commit, and report
the resolved SHA. A supplied commit SHA is used directly.

## Discovery flow

The skill would follow a common sequence.

1. Enumerate `tools/` and read the per-tool `source.json` entries.
2. Resolve each source being inspected, read `smart-tool.json` at its
   distribution root, and follow its manifest path at the same commit.
   Use the manifests to select a tool that fits the request.
3. Check whether the launch command is available in the current execution
   environment.
4. If missing, present the documented installation route and follow the host's
   approval policy.
5. Read help from the installed tool and check relevant prerequisites.
6. Invoke the requested operation, inspect the result, and report failures or
   missing setup.

The installed tool's help should govern invocation if its version differs from
the catalog reference. A command name on PATH alone is not proof that it is the
expected tool.

This is on-demand discovery of a selected tool. It does not require enumerating
every installed program or maintaining a local inventory service.

## Installing the discovery skill

Vercel's `skills` CLI already installs skills from GitHub into recognized
locations for Claude Code, Codex, GitHub Copilot, and other hosts. It supports
project or user scope and either symlinks or copies. [5]

Once our repository and skill exist, an installation could look like this.

```bash
npx skills add robotdad/amplifier-tools-smart-catalog \
  --skill discover-smart-tools \
  --agent claude-code codex github-copilot
```

This is the planned repository name, not a claim that the repository or skill
has been published. The default is project scope. Adding `--global` selects
user scope.

Amplifier is not listed as a target in the installer documentation we reviewed.
The listed product named Amp is different. Initially, we can place the same
skill in `.amplifier/skills/` and use a bundle with the skills capability enabled.
Each host still needs a check that it actually discovers the installed skill.

Installing this skill does not install tmux, DTU, their runtime dependencies,
or model credentials.

## Boundaries the skill must preserve

**Catalog availability is not runtime readiness.** A tool can be listed but
not installed, installed but missing prerequisites, or usable only for its
non-AI commands. The skill should report those distinctions.

**Discovery is not permission to act.** Reading a manifest, installing code,
sending input to a live tmux session, and launching or destroying a container
are different actions. The host's authorization rules still apply. Metadata
from a repository is input to inspect, not authority to bypass those rules.

**The execution environment matters.** A local agent may be able to reach tmux
or Incus while a sandboxed or cloud agent cannot. We are starting with local
coding CLIs, not promising access to a laptop from a cloud agent.

**Embedded AI has its own setup.** The reference tools document provider API
credentials. We have not established reuse of Claude Code or Codex subscription
credentials.

**Cleanup belongs to the workflow.** DTU environments persist until explicitly
destroyed. A caller must track what it creates rather than clean up unrelated
environments.

## What I would leave out

- Per-tool skills.
- An MCP gateway or generated MCP wrappers.
- A new plugin marketplace.
- A hand-maintained top-level inventory or copied tool manifests.
- Whole-machine scanning or a background registry service.
- Automatic installation merely because a tool appears relevant.

Skills give us a distribution route for this first experiment. Existing plugin
and MCP models remain options if actual use shows a gap they would solve.

## What would make the experiment convincing

Before running it, agree on the acceptance criteria. My proposed first check is
a fresh local coding-agent session with only the discovery skill installed.

Ask it to inspect tmux sessions or assess whether the machine is ready for DTU.
It should find the appropriate catalog entry, learn the invocation from the
tool, and complete a read-only operation without manually supplied per-tool
instructions.

Repeat that in the other target hosts. Include a missing-tool case and a
missing-prerequisite case. A useful result is either a correct operation or a
clear explanation of what prevents it, without unauthorized installation or
mutation.

Record where the agent needed extra help. That evidence should determine
whether we improve the skill, improve the tool's self-description, or add
infrastructure.

## Questions for review

- Who curates additions to the folder-based inventory?
- Should the initial tmux and DTU entries pin the inspected commits or use the
  supported default of floating on `main`?
- Which host should we use for the first read-only trial?

## Sources

Repository findings are from static inspection. Host installation behavior has
not been verified end to end.

1. [Smart Tools roadmap](https://github.com/microsoft/amplifier-smart-tools/blob/fd3c63416d1c9b0eb6e55981b248d1b2b5c64452/ROADMAP.md#L24-L59)
   leaves host integration and registry discovery open.
2. [Packaging](https://github.com/microsoft/amplifier-smart-tools/blob/fd3c63416d1c9b0eb6e55981b248d1b2b5c64452/spec/packaging.md#L27-L55)
   defines the descriptor.
   [Invocation](https://github.com/microsoft/amplifier-smart-tools/blob/fd3c63416d1c9b0eb6e55981b248d1b2b5c64452/spec/invocation.md#L28-L50)
   describes the manifest/help split.
   [Manifest ownership](https://github.com/microsoft/amplifier-smart-tools/blob/fd3c63416d1c9b0eb6e55981b248d1b2b5c64452/spec/manifest.md#L3-L10)
   keeps the authoritative description in the tool's source.
3. [tmux reference implementation](https://github.com/microsoft/amplifier-smart-tool-tmux/tree/9a4a167101c92b803f7a693e6614a21a6d21cf5b).
4. [DTU reference implementation](https://github.com/microsoft/amplifier-smart-tool-digital-twin-universe/tree/4c2e0934126615460ada61ad0fb87f8b96dc81ed).
5. [Skills installer documentation](https://github.com/vercel-labs/skills#readme),
   reviewed September 9, 2026. Supported hosts and installation behavior can change.