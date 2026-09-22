# Amplifier Smart Tools Catalog

A catalog of [Amplifier Smart Tools](https://github.com/microsoft/amplifier-smart-tools).
Browse [the catalog](tools/) or the [website](https://microsoft.github.io/amplifier-smart-tools-catalog/).

## Use the catalog from your agent

Install the [Amplifier Smart Tools skill](https://github.com/microsoft/amplifier-smart-tools/blob/main/skills/amplifier-smart-tools/SKILL.md).
It reads this catalog to find and install tools, drives them through their own
help, and covers creating a tool and adding it here.

```bash
npx skills add microsoft/amplifier-smart-tools
```

Then ask your agent for a Smart Tool for the task. The skill normally reads the
catalog from GitHub; to use a local checkout instead, give your agent that path.
Adding the skill does not install Smart Tools or configure credentials.

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
