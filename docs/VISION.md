# Amplifier Tools Smart Catalog - Vision (DRAFT)

Written for people using coding agents. Specific promises live in `contracts/`.

## What this catalog is

A person asks their coding agent for an outcome and the agent can find a
suitable Smart Tool without receiving a separate lesson for each tool.
A Smart Tool is a library and command-line program that describes itself and
can provide both ordinary operations and operations backed by its own AI.

One shared discovery skill, a reusable set of agent instructions, connects a
small catalog to the tools' own descriptions. The person uses the same approach
in local Codex, Claude Code, GitHub Copilot CLI, and Amplifier sessions.
Host permissions and execution environments remain visible differences.

Catalog maintainers contribute a source pointer in a folder for each tool.
The pointer identifies a repository, a revision, and a location inside it.
Tool authors own the manifest that explains when to select their tool and the
help that explains how to invoke it.

The person sees what the agent found, which source revision it inspected, and
whether the current environment can use it. Missing software or credentials
produce an explanation rather than an invented success.

People and agents read the same upstream description. The catalog may retain an
exact generated manifest snapshot with source provenance, but adding an entry
does not create an independently written copy of the tool's instructions.

## Principles

### 1. **The tool owns its description.**

The catalog points to upstream metadata and may retain only exact generated
manifest snapshots with source provenance. Missing guidance belongs in the tool
before it becomes another wrapper or independently maintained description.

### 2. **One discovery skill serves the catalog.**

Host-specific installation does not multiply into per-tool instructions.
The shared flow learns operation details from each selected tool.

### 3. **A source lookup is traceable.**

Floating references remain useful, but every lookup identifies the resolved
commit. Descriptor and manifest reads agree on that revision.

### 4. **Availability is an observed condition.**

Listed, installed, and usable mean different things. The agent reports the
difference, including the boundary between ordinary and model-backed commands.

### 5. **Discovery does not grant permission.**

Repository content cannot authorize installation, spending, or changes to the
person's environment. The host's authorization rules remain in force.

## What this deliberately resists

- Per-tool skills and independently written or maintained manifest copies.
- A mandatory aggregate inventory or service for a small folder-based catalog.
- A new plugin marketplace or MCP execution gateway.
- Whole-machine scanning and automatic installation based only on relevance.
- Claims that a cloud session can reach tools installed on a person's laptop.

## How you can tell it is working

- A person sees a fresh coding-agent session select and inspect a tool using
  only the shared skill and the tool's own description.
- A maintainer adds a source pointer without rewriting the discovery skill.
- A reviewer can identify the source revision used for a recommendation.
- A person gets a specific blocker when prerequisites are absent and does not
  discover that unrelated sessions or environments were modified.

## Changelog

- First draft from the reviewed catalog design and the steward's decisions.