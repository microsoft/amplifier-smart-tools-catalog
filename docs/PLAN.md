# Bootstrap decisions and validation plan (DRAFT)

## State

This is direction preparation, not implementation work breakdown.
No skill, catalog entries, runtime, validation kit, queue, or lanes exist.
The repository is local on main. GitHub visibility is pending.

## Investigation and evidence

The prospective local path was absent. GitHub lookup returned 404 for
`robotdad/amplifier-tools-smart-catalog` while authenticated as robotdad.
No ancestor `WORKSPACE-MANIFEST.json` exists, so this repository is its own
workspace. Unrelated sibling repositories are outside its scope.

The reviewed design is preserved in `docs/designs/smart-tools-discovery-review.md`.
It is a bootstrap snapshot, not a second contract. Later decisions live in the
vision and relevant contract, with this plan recording their status.

## Decision record

The conversation established these choices before bootstrap.

- Marc chose `robotdad/amplifier-tools-smart-catalog`.
- One skill discovers all tools. No per-tool skills, gateway, or local service.
- One folder per tool contains `source.json`; there is no top-level inventory.
- Descriptions remain upstream, not copied into the catalog.
- HTTPS repository URL is required. Optional ref defaults to main, optional
  distribution path defaults to the repository root.
- Branches and tags resolve once per lookup, with same-commit metadata reads
  and a reported resolved SHA.
- Start with the Microsoft tmux and DTU reference implementations.

Two draft contracts separate consumers with different needs. Catalog
contributors depend on source interpretation; host users depend on discovery,
readiness reporting, and authorization boundaries. This is document structure,
not a decision to build separate components.

## Review before work breakdown

1. Review the vision and the two draft contracts against the agreed design.
2. Settle missing input-validation rules and catalog access from an installed
   skill. Proposed direction is strict invalid-input handling and safe paths,
   but no detailed policy has been ratified.
3. Choose initial entry revisions. Recommendation is inspected commit pins for
   the first trial, while preserving floating main support in the format.
4. Approve trial correctness, host order, and budget before executing candidates.
5. Only after direction approval, seed honest contract checks and derive work
   from the gaps. There is no task queue to execute before that gate.

Draft approval is not evidence that a contract is ready to lock.
Locking requires the Converge freeze bar, including working checks and real
implementation evidence, rather than a status edit on a blank project.

## Proposed validation

The first trial is read-only. It asks a fresh local coding host to discover
tmux inspection or DTU readiness from the installed shared skill.
Success means the agent reads the source metadata and installed help, records
the source revision, and returns either the correct observation or an accurate
blocker without unapproved installation or mutation.

Include missing executable, missing prerequisite, invalid source, pinned commit,
moving branch, and hostile metadata cases. Separate deterministic source checks
from host-session trials. Record what was checked and what remains unverified.

Repeat the shared flow across the target local hosts. A missing host is a
coverage gap, not a pass. Do not test destructive operations on user resources.
Operational test design follows the approved rubric, not the other way around.

## Publication

Public/private visibility remains Marc's decision. No remote is created or
content published until that choice lands. Licensing is not selected yet.

## Resume

Read the latest owner return log, then this plan and the draft contracts.
Manager state lives in `.converge/smart_tools_catalog/`. No tracker project has
been provisioned and no lane launch needs recovery.