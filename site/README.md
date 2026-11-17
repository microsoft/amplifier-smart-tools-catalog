# Website

This repository's promotional page uses the Amplifier Smart Tools family theme.
Product page content lives in `site.json`. The canonical theme is maintained in
`microsoft/amplifier-smart-tools/site/theme`; this repository carries a versioned
copy so a build does not depend on a moving remote theme or an online service.
Theme version: 0.3.0. Theme code is MIT licensed.

## Build and preview

From the repository root, using Python 3.12 or later:

```sh
python3 -m venv .work/site-venv
.work/site-venv/bin/python -m pip install -r site/requirements.txt
.work/site-venv/bin/python site/theme/build.py --family-owner robotdad
python3 -m http.server 8000 --directory _site --bind 127.0.0.1
```

Open http://127.0.0.1:8000. Generated output belongs in `_site/` and is ignored.
The site is a static build; visitors need no Python runtime or account.

The `--family-owner robotdad` option points overview and catalog links at the
fork previews. Omit it for their Microsoft organization URLs. Individual tool
links retain their authors' owners. Keep the same setting across the family.
For a combined local preview, build each page with `--local --output` into a
shared preview directory named after its repository, then serve that directory.

## GitHub Pages

The Website workflow builds a `github-pages` artifact for relevant pull requests and retains it for seven days. See the root [preview instructions](../README.md#review-a-website-preview) for downloading the exact run's `artifact.tar` and serving the static build. Pull requests never deploy.

On main, relevant pushes build and publish automatically. Either success or failure of a trusted Refresh Amplifier Smart Tools manifests run on main also triggers a validated build and publish from current main, including successful entry updates committed during a partially failed refresh. The workflow never consumes triggering-run code or artifacts. Metadata validation belongs to the canonical renderer and is also run by CI through `scripts/validate_catalog.py`.

The existing GitHub Actions Pages setup and main environment policy remain unchanged. Manual publication is restricted to main; other revisions are preview-only. All linked family sites must be published before cross-site navigation is live.

## Shared identity

Use the full family name, Amplifier Smart Tools, as one masthead and footer
identity. The overview explains the format and how to build a tool; discovery
and individual tool listings belong in the catalog.

Use plain punctuation. The footer credit, "Developed by made at Microsoft", is the
only attribution. Do not link to the internal team site. Preserve the shared navigation,
layout, typography, paper background, and gold details; a tool may set its own
accent, content, and image in `site.json`.

Images are copied from the repository's existing `docs/images/` at build time.
Their existing provenance remains there. Screenshots are labeled as screenshots;
concept artwork is labeled as illustration. Add demo video only when reviewed
footage is available. Do not use a fake player over a still image.

To update a vendored theme, run the canonical `site/sync_theme.py` with an explicit
target checkout, review the diff, and build again. It updates only `site/theme/`.
Page content stays in the owning repository. The family link registry holds only
navigation identity; the catalog's tool inventory remains `tools/*/source.json`.

## Site text

`site/theme/text.yaml` holds the wording of the catalog page and the tool pages. It is
part of the shared theme, so change it in the canonical theme and sync it here. A tool's
name, description, and use cases come from its own manifest, and category names come from
`categories.json`.

## Graphics and fonts

`site/theme/graphics.py` draws the family mark, line icons, and one glyph per tool,
all as inline SVG. A tool's glyph and field color are keyed by its catalog slug; a
tool without a glyph shows its initial on a neutral field. Reality Check, Smart Tool
Creator, and Digital Twin Universe have their own artwork: a line drawing with one
pastel part on an ink tile.

Instrument Sans, Geist Mono, and Pirata One ship in `site/theme/assets/fonts/` with
their Open Font License texts and are included by the theme sync script.

## Markdown copies and llms.txt

The build follows the [llms.txt](https://llmstxt.org/) proposal so an agent can read the
catalog without parsing HTML. `llms.txt` at the site root lists every tool by category,
with the recommended tools first. Each link goes to the tool's Markdown copy at
`tools/<slug>/index.md`, which holds its description, facts, install prompt, and use
cases. A tool page names its copy in a `rel="alternate"` link, and every page names
`llms.txt` in a `rel="describedby"` link.

## Catalog categories and Recommended

The catalog uses the flat `categories.json` taxonomy and each listing's optional
primary `category`. Keep category IDs stable and expose labels and scopes without
turning categories into a hierarchy. Ordinary listings and tools without classification remain available.

Submissions are source-only and category-agnostic: submitters do not add, choose, or create categories or recommendations and need not know category definitions. Maintainers assign classification from the approved registry in separate metadata, never upstream manifests or source pointers. Category additions, label changes, and scope changes require their separate review and approval. A maintainer-owned ordinary listing is `{"category": "approved-id"}`. The required category must be known; optional `recommended` defaults to false in a normalized copy in memory without mutating input or rewriting files. A provided flag must be a strict boolean. True requires the full selected `reviewed_source`; false or omission prohibits it.

Each tool's catalog page shows its category as a fact. Effective recommendations carry a "Recommended" label in the All tools list and a "Recommended" label on the tool's page; designations needing review show "Recommendation needs review" in both places. Ordinary listings have no recommendation mark. Tools without listings show the category Other. Other is a built-in fallback grouping, not a registry category. Tools without classification automatically appear there and remain searchable by Name and Category. They remain readable without snapshots or JavaScript.

See the root [category table](../README.md#categories-and-recommendations) for coverage; category scopes remain in `categories.json`. Missing classification is valid for source-pointer contributions.

Explain “Recommended” as a maintainer-curated preference for a category, bound to a selected source repository and distribution path, under the [maintainer guide](../docs/maintainers.md). It is not certification, guaranteed outcomes, or proof of local readiness. Catalog metadata tests do not establish tool quality or completed evaluation.

Keep Recommended separate from All tools. Render each effective recommendation once as a card in Recommended and once as a row in All tools. All tools includes every unique listing. Omit the Recommended section when no designation is effective, and hide it while a search or category is active. Do not render a Recommended empty-state message or explanation link. The marks are static, not controls.

Retain the `reviewed_source` field name for schema compatibility: it records selected source identity, not proof of conformance or task results. Repository or distribution path drift removes recommendation preference without removing the category or listing. The stale designation still occupies its category's slot.

Render Recommended before All tools. List all unique listings in All tools in name order. Each row shows the icon, name, first sentence of the manifest description, and Get. Search matches tool names, descriptions, use cases, platforms, and category labels.

Put Search and one row of category chips above all results. Show a chip only for a category that holds a tool, and the Other chip only when an entry lacks classification. Do not display category scope text; keep scope metadata in the registry. At phone widths the chips scroll sideways in one row. When nothing matches, show one empty message with a Clear search action.

Search and chips remain hidden without JavaScript so all unique listings stay visible in All tools, alongside the Recommended cards. A status for screen readers reports the number of matching unique listings.

Get, a row's name, and a card open the tool's catalog page at `tools/<slug>/`, or the tool's own website when it is recommended and has one in `family.json`. The catalog page shows the icon, name, one line of facts, first sentence, an install prompt for an agent, up to six use cases, and other tools in the same category.

Keep review evidence free of credentials and private details. Preserve public
source URLs and exact generated manifests. Implement shared rendering and
metadata changes in the canonical theme, then sync; never patch the vendored
copy independently.
