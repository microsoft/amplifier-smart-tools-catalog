# Amplifier Smart Tools Catalog

[Website](https://microsoft.github.io/amplifier-smart-tools-catalog/)

A catalog and one shared skill for finding Amplifier Smart Tools from your
coding agent. Browse [the catalog](tools/) or install the
[discovery skill](skills/amplifier-smart-tools-catalog/SKILL.md).

## Install the skill

For Claude Code, Codex, and GitHub Copilot, name the agents directly.

```bash
npx skills add microsoft/amplifier-smart-tools-catalog \
  --skill amplifier-smart-tools-catalog \
  --agent claude-code codex github-copilot
```

Keep only the agents you use, such as `--agent codex` for Codex alone.
Run this from your project, or add `--global` to make the skill available across
projects. Adding the skill does not install Smart Tools or configure credentials.

<details>
<summary>Optional installation details - interactive setup, defaults, and local sources</summary>

If you prefer to choose through prompts, omit `--agent`.

```bash
npx skills add microsoft/amplifier-smart-tools-catalog
```

The CLI detects installed agents and guides you through target selection and
setup. Omitting `--agent` does not mean installing to every supported agent.

Specifying `--agent` skips agent selection, but other setup prompts may remain.
Add `--yes` to accept the remaining defaults without prompts.
For a local checkout, replace the repository argument with its directory path.

</details>

<details>
<summary>Installing in Amplifier</summary>

Amplifier is not a target supported by the skills CLI.
The Amplifier App CLI already provides Skills. Add the catalog behavior
persistently with:

```bash
amplifier bundle add 'git+https://github.com/microsoft/amplifier-smart-tools-catalog@main#subdirectory=behaviors/smart-tools-catalog.yaml' --app
```

This is user-wide and composes the behavior into every new Amplifier session;
it does not select the behavior as a root bundle. Other Amplifier hosts must
already compose Skills. The App CLI needs no separate skills-capability enable
step.

The metadata-only `bundle.md` lets Foundation recognize this Git repository as
a bundle source; it does not provide a runnable host.

Start a new session with `amplifier`, use `/skills` to confirm discovery, then
ask naturally for a Smart Tool for the task. Adding the discovery skill does
not install Smart Tools or configure credentials.

The behavior's remote skill tracks the catalog's `main` independently of a
revision pin on the behavior URI. For a controlled version instead, manually
copy or link the existing `skills/amplifier-smart-tools-catalog/` folder from a
pinned checkout into `.amplifier/skills/` or `~/.amplifier/skills/`; normal
Amplifier skill discovery needs no enable step.

</details>

## Use the skill

Ask your agent to find a Smart Tool for a task or explain how to install one.
You can also ask for help creating a Smart Tool or adding one to the catalog.

The skill normally reads the catalog from GitHub. If you want it to use a local
catalog checkout instead, explicitly give the host that path.

## Update the skill

For a project installation, run this from that project.

```bash
npx skills update amplifier-smart-tools-catalog -p
```

Start a fresh coding-agent session after updating so it loads the new instructions.

<details>
<summary>Other update options - global scope and Amplifier</summary>

For a user-wide installation, use global scope.

```bash
npx skills update amplifier-smart-tools-catalog --global
```

Without a scope flag, `npx skills update amplifier-smart-tools-catalog` prompts
for scope.

For an Amplifier App CLI behavior installation, run:

```bash
amplifier update
```

Then start a fresh `amplifier` session. This can refresh other eligible
Amplifier sources as well, so it is not a catalog-only update.

For a manually copied or linked skill, update the source checkout to the
revision you want. Copy the skill again if needed; a symlink reads that checkout.

To stop composing the behavior into future App CLI sessions, run:

```bash
amplifier bundle remove 'git+https://github.com/microsoft/amplifier-smart-tools-catalog@main#subdirectory=behaviors/smart-tools-catalog.yaml' --app
```

Removal unregisters future composition; it does not uninstall Smart Tool
programs or promise deletion of a cached remote skill. Use the same URI you
registered if you chose a different revision.

Skill updates are separate from catalog refreshes. The GitHub Action refreshes
catalog snapshots; updating the skill gets changes to the discovery instructions.

</details>

## Catalog details

<details>
<summary>How source pointers and automatic refresh work</summary>

Each `tools/<slug>/source.json` points to an upstream repository. Optional `ref`
selects a branch, tag, or commit and defaults to `main`. Optional `path` selects
the tool's distribution root and defaults to the repository root.

The refresh action generates exact `SMART_TOOL.md` snapshots and provenance
after source changes reach `main`, daily, and on manual dispatch. Changes to
the refresh implementation also trigger it.

Tools own their manifests and usage help. The skill reads the snapshots first
and follows upstream guidance when needed. A recorded refresh time says when
the last refresh succeeded, not that the snapshot is currently fresh. Failed
source refreshes preserve the previous snapshot and appear in the action logs.

This repo does not provide an installer or validation kit.
Remote skill installation and a read-only workflow using an explicitly supplied
local catalog have been exercised in an isolated Amplifier App CLI environment.
Other coding hosts remain unverified.

</details>

## Product direction

- [Vision](docs/VISION.md)
- [Catalog source contract](contracts/catalog-source.v1.md)
- [Discovery contract](contracts/discovery.v1.md)

## Contributing

Submit catalog pull requests with source pointers only: add or update
`tools/<slug>/source.json` and do not hand-copy generated `SMART_TOOL.md` or
`provenance.json` files. After a source pointer merges to `main`, the refresh
workflow generates snapshots and provenance.

This project welcomes contributions and suggestions. Most contributions require
you to agree to a Contributor License Agreement (CLA) declaring that you have
the right to, and actually do, grant us the rights to use your contribution.
For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether
you need to provide a CLA and decorate the PR appropriately (for example, with
a status check or comment). Simply follow the instructions provided by the bot.
You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](CODE_OF_CONDUCT.md).
For more information, see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/)
or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with questions
or comments. See [SECURITY.md](SECURITY.md) to report vulnerabilities.

## Trademarks

This project may contain trademarks or logos for projects, products, or
services. Authorized use of Microsoft trademarks or logos is subject to and
must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must
not cause confusion or imply Microsoft sponsorship. Any use of third-party
trademarks or logos is subject to those third-party's policies.

## License

[MIT](LICENSE)