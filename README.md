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

### Categories and recommendations

The catalog owns a flat category registry in [`categories.json`](categories.json), with stable IDs, labels, and scopes. Maintainer-owned optional `tools/<slug>/listing.json` files assign at most one primary approved category and may record a recommendation for a selected source repository and distribution path. The ordinary form is `{"category": "approved-id"}`: an omitted `recommended` defaults to false without rewriting the file. A provided flag must be boolean; true requires the full selected `reviewed_source`, while false or omission prohibits it. Missing listing metadata means listed under Other and not recommended. Other is a built-in fallback grouping, not a registry category. Tools without classification automatically appear there and remain searchable by Name and Category. Ordinary listings remain available; they are not rejected or unapproved.

Classifications are based on the work described in the exact, commit-pinned public manifests, not repository names.

Classification and recommendation are not completed tool evaluations. Source-pointer contributions may omit classification; those tools appear under Other until maintainers assign a category.

| Category | Tools | Current listings |
|---|---:|---|
| Test environments | 1 | `digital-twin-universe` |
| Smart Tool development | 1 | `smart-tool-creator` |
| Research & knowledge | 5 | `deep-research`, `fact-check`, `hacker-news`, `lore`, `team-pulse` |
| Audio, video & animation | 5 | `aud`, `vid`, `outtake`, `unfold`, `showrun` |
| Presentations & documents | 1 | `stories` |
| App design & developer tools | 4 | `possibly`, `fast-decisions`, `github-repos`, `tmux` |
| Email, calendar & work preparation | 2 | `gmail`, `workiq` |
| Music & playlists | 2 | `music-deck`, `spotify` |
| Smart home | 1 | `home-assistant` |

Digital Twin Universe is Recommended for Test environments and Smart Tool Creator for Smart Tool development. Each selected source repository and distribution path is recorded in the tool's `listing.json`. All other listings are ordinary. These designations record maintainer-curated preference, not completed conformance reviews or task evaluations.

“Recommended” means a maintainer-curated preference for a tool in a category, bound to a selected source repository and distribution path. It is not certification, a guarantee of outcomes, or a claim that the tool is installed or ready on this machine. It does not authorize installation, execution, spending, or access to secrets. The tool's own manifest still determines whether it fits the request. Catalog metadata tests check structure and source identity, not tool quality or completed evaluation.

A recommendation is effective only when its selected repository and distribution path agree with the source pointer and snapshot provenance. It follows the tracked ref, so a newer upstream commit keeps it effective. The field name `reviewed_source` is retained for schema compatibility: it records selected source identity, not proof of conformance or task results. When identities no longer agree, the entry keeps its category and designation but shows “Recommendation needs review” instead of an effective recommendation. It loses recommendation preference until maintainers explicitly select a source and initiate renewal. A stale designation still occupies the category's one recommendation slot. Refresh time and recorded revision describe a past snapshot, not current tool health. Record actual checks separately, only when run, under the [maintainer guide](docs/maintainers.md#evaluation-practice).

The website places effective recommendations in a distinct Recommended region above All tools. Each effective recommendation appears once as a featured shortcut and once in the complete All tools list. The global and All tools counts are based on unique listings, not the rendered card count. One control bar sits above all results, with Search, Category, Platform, Sort by (Category or Name), and Clear filters. Search, category, and platform filter both copies; sorting changes only All tools. Category scopes remain registry metadata and are not inserted into the controls when a category is selected. The Other option and group appear only when an entry lacks classification. Every card retains its category label; ordinary cards have no recommendation-status badge, and featured shortcuts rely on their section heading instead of a repeated badge. The Recommended region is hidden when no effective recommendations match. When nothing matches, one global empty message replaces section-specific messages. Without JavaScript, the control bar and Name list stay hidden, all unique listings remain visible in All tools alongside the featured shortcuts, and a zero-card Recommended region starts hidden. Future tools without classification or snapshots remain readable under Other without JavaScript. All tools remain grouped under noninteractive category headings, with no separate category navigation.

## Product direction

- [Vision](docs/VISION.md)
- [Catalog source contract](contracts/catalog-source.v1.md)
- [Discovery contract](contracts/discovery.v1.md)

## Maintainer curation

Only catalog maintainers select and initiate recommendations. Implement an explicit maintainer selection by setting `recommended: true` with its selected source identity; do not infer completed validation from the selection. Curation is separate from ordinary listing contributions; roles, suggested evaluation practice, category review, and metadata procedures live in the [maintainer guide](docs/maintainers.md).

## Contributing

1. Add or update `tools/<slug>/source.json` to point to the tool's public upstream distribution.
2. Run the [contribution checks](#check-a-contribution) and submit a pull request with only the source pointer.

Submissions are category-agnostic. Submitters do not add, choose, or create categories or recommendations and do not need to know category definitions. Maintainers assign classification from the approved registry; category additions, label changes, and scope changes require their separate review and approval. Tools without classification automatically appear under Other and remain searchable by Name and Category.

Listing or contributing a tool is not a recommendation nomination. Do not solicit recommendation requests or proposals from authors. Do not hand-copy or hand-edit generated `SMART_TOOL.md` or `provenance.json` files. After a source pointer merges to `main`, the refresh workflow generates snapshots and provenance. Never add classification or recommendation fields to `source.json` or upstream manifests.

### Check a contribution

Use Python 3.12 or later with `site/requirements.txt` installed in your workspace virtual environment, as in the [site build instructions](site/README.md#build-and-preview). The full tests exercise snapshot rendering and require PyYAML. From the repository root, with that environment active:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_catalog.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

The CLI and website build use the same validator in the versioned canonical theme. Do not add a separate schema or a second implementation here. Metadata validation does not evaluate tool quality or prove the selection and initiation policy has been enforced.

### Review a website preview

The Website workflow uploads a `github-pages` artifact for relevant pull requests, retained for seven days. Pull requests do not deploy. Open the exact Website run for the pull request and confirm its revision before downloading its artifact; do not choose the latest run by accident.

With GitHub CLI installed, replace the run ID below with that exact run. Choose a temporary directory under a preview parent you control; this example keeps it in the checkout's ignored `.work/` directory.

```sh
RUN_ID='<exact Website run ID>'
PREVIEW_PARENT="$PWD/.work"
mkdir -p "$PREVIEW_PARENT"
PREVIEW_DIR="$(mktemp -d "$PREVIEW_PARENT/catalog-preview.XXXXXX")"
gh run download "$RUN_ID" --repo microsoft/amplifier-smart-tools-catalog --name github-pages --dir "$PREVIEW_DIR/download"
mkdir "$PREVIEW_DIR/site"
tar -xf "$PREVIEW_DIR/download/artifact.tar" -C "$PREVIEW_DIR/site"
PYTHONDONTWRITEBYTECODE=1 python3 -m http.server 8000 --bind 127.0.0.1 --directory "$PREVIEW_DIR/site"
```

`gh run download` extracts the artifact's outer ZIP into `download/`; the remaining `artifact.tar` contains the site files directly, so no extra `_site/` prefix is needed when serving `site/`.

Open `http://127.0.0.1:8000` to inspect the static build. That address is only a local serving address, not source provenance or a public deployment. The source revision is the one shown on the selected GitHub run. The Actions UI also offers the same `github-pages` download as a ZIP containing `artifact.tar`; extract the ZIP into the chosen download directory before using the tar command.

The refresh workflow pushes its snapshot commit with a deploy key, so the push starts the Website workflow, which rebuilds and publishes `main`. This includes a refresh that commits successful entries before it reports another entry's failure, so a failure does not leave an outdated recommendation badge published. The workflow never deploys untrusted pull-request content. Manual publication is restricted to `main`; other revisions are preview-only.

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
