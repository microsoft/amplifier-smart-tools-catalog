"""Exercise the canonical validator against catalog fixtures and real classifications."""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import re
import sys
import tempfile
import unittest
from collections import Counter
from collections.abc import Iterator
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import patch
from urllib.parse import quote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "site" / "theme"))
from catalog_metadata import (
    catalog_sources,
    load_catalog_metadata,
    read_json,
    read_snapshot,
    recommendation_state,
    validate_listing,
    validate_pointer,
)


CATEGORY = {"id": "test-environments", "label": "Test environments", "scope": "Isolated testing."}
IDENTITY = {"repository": "https://example.test/tool.git", "path": "."}
COMMIT = "a" * 40
# Synthetic source identity is test-only, never evidence of an actual evaluation.
LISTING = {"category": CATEGORY["id"], "recommended": True, "reviewed_source": IDENTITY}
# Maintainer classifications that must survive refresh. New sources may remain
# unclassified, and later classifications need not be added here.
CURRENT_CLASSIFICATIONS = {
    "test-environments": ("digital-twin-universe",),
    "builder-tools": ("reality-check",),
    "smart-tool-development": ("smart-tool-creator",),
    "research-knowledge": ("deep-research", "fact-check", "hacker-news", "lore", "team-pulse"),
    "media-production": ("aud", "vid", "outtake", "unfold", "showrun"),
    "presentations-documents": ("stories",),
    "developer-tools": ("possibly", "fast-decisions", "github-repos", "tmux"),
    "workplace-productivity": ("gmail", "workiq"),
    "music-listening": ("music-deck", "spotify"),
    "home-automation": ("home-assistant",),
}
# Selected sources are maintainer data in listing.json and follow the tracked ref.
CURRENT_SELECTIONS = {
    "digital-twin-universe": {
        "repository": "https://github.com/microsoft/amplifier-smart-tool-digital-twin-universe.git",
        "path": ".",
    },
    "reality-check": {
        "repository": "https://github.com/microsoft/amplifier-smart-tool-reality-check.git",
        "path": ".",
    },
    "smart-tool-creator": {
        "repository": "https://github.com/microsoft/amplifier-smart-tool-creator.git",
        "path": ".",
    },
}
SITE = json.loads((ROOT / "site" / "site.json").read_text(encoding="utf-8"))
ARGS = SimpleNamespace(local=False, family_owner="microsoft")
CATALOG_URL = "https://microsoft.github.io/amplifier-smart-tools-catalog/"
VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})
UNCLASSIFIED = "__unclassified__"
NO_SNAPSHOT = "No manifest snapshot is available yet."
ALL_CHIP = ("", "All", "true")
OTHER_CHIP = (UNCLASSIFIED, "Other", "false")
CATEGORY_CHIP = (CATEGORY["id"], CATEGORY["label"], "false")
# Labels a row carries beyond its name and sentence, as (element holding it, class, text).
MARKS = {
    "recommended": [("app-row-name", "tag", "Recommended")],
    "needs-review": [("div", "tag", "Recommendation needs review")],
    "ordinary": [],
}
PILLS = {
    "recommended": ["Recommended"],
    "needs-review": ["Recommendation needs review"],
    "ordinary": [],
}


def tool_count(count: int) -> str:
    return f"{count} tool" if count == 1 else f"{count} tools"


def get_started(source_url: str) -> str:
    """All the text of a tool page's get-started section: its heading, hint, and one prompt."""
    return (
        "Get started. Your agent installs the tool and reads its help. "
        f"Ask your agent. Prompt Copy Go to {source_url} and install it."
    )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


class Element:
    """One rendered element with its attributes, children, and place in the page."""

    def __init__(self, tag: str, attrs: dict[str, str | None], parent: Element | None = None) -> None:
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Element | str] = []

    @property
    def classes(self) -> list[str]:
        return (self.attrs.get("class") or "").split()

    @property
    def text(self) -> str:
        # A tool without its own glyph draws a letter inside svg; that is art, not copy.
        parts = [
            child if isinstance(child, str) else child.text
            for child in self.children
            if isinstance(child, str) or child.tag != "svg"
        ]
        return " ".join(" ".join(parts).split())

    def ancestors(self) -> Iterator[Element]:
        element = self.parent
        while element is not None and element.tag:
            yield element
            element = element.parent

    def descendants(self) -> Iterator[Element]:
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.descendants()

    def select(self, tag: str, class_name: str = "", identity: str = "") -> list[Element]:
        return [
            element
            for element in self.descendants()
            if element.tag == tag
            and (not class_name or class_name in element.classes)
            and (not identity or element.attrs.get("id") == identity)
        ]

    def one(self, tag: str, class_name: str = "", identity: str = "") -> Element:
        found = self.select(tag, class_name, identity)
        assert len(found) == 1, f"Expected one <{tag}> ({class_name or identity}), found {len(found)}"
        return found[0]

    def identities(self) -> Counter[str]:
        return Counter(
            element.attrs["id"] for element in self.descendants() if element.attrs.get("id")
        )


class PageParser(HTMLParser):
    """Build the element tree of rendered markup, not of source code."""

    def __init__(self) -> None:
        super().__init__()
        self.root = Element("", {})
        self.current = self.root

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        element = Element(tag, dict(attributes), self.current)
        self.current.children.append(element)
        if tag not in VOID_TAGS:
            self.current = element

    def handle_startendtag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        self.current.children.append(Element(tag, dict(attributes), self.current))

    def handle_endtag(self, tag: str) -> None:
        element = self.current
        while element.parent is not None and element.tag != tag:
            element = element.parent
        if element.parent is not None:
            self.current = element.parent

    def handle_data(self, data: str) -> None:
        self.current.children.append(data)


def parse(document: str) -> Element:
    parser = PageParser()
    parser.feed(document)
    parser.close()
    return parser.root


@dataclass(frozen=True)
class Listed:
    """What one catalog row or featured card tells a reader about a tool."""

    slug: str
    category: str
    search: str
    name: str
    tagline: str
    links: list[str]
    get_label: str | None
    marks: list[tuple[str, str | None, str]]
    text: str


def named(element: Element) -> str:
    """Name an element by its class, or by its tag when it has no class."""
    return element.attrs.get("class") or element.tag


def listed(article: Element) -> Listed:
    title = article.one("h3").one("a")
    get = article.one("a", "get")
    return Listed(
        slug=article.attrs["data-tool"] or "",
        category=article.attrs.get("data-category") or "",
        search=article.attrs.get("data-search") or "",
        name=title.text,
        tagline=article.one("p").text,
        links=[title.attrs["href"] or "", get.attrs["href"] or ""],
        get_label=get.attrs.get("aria-label"),
        marks=[
            (named(span.parent or article), span.attrs.get("class"), span.text)
            for span in article.select("span")
            if "app-icon" not in span.classes
        ],
        text=article.text,
    )


class CatalogPage:
    """Read the rendered catalog index: category chips, featured cards, rows, and count."""

    def __init__(self, document: str) -> None:
        self.root = parse(document)
        self.chips = [
            (chip.attrs["data-category"], chip.text, chip.attrs["aria-pressed"])
            for group in self.root.select("div", identity="category-chips")
            for chip in group.select("button", "chip")
        ]
        self.featured = [
            listed(card)
            for section in self.root.select("section", identity="featured")
            for card in section.select("article", "tool-card")
        ]
        self.rows = [
            listed(row) for row in self.root.one("div", "app-list").select("article", "app-row")
        ]
        self.count = self.root.one("span", identity="result-count").text


def parts(element: Element) -> list[str]:
    """Name each child element by its class, or by its tag when it has no class."""
    return [named(child) for child in element.children if isinstance(child, Element)]


def section_name(section: Element) -> str:
    headings = section.select("h2")
    return section.attrs.get("id") or (headings[0].text if headings else " ".join(section.classes))


class ToolPage:
    """Read a tool's own page: layout, status, facts, use cases, prompt, and every link."""

    def __init__(self, document: str) -> None:
        self.document = document
        self.root = parse(document)
        main = self.root.one("main")
        head = main.one("section", "store-head")
        started = main.one("section", identity="get-started")
        self.title = self.root.one("title").text
        self.text = self.root.one("body").text
        self.links = [link.attrs.get("href") or "" for link in self.root.select("a")]
        self.layout = [
            section_name(child) for child in main.children if isinstance(child, Element)
        ]
        self.header = parts(head.one("h1").parent or head)
        self.assets = [link.attrs["href"] for link in self.root.select("link")]
        self.assets += [script.attrs["src"] for script in self.root.select("script")]
        self.pills = [pill.text for pill in head.select("p", "status-pill")]
        self.name = head.one("h1").text
        self.tagline = head.one("p", "standfirst").text
        self.actions = {
            action.text: action.attrs["href"] for action in head.one("div", "actions").select("a")
        }
        self.facts = {
            fact.one("dt").text: fact.one("dd").text
            for fact in self.root.one("dl").select("div")
        }
        self.sections = {
            heading.text: section.text
            for section in main.select("section")
            for heading in section.select("h2")
        }
        self.use_cases = [
            case.text for cases in main.select("ul", "use-cases") for case in cases.select("li")
        ]
        self.prompt = started.one("pre", identity="prompt").text
        self.more = [listed(row) for row in main.select("article", "app-row")]


class MarkdownPage:
    """Read a tool's Markdown copy: name, description, facts, prompt, and use cases."""

    def __init__(self, document: str) -> None:
        assert document.endswith("\n") and not document.endswith("\n\n"), "Expected one final newline"
        blocks = document.removesuffix("\n").split("\n\n")
        self.layout = [block for block in blocks if block.startswith("#")]
        self.name = blocks[0].removeprefix("# ")
        self.description = blocks[1]
        self.facts = {
            term: value
            for term, _, value in (line.removeprefix("- ").partition(": ") for line in blocks[2].splitlines())
        }
        assert blocks[3:5] == ["## Get started", "Give this prompt to your agent:"], blocks[3:5]
        self.prompt = blocks[5].removeprefix("> ")
        self.use_cases = [line.removeprefix("- ") for block in blocks[7:] for line in block.splitlines()]


def llms_sections(document: str) -> dict[str, list[tuple[str, str, str]]]:
    """Check the llms.txt layout and return the (name, URL, notes) of each item by H2 title."""
    lines = document.splitlines()
    assert re.fullmatch(r"# \S.*", lines[0]) and re.fullmatch(r"> \S.*", lines[2]), lines[:3]
    assert lines[1] == lines[3] == "", lines[:4]
    assert document.endswith("\n") and not document.endswith("\n\n"), "Expected one final newline"
    sections: dict[str, list[tuple[str, str, str]]] = {}
    items: list[tuple[str, str, str]] | None = None
    for line in lines[1:]:
        if line.startswith("#"):
            assert re.fullmatch(r"## \S.*", line) and line[3:] not in sections, line
            items = sections[line[3:]] = []
        elif line and items is not None:
            item = re.fullmatch(r"- \[([^\]]+)\]\((\S+)\)(?:: (\S.*))?", line)
            assert item, line
            items.append((item[1], item[2], item[3] or ""))
    return sections


@dataclass(frozen=True)
class Recorded:
    """What a tool's recorded files say its row and page show, and the snapshot source they omit."""

    name: str
    state: str
    category: str
    label: str
    tagline: str
    use_cases: list[str]
    source_url: str
    publisher: str
    version: str | None
    provenance: dict[str, Any]


def load_renderer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("catalog_theme_build", ROOT / "site" / "theme" / "build.py")
    assert spec and spec.loader
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    return renderer


def rendered_catalog(root: Path) -> str:
    return load_renderer().catalog({}, ARGS, root)


def rendered_tool_pages(root: Path) -> dict[str, str]:
    """Build the per-tool pages and return every written file by its output path."""
    with tempfile.TemporaryDirectory() as temporary:
        out = Path(temporary)
        load_renderer().build_listings(root, out, ARGS, SITE)
        return {
            path.relative_to(out).as_posix(): path.read_text(encoding="utf-8")
            for path in out.rglob("*")
            if path.is_file()
        }


def tool_page(root: Path, slug: str) -> ToolPage:
    return ToolPage(rendered_tool_pages(root)[f"tools/{slug}/index.html"])


def recorded_tools(root: Path) -> dict[str, Recorded]:
    """Derive each tool's expected display from its files and the shared identity helper."""
    renderer = load_renderer()

    def shown(value: str) -> str:
        return " ".join(renderer.plain(value).split())

    categories, listings = load_catalog_metadata(root)
    tools = {}
    for source in catalog_sources(root):
        slug = source.parent.name
        pointer = validate_pointer(read_json(source, root))
        manifest, provenance = read_snapshot(source.parent, root)
        listing = listings.get(slug)
        repository = pointer["repository"].removesuffix(".git")
        source_url = repository
        if pointer["path"] != ".":
            source_url = f"{repository}/tree/{quote(pointer['ref'], safe='/')}/{quote(pointer['path'], safe='/')}"
        owner = urlsplit(repository).path.strip("/").split("/")[0]
        tools[slug] = Recorded(
            name=slug.replace("-", " ").title(),
            state=recommendation_state(pointer, provenance, listing, bool(manifest)),
            category=listing["category"] if listing else UNCLASSIFIED,
            label=categories[listing["category"]]["label"] if listing else "Other",
            tagline=shown(renderer.first_sentence(manifest["description"])) if manifest else NO_SNAPSHOT,
            use_cases=[shown(case) for case in manifest.get("use_cases", [])],
            source_url=source_url,
            publisher="Microsoft" if owner == "microsoft" else owner,
            version=f"v{manifest['version']}" if manifest.get("version") else None,
            provenance=provenance,
        )
    return tools


class CatalogMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_json(self.root / "categories.json", {"categories": [CATEGORY]})
        self.add_entry("tool", LISTING)

    def add_entry(self, slug: str, listing: object | None) -> Path:
        entry = self.root / "tools" / slug
        write_json(entry / "source.json", {"repository": IDENTITY["repository"]})
        write_json(
            entry / "provenance.json",
            {
                "source": {**IDENTITY, "commit": COMMIT, "ref": "main"},
                "original_manifest_path": "SMART_TOOL.md",
                "last_success": "2026-10-07T03:38:13Z",
            },
        )
        (entry / "SMART_TOOL.md").write_text(
            "---\nname: Tool\ndescription: A fixture tool.\nplatforms: [linux]\nuse_cases: [testing]\n---\n# Tool\n",
            encoding="utf-8",
        )
        if listing is not None:
            write_json(entry / "listing.json", listing)
        return entry

    def assert_omits_snapshot_source(self, page: ToolPage, provenance: dict[str, Any]) -> None:
        """The snapshot's commit, refresh date, and manifest stay out of a tool's page."""
        self.assertNotIn("Manifest snapshot", page.text)
        self.assertNotIn("Read manifest", page.text)
        self.assertEqual([href for href in page.links if "/blob/" in href], [])
        if provenance:
            self.assertNotIn(provenance["source"]["commit"][:7], page.document)
            self.assertNotIn(provenance["last_success"][:10], page.document)
            manifest = quote(provenance["original_manifest_path"], safe="/")
            self.assertEqual([href for href in page.links if href.endswith(manifest)], [])

    def test_valid_recommendation_and_classified_alternative(self) -> None:
        self.add_entry("alternative", {"category": CATEGORY["id"], "recommended": False})
        categories, listings = load_catalog_metadata(self.root)
        self.assertEqual(categories, {CATEGORY["id"]: CATEGORY})
        self.assertEqual(listings["tool"], LISTING)
        self.assertEqual(listings["alternative"], {"category": CATEGORY["id"], "recommended": False})

    def test_category_only_normalizes_without_mutating_input_or_source_files(self) -> None:
        original = {"category": CATEGORY["id"]}
        normalized = validate_listing(original, {CATEGORY["id"]: CATEGORY})
        self.assertEqual(normalized, {**original, "recommended": False})
        self.assertIsNot(normalized, original)
        self.assertEqual(original, {"category": CATEGORY["id"]})
        self.assertEqual(recommendation_state({}, {}, original), "ordinary")
        entry = self.add_entry("category-only", original)
        paths = [self.root / "categories.json", *entry.iterdir()]
        before = {path: path.read_bytes() for path in paths}
        self.add_entry("explicit-false", {**original, "recommended": False})
        _, listings = load_catalog_metadata(self.root)
        self.assertEqual(listings["category-only"], normalized)
        self.assertEqual(sum(listing["recommended"] for listing in listings.values()), 1)
        rendered_catalog(self.root)
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_missing_metadata_preserves_legacy_catalog(self) -> None:
        (self.root / "categories.json").unlink()
        (self.root / "tools" / "tool" / "listing.json").unlink()
        self.assertEqual(load_catalog_metadata(self.root), (None, {}))

    def test_catalog_without_registry_renders_rows_without_chips(self) -> None:
        (self.root / "categories.json").unlink()
        (self.root / "tools" / "tool" / "listing.json").unlink()
        catalog = CatalogPage(rendered_catalog(self.root))
        self.assertEqual(catalog.root.select("div", identity="category-chips"), [])
        self.assertEqual(catalog.root.select("section", identity="featured"), [])
        self.assertEqual([row.slug for row in catalog.rows], ["tool"])
        self.assertEqual(catalog.rows[0].marks, [])
        self.assertEqual(catalog.rows[0].search, "tool tool a fixture tool. testing linux")
        self.assertEqual(catalog.count, "1 tool")
        page = tool_page(self.root, "tool")
        self.assertEqual(page.pills, [])
        self.assertEqual(page.facts, {"Platform": "Linux", "Publisher": "example.test"})

    def test_registry_with_unclassified_listing_is_valid(self) -> None:
        self.add_entry("unclassified", None)
        categories, listings = load_catalog_metadata(self.root)
        self.assertEqual(categories, {CATEGORY["id"]: CATEGORY})
        self.assertNotIn("unclassified", listings)

    def test_new_pointer_does_not_require_a_generated_snapshot(self) -> None:
        entry = self.add_entry("new-tool", None)
        (entry / "SMART_TOOL.md").unlink()
        (entry / "provenance.json").unlink()
        _, listings = load_catalog_metadata(self.root)
        self.assertNotIn("new-tool", listings)

    def test_source_only_tools_with_and_without_snapshots_render_under_other(self) -> None:
        (self.root / "tools" / "tool" / "listing.json").unlink()
        pending = self.add_entry("pending-snapshot", None)
        (pending / "SMART_TOOL.md").unlink()
        (pending / "provenance.json").unlink()
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        catalog = CatalogPage(rendered_catalog(self.root))
        pages = rendered_tool_pages(self.root)
        self.assertEqual([row.slug for row in catalog.rows], ["pending-snapshot", "tool"])
        for row in catalog.rows:
            self.assertEqual(row.category, UNCLASSIFIED)
            self.assertEqual(row.marks, [])
            self.assertEqual(row.links, [f"./tools/{row.slug}/"] * 2)
        pending_row, tool_row = catalog.rows
        self.assertEqual(pending_row.text, f"Pending Snapshot {NO_SNAPSHOT} Get")
        self.assertEqual(
            pending_row.search,
            "pending-snapshot pending snapshot no manifest snapshot is available yet. "
            "inspect the source repository for current guidance. other",
        )
        self.assertEqual(tool_row.text, "Tool A fixture tool. Get")
        self.assertEqual(tool_row.search, "tool tool a fixture tool. testing linux other")
        self.assertEqual(catalog.chips, [ALL_CHIP, OTHER_CHIP])
        self.assertEqual(catalog.count, "2 tools")
        self.assertEqual(catalog.featured, [])
        self.assertEqual(catalog.root.select("section", identity="featured"), [])
        self.assertEqual(
            set(pages),
            {
                "tools/pending-snapshot/index.html",
                "tools/pending-snapshot/index.md",
                "tools/tool/index.html",
                "tools/tool/index.md",
            },
        )
        self.assertEqual(
            pages["tools/pending-snapshot/index.md"],
            f"# Pending Snapshot\n\n{NO_SNAPSHOT} Inspect the source repository for current guidance.\n\n"
            "- Category: Other\n- Publisher: example.test\n- Source: https://example.test/tool\n\n"
            "## Get started\n\nGive this prompt to your agent:\n\n"
            "> Go to https://example.test/tool and install it.\n",
        )
        self.assertEqual(
            pages["tools/tool/index.md"],
            "# Tool\n\nA fixture tool.\n\n"
            "- Category: Other\n- Platforms: Linux\n- Publisher: example.test\n"
            "- Source: https://example.test/tool\n\n"
            "## Get started\n\nGive this prompt to your agent:\n\n"
            "> Go to https://example.test/tool and install it.\n\n"
            "## Use it to\n\n- testing\n",
        )
        pending_page = ToolPage(pages["tools/pending-snapshot/index.html"])
        self.assertEqual(pending_page.pills, [])
        self.assertEqual(pending_page.tagline, NO_SNAPSHOT)
        self.assertEqual(
            pending_page.facts,
            {"Category": "Other", "Platform": "Not declared", "Publisher": "example.test"},
        )
        self.assertEqual(pending_page.prompt, "Go to https://example.test/tool and install it.")
        self.assertEqual(
            pending_page.sections,
            {
                "Get started.": get_started("https://example.test/tool"),
                "What it does.": "What it does. Inspect the source repository for current guidance.",
            },
        )
        self.assertEqual(pending_page.text.count(NO_SNAPSHOT), 1)
        self.assert_omits_snapshot_source(pending_page, {})
        snapshot_page = ToolPage(pages["tools/tool/index.html"])
        self.assertEqual(snapshot_page.pills, [])
        self.assertEqual(
            snapshot_page.facts,
            {"Category": "Other", "Platform": "Linux", "Publisher": "example.test"},
        )
        self.assertEqual(
            snapshot_page.sections,
            {"Get started.": get_started("https://example.test/tool"), "Use it to.": "Use it to. testing"},
        )
        self.assertNotIn(NO_SNAPSHOT, snapshot_page.text)
        self.assert_omits_snapshot_source(
            snapshot_page, read_json(self.root / "tools" / "tool" / "provenance.json", self.root)
        )
        self.assertEqual(load_catalog_metadata(self.root), ({CATEGORY["id"]: CATEGORY}, {}))
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)
        self.assertEqual({path for path in self.root.rglob("*") if path.is_file()}, set(before))

    def test_unknown_category_and_listing_without_registry_fail(self) -> None:
        write_json(self.root / "tools" / "tool" / "listing.json", {"category": "self-awarded"})
        with self.assertRaisesRegex(ValueError, "category"):
            load_catalog_metadata(self.root)
        write_json(self.root / "tools" / "tool" / "listing.json", LISTING)
        (self.root / "categories.json").unlink()
        with self.assertRaisesRegex(ValueError, r"categories\.json"):
            load_catalog_metadata(self.root)

    def test_duplicate_category_and_second_designation_fail(self) -> None:
        write_json(self.root / "categories.json", {"categories": [CATEGORY, CATEGORY]})
        with self.assertRaises(ValueError):
            load_catalog_metadata(self.root)
        write_json(self.root / "categories.json", {"categories": [CATEGORY]})
        self.add_entry("second", LISTING)
        with self.assertRaises(ValueError):
            load_catalog_metadata(self.root)

    def test_stale_designation_still_reserves_the_category(self) -> None:
        provenance = self.root / "tools" / "tool" / "provenance.json"
        value = json.loads(provenance.read_text())
        value["source"]["path"] = "another"
        write_json(provenance, value)
        # Drift is a valid editorial state, not permission to award the slot twice.
        _, listings = load_catalog_metadata(self.root)
        pointer = read_json(self.root / "tools" / "tool" / "source.json", self.root)
        self.assertEqual(recommendation_state(pointer, value, listings["tool"]), "needs-review")
        self.add_entry("second", LISTING)
        with self.assertRaises(ValueError):
            load_catalog_metadata(self.root)

    def test_registry_types_and_required_fields_fail(self) -> None:
        invalid = [[], {"categories": {}}, {"categories": [None]}, {"categories": [True]}]
        for field in ("id", "label", "scope"):
            for bad in (None, False, 7, "", [], {}):
                invalid.append({"categories": [{**CATEGORY, field: bad}]})
            invalid.append({"categories": [{key: value for key, value in CATEGORY.items() if key != field}]})
        for value in invalid:
            with self.subTest(value=value):
                write_json(self.root / "categories.json", value)
                with self.assertRaises(ValueError):
                    load_catalog_metadata(self.root)

    def test_listing_types_and_required_fields_fail(self) -> None:
        invalid = [[], None, True, {}, {"recommended": True}]
        for bad in (None, "true", 1, 0, [], {}):
            invalid.append({**LISTING, "recommended": bad})
        for bad in (None, False, 7, "", [], {}):
            invalid.append({**LISTING, "category": bad})
        invalid.append({"category": CATEGORY["id"], "recommended": True})
        for value in invalid:
            with self.subTest(value=value):
                write_json(self.root / "tools" / "tool" / "listing.json", value)
                with self.assertRaises(ValueError):
                    load_catalog_metadata(self.root)

    def test_only_one_primary_category_and_no_duplicate_evidence_fields(self) -> None:
        for value in (
            {**LISTING, "category": [CATEGORY["id"]]},
            {**LISTING, "categories": [CATEGORY["id"]]},
            {**LISTING, "review_evidence": "https://example.test/review"},
            {**LISTING, "review_status": "passed"},
            {"category": CATEGORY["id"], "recommended": False, "reviewed_source": IDENTITY},
            {"category": CATEGORY["id"], "reviewed_source": IDENTITY},
        ):
            with self.subTest(value=value):
                write_json(self.root / "tools" / "tool" / "listing.json", value)
                with self.assertRaises(ValueError):
                    load_catalog_metadata(self.root)

    def test_registry_is_flat_and_closed(self) -> None:
        for category in (
            {**CATEGORY, "children": []},
            {**CATEGORY, "parent": "other"},
            {**CATEGORY, "id": "Invalid ID"},
        ):
            with self.subTest(category=category):
                write_json(self.root / "categories.json", {"categories": [category]})
                with self.assertRaises(ValueError):
                    load_catalog_metadata(self.root)

    def test_structural_validation_does_not_establish_maintainer_authority(self) -> None:
        # A valid designation alone cannot distinguish a maintainer decision
        # from creator-authored metadata. Authorization is the documented merge
        # gate, not a runtime claim made by the schema validator.
        _, listings = load_catalog_metadata(self.root)
        self.assertEqual(listings["tool"], LISTING)

    def test_reviewed_source_identity_validation(self) -> None:
        invalid = [None, [], True, {}]
        for field in ("repository", "path"):
            for bad in (None, False, 7, "", [], {}):
                invalid.append({**IDENTITY, field: bad})
            invalid.append({key: value for key, value in IDENTITY.items() if key != field})
        invalid.extend(
            [
                {**IDENTITY, "commit": COMMIT},
                {**IDENTITY, "ref": "main"},
                {**IDENTITY, "repository": "http://example.test/tool.git"},
                {**IDENTITY, "repository": "https://user:password@example.test/tool.git"},
                {**IDENTITY, "repository": "https://example.test/tool.git?secret=example"},
                {**IDENTITY, "path": "../tool"},
                {**IDENTITY, "path": "/tool"},
            ]
        )
        for identity in invalid:
            with self.subTest(identity=identity):
                write_json(self.root / "tools" / "tool" / "listing.json", {**LISTING, "reviewed_source": identity})
                with self.assertRaises(ValueError):
                    load_catalog_metadata(self.root)

    def test_malformed_json_fails_without_changing_files(self) -> None:
        for relative in ("categories.json", "tools/tool/listing.json"):
            with self.subTest(file=relative):
                target = self.root / relative
                original = target.read_bytes()
                target.write_bytes(b"{ broken\n")
                with self.assertRaises(ValueError):
                    load_catalog_metadata(self.root)
                self.assertEqual(target.read_bytes(), b"{ broken\n")
                target.write_bytes(original)

    def test_validation_never_renews_editorial_data(self) -> None:
        listing_file = self.root / "tools" / "tool" / "listing.json"
        registry_file = self.root / "categories.json"
        registry_before = registry_file.read_bytes()
        before = listing_file.read_bytes()
        changed = copy.deepcopy(LISTING)
        changed["reviewed_source"]["path"] = "another"
        # A well-formed review of another path is valid metadata but not a renewed endorsement.
        write_json(listing_file, changed)
        old_review = listing_file.read_bytes()
        _, listings = load_catalog_metadata(self.root)
        self.assertEqual(listings["tool"], changed)
        self.assertEqual(listing_file.read_bytes(), old_review)
        self.assertEqual(registry_file.read_bytes(), registry_before)
        self.assertNotEqual(old_review, before)

    def test_current_classifications_keep_ten_categories_and_two_selected_sources(self) -> None:
        expected_categories = {
            "test-environments": (
                "Test environments",
                "Create and operate isolated environments for testing software and reproducing failures.",
            ),
            "builder-tools": (
                "Builder tools",
                "Hand off more of the work when you build with AI, and spend your time on what matters.",
            ),
            "smart-tool-development": (
                "Smart Tool development",
                "Create, extend, check, and evaluate Smart Tools.",
            ),
            "research-knowledge": (
                "Research & knowledge",
                "Find sourced answers, check claims, explore documentation and news, and retrieve team knowledge.",
            ),
            "media-production": (
                "Audio, video & animation",
                "Record demonstrations, edit recordings, extract clips, and produce motion graphics.",
            ),
            "presentations-documents": (
                "Presentations & documents",
                "Turn evidence into presentations or documents and review the resulting communication.",
            ),
            "developer-tools": (
                "App design & developer tools",
                "Prototype app experiences, discover and manage repositories, and manage coding sessions and terminals.",
            ),
            "workplace-productivity": (
                "Email, calendar & work preparation",
                "Handle messages, contacts, schedules, meeting preparation, and workplace briefings.",
            ),
            "music-listening": (
                "Music & playlists",
                "Find music, curate playlists, inspect listening libraries and devices, and control playback.",
            ),
            "home-automation": (
                "Smart home",
                "Inspect household devices and operate explicitly authorized home services.",
            ),
        }
        registry = json.loads((ROOT / "categories.json").read_text())
        self.assertEqual(
            {category["id"]: (category["label"], category["scope"]) for category in registry["categories"]},
            expected_categories,
        )
        expected_assignments = {
            slug: category
            for category, slugs in CURRENT_CLASSIFICATIONS.items()
            for slug in slugs
        }
        categories, listings = load_catalog_metadata(ROOT)
        self.assertEqual(set(categories), set(expected_categories))
        sources = {source.parent.name for source in catalog_sources(ROOT)}
        self.assertLessEqual(set(expected_assignments), sources)
        self.assertLessEqual(set(listings), sources)
        for slug, category in expected_assignments.items():
            with self.subTest(tool=slug):
                listing = listings.get(slug)
                self.assertIsNotNone(listing)
                self.assertEqual(listing["category"], category)
                self.assertEqual(listing["recommended"], slug in CURRENT_SELECTIONS)
                if slug not in CURRENT_SELECTIONS:
                    raw_listing = read_json(ROOT / "tools" / slug / "listing.json", ROOT)
                    self.assertEqual(raw_listing, {"category": category})
        self.assertEqual(
            {slug for slug, listing in listings.items() if listing["recommended"]},
            set(CURRENT_SELECTIONS),
        )

    def test_selected_sources_keep_their_source_identity(self) -> None:
        # Refresh may advance a snapshot to a newer upstream commit; the
        # selection follows the tracked ref.
        _, listings = load_catalog_metadata(ROOT)
        for slug, identity in CURRENT_SELECTIONS.items():
            with self.subTest(tool=slug):
                entry = ROOT / "tools" / slug
                pointer = validate_pointer(read_json(entry / "source.json", ROOT))
                manifest, provenance = read_snapshot(entry, ROOT)
                reviewed = listings[slug]["reviewed_source"]
                self.assertEqual(pointer["repository"], identity["repository"])
                self.assertEqual(pointer["path"], identity["path"])
                self.assertEqual(provenance["source"]["repository"], identity["repository"])
                self.assertEqual(provenance["source"]["path"], identity["path"])
                self.assertEqual({key: reviewed[key] for key in identity}, identity)
                self.assertEqual(
                    recommendation_state(pointer, provenance, listings[slug], bool(manifest)),
                    "recommended",
                )

    def test_real_classifications_remain_valid_metadata_after_snapshot_refresh(self) -> None:
        seed_root = self.root / "seeds"
        write_json(seed_root / "categories.json", json.loads((ROOT / "categories.json").read_text()))
        for entry in ROOT.glob("tools/*/listing.json"):
            slug = entry.parent.name
            for name in ("source.json", "listing.json", "provenance.json", "SMART_TOOL.md"):
                destination = seed_root / "tools" / slug / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((entry.parent / name).read_bytes())
            listing_file = seed_root / "tools" / slug / "listing.json"
            before = listing_file.read_bytes()
            provenance_file = seed_root / "tools" / slug / "provenance.json"
            value = json.loads(provenance_file.read_text())
            value["source"]["commit"] = "b" * 40
            write_json(provenance_file, value)
            _, listings = load_catalog_metadata(seed_root)
            pointer = read_json(seed_root / "tools" / slug / "source.json", seed_root)
            manifest, provenance = read_snapshot(seed_root / "tools" / slug, seed_root)
            self.assertEqual(
                recommendation_state(pointer, provenance, listings[slug], bool(manifest)),
                "recommended" if slug in CURRENT_SELECTIONS else "ordinary",
            )
            self.assertEqual(listing_file.read_bytes(), before)

    def test_cli_delegates_to_the_shared_validator(self) -> None:
        spec = importlib.util.spec_from_file_location("validate_catalog_cli", ROOT / "scripts" / "validate_catalog.py")
        assert spec and spec.loader
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with patch("catalog_metadata.load_catalog_metadata") as shared, redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["--catalog-root", str(self.root)]), 0)
        shared.assert_called_once_with(self.root.resolve())
        with (
            patch("catalog_metadata.load_catalog_metadata", side_effect=ValueError("invalid metadata")),
            redirect_stderr(io.StringIO()) as errors,
        ):
            self.assertEqual(cli.main(["--catalog-root", str(self.root)]), 1)
        self.assertIn("ERROR catalog: invalid metadata", errors.getvalue())

    def test_cli_help_describes_category_metadata(self) -> None:
        spec = importlib.util.spec_from_file_location("validate_catalog_cli", ROOT / "scripts" / "validate_catalog.py")
        assert spec and spec.loader
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with redirect_stdout(io.StringIO()) as output, self.assertRaises(SystemExit) as result:
            cli.main(["--help"])
        self.assertEqual(result.exception.code, 0)
        self.assertIn("optional categories.json", " ".join(output.getvalue().split()))

    def test_recommendation_requires_matching_pointer_review_and_snapshot(self) -> None:
        entry = self.root / "tools" / "tool"
        pointer = read_json(entry / "source.json", self.root)
        manifest, provenance = read_snapshot(entry, self.root)
        self.assertEqual(manifest["name"], "Tool")
        self.assertEqual(validate_pointer(pointer)["ref"], "main")
        self.assertEqual(catalog_sources(self.root), [entry / "source.json"])
        self.assertEqual(recommendation_state(pointer, provenance, LISTING), "recommended")
        self.assertEqual(recommendation_state(pointer, provenance, None), "ordinary")
        self.assertEqual(
            recommendation_state(pointer, provenance, {"category": CATEGORY["id"], "recommended": False}),
            "ordinary",
        )
        self.assertEqual(recommendation_state(pointer, provenance, LISTING, False), "needs-review")
        self.assertEqual(recommendation_state(pointer, {}, LISTING), "needs-review")
        advanced = copy.deepcopy(provenance)
        advanced["source"]["commit"] = "b" * 40
        self.assertEqual(recommendation_state(pointer, advanced, LISTING), "recommended")
        self.assertEqual(
            recommendation_state({**pointer, "ref": COMMIT}, advanced, LISTING), "needs-review"
        )
        for field, value in (
            ("repository", "https://example.test/another.git"),
            ("path", "another"),
            ("ref", "feature"),
        ):
            with self.subTest(pointer_field=field):
                self.assertEqual(
                    recommendation_state({**pointer, field: value}, provenance, LISTING), "needs-review"
                )
        for field, value in (
            ("repository", "https://example.test/another.git"),
            ("path", "another"),
        ):
            changed = copy.deepcopy(LISTING)
            changed["reviewed_source"][field] = value
            with self.subTest(reviewed_field=field):
                self.assertEqual(recommendation_state(pointer, provenance, changed), "needs-review")

    def test_recommendation_drift_removes_rendered_badge_and_preference(self) -> None:
        self.add_entry("a-ordinary", None)
        before = CatalogPage(rendered_catalog(self.root))
        self.assertEqual([row.slug for row in before.rows], ["a-ordinary", "tool"])
        self.assertEqual([card.slug for card in before.featured], ["tool"])
        self.assertEqual(before.rows[0].marks, [])
        self.assertEqual(before.rows[1].marks, MARKS["recommended"])
        self.assertEqual(before.featured[0].marks, [])
        self.assertEqual(tool_page(self.root, "tool").pills, ["Recommended"])
        listing_path = self.root / "tools" / "tool" / "listing.json"
        original = listing_path.read_bytes()
        provenance_path = self.root / "tools" / "tool" / "provenance.json"
        provenance = read_json(provenance_path, self.root)
        provenance["source"]["commit"] = "b" * 40
        write_json(provenance_path, provenance)
        advanced = CatalogPage(rendered_catalog(self.root))
        self.assertEqual([card.slug for card in advanced.featured], ["tool"])
        self.assertEqual(advanced.rows[1].marks, MARKS["recommended"])
        advanced_page = tool_page(self.root, "tool")
        self.assertEqual(advanced_page.pills, ["Recommended"])
        self.assertEqual(advanced_page.sections["Get started."], get_started("https://example.test/tool"))
        self.assert_omits_snapshot_source(advanced_page, provenance)
        # The distribution path moved away from the reviewed source.
        pointer_path = self.root / "tools" / "tool" / "source.json"
        write_json(pointer_path, {"repository": IDENTITY["repository"], "path": "another"})
        provenance["source"]["path"] = "another"
        write_json(provenance_path, provenance)
        after = CatalogPage(rendered_catalog(self.root))
        self.assertEqual([row.slug for row in after.rows], ["a-ordinary", "tool"])
        ordinary, drifted = after.rows
        self.assertEqual(drifted.category, CATEGORY["id"])
        self.assertEqual(drifted.marks, MARKS["needs-review"])
        self.assertEqual(drifted.text, "Tool A fixture tool. Recommendation needs review Get")
        review = after.root.one("span", "tag")
        self.assertEqual(review.attrs, {"class": "tag"})
        self.assertEqual(parts(review.parent or after.root), ["app-row-name", "p", "tag"])
        self.assertEqual(ordinary.category, UNCLASSIFIED)
        self.assertEqual(ordinary.marks, [])
        self.assertEqual(ordinary.text, "A Ordinary A fixture tool. Get")
        self.assertEqual(after.featured, [])
        self.assertEqual(after.root.select("section", identity="featured"), [])
        self.assertEqual(after.chips, [ALL_CHIP, CATEGORY_CHIP, OTHER_CHIP])
        drifted_page = tool_page(self.root, "tool")
        self.assertEqual(drifted_page.pills, ["Recommendation needs review"])
        self.assertEqual(drifted_page.facts["Category"], CATEGORY["label"])
        self.assertEqual(
            drifted_page.actions,
            {"Get": "#get-started", "View on GitHub": "https://example.test/tool/tree/main/another"},
        )
        self.assertEqual(
            drifted_page.prompt, "Go to https://example.test/tool/tree/main/another and install it."
        )
        self.assert_omits_snapshot_source(drifted_page, provenance)
        self.assertEqual(listing_path.read_bytes(), original)

    def test_search_and_category_chips_precede_featured_and_all_tools(self) -> None:
        self.add_entry("ordinary", None)
        renderer = load_renderer()
        document = renderer.catalog({}, ARGS, self.root)
        positions = [
            document.index(f'id="{identity}"')
            for identity in ("store-search", "category-chips", "featured", "result-count", "empty-results")
        ]
        self.assertEqual(positions, sorted(positions))
        catalog = CatalogPage(document)
        root = catalog.root
        self.assertEqual(root.one("section", "catalog-hero").one("h1").text, "Catalog")
        # The script reveals its own controls; the tools stay readable without it.
        hidden = {element.attrs.get("id") for element in root.descendants() if "hidden" in element.attrs}
        self.assertEqual(hidden, {"store-search", "category-chips", "empty-results"})
        search = root.one("section", "catalog-hero").one("div", identity="store-search")
        self.assertEqual(search.one("input", identity="tool-search").attrs["type"], "search")
        self.assertEqual(root.one("div", identity="category-chips").attrs["role"], "group")
        self.assertEqual(catalog.chips, [ALL_CHIP, CATEGORY_CHIP, OTHER_CHIP])
        clear = [element for element in root.descendants() if "data-clear" in element.attrs]
        self.assertEqual(clear, root.one("div", identity="empty-results").select("button"))
        self.assertEqual(len(clear), 1)
        # The count is spoken, not drawn: a status that only screen readers reach.
        count = root.one("span", identity="result-count")
        self.assertEqual(count.attrs["role"], "status")
        self.assertEqual(count.classes, ["visually-hidden"])
        self.assertEqual(catalog.count, "2 tools")
        self.assertEqual(parts(count.parent or root), ["h2", "visually-hidden"])
        self.assertEqual((count.parent or root).text, "All tools 2 tools")
        browse = root.one("section", "split")
        self.assertEqual(
            browse.text,
            "Let your agent browse. One skill finds the right tool and installs it. "
            f"Ask your agent. Prompt Copy {renderer.FAMILY_PROMPT}",
        )
        self.assertEqual(parts(browse.one("div", "callout")), ["h3", "copy-region"])
        self.assertEqual(root.select("p", "note"), [])
        self.assertNotIn("not the tools themselves", root.text)
        self.assertNotIn("Listings come from", root.text)
        self.assertNotIn("Add a tool", [anchor.text for anchor in root.select("a")])
        self.assertEqual([card.slug for card in catalog.featured], ["tool"])
        self.assertEqual([row.slug for row in catalog.rows], ["ordinary", "tool"])
        self.assertEqual(catalog.featured[0].marks, [])
        self.assertEqual(catalog.rows[0].marks, [])
        self.assertEqual(catalog.rows[1].marks, MARKS["recommended"])
        self.assertEqual(
            [article.attrs["class"] for article in root.select("article")],
            ["tool-card wide", "app-row", "app-row"],
        )

    def test_every_element_the_script_looks_up_is_rendered_once(self) -> None:
        self.add_entry("ordinary", None)
        script = (ROOT / "site" / "theme" / "site.js").read_text(encoding="utf-8")
        looked_up = set(re.findall(r"getElementById\('([^']+)'\)", script))
        self.assertLessEqual(
            {"tool-search", "store-search", "category-chips", "result-count", "featured", "empty-results"},
            looked_up,
        )
        renderer = load_renderer()
        page = parse(renderer.document(SITE, renderer.catalog(SITE, ARGS, self.root), ARGS))
        identities = page.identities()
        for identity in looked_up:
            with self.subTest(identity=identity):
                self.assertEqual(identities[identity], 1)
        self.assertEqual(set(identities.values()), {1})

    def test_recommended_marker_is_static_and_the_tool_page_omits_snapshot_source(self) -> None:
        catalog = CatalogPage(rendered_catalog(self.root))
        self.assertEqual([row.slug for row in catalog.rows], ["tool"])
        self.assertEqual([card.slug for card in catalog.featured], ["tool"])
        row, card = catalog.rows[0], catalog.featured[0]
        self.assertEqual(row.category, CATEGORY["id"])
        self.assertEqual(row.marks, MARKS["recommended"])
        self.assertEqual(row.text, "Tool Recommended A fixture tool. Get")
        self.assertEqual(row.links, ["./tools/tool/"] * 2)
        self.assertEqual(row.get_label, "Get Tool")
        self.assertEqual(card.marks, [])
        self.assertEqual(card.text, "Tool A fixture tool. Get")
        self.assertEqual(card.links, ["./tools/tool/"] * 2)
        tag = catalog.root.one("span", "tag")
        self.assertEqual(tag.attrs, {"class": "tag"})
        self.assertEqual(tag.children, ["Recommended"])
        self.assertEqual(parts(tag.parent or catalog.root), ["a", "tag"])
        self.assertTrue(
            {"a", "button", "details", "summary"}.isdisjoint(ancestor.tag for ancestor in tag.ancestors())
        )
        self.assertEqual(
            [span.attrs.get("id") for span in catalog.root.select("span", "visually-hidden")],
            ["result-count"],
        )
        page = tool_page(self.root, "tool")
        self.assertEqual(page.title, "Tool | Amplifier Smart Tools catalog")
        self.assertEqual(page.pills, ["Recommended"])
        self.assertEqual(page.name, "Tool")
        self.assertEqual(page.tagline, "A fixture tool.")
        self.assertEqual(
            page.actions, {"Get": "#get-started", "View on GitHub": "https://example.test/tool"}
        )
        self.assertEqual(
            page.facts, {"Category": "Test environments", "Platform": "Linux", "Publisher": "example.test"}
        )
        self.assertEqual(page.use_cases, ["testing"])
        self.assertEqual(page.prompt, "Go to https://example.test/tool and install it.")
        self.assertEqual(
            page.sections,
            {"Get started.": get_started("https://example.test/tool"), "Use it to.": "Use it to. testing"},
        )
        self.assert_omits_snapshot_source(
            page, read_json(self.root / "tools" / "tool" / "provenance.json", self.root)
        )
        self.assertEqual(page.more, [])

    def test_tool_page_status_pill_follows_recommendation_state(self) -> None:
        self.add_entry("ordinary", {"category": CATEGORY["id"]})
        pages = rendered_tool_pages(self.root)
        recommended = ToolPage(pages["tools/tool/index.html"])
        ordinary = ToolPage(pages["tools/ordinary/index.html"])
        self.assertEqual(recommended.pills, ["Recommended"])
        self.assertEqual(recommended.header, ["status-pill", "h1", "facts", "standfirst", "actions"])
        self.assertEqual(ordinary.pills, [])
        self.assertEqual(ordinary.header, ["h1", "facts", "standfirst", "actions"])
        # A designation without its snapshot keeps the category slot but not the endorsement.
        (self.root / "tools" / "tool" / "provenance.json").unlink()
        review = tool_page(self.root, "tool")
        self.assertEqual(review.pills, ["Recommendation needs review"])
        self.assertEqual(review.header, ["status-pill", "h1", "facts", "standfirst", "actions"])
        self.assertEqual(tool_page(self.root, "ordinary").pills, [])

    def test_tool_page_keeps_facts_in_its_header_and_the_prompt_ahead_of_use_cases(self) -> None:
        self.add_entry("neighbor", {"category": CATEGORY["id"]})
        manifest = self.root / "tools" / "tool" / "SMART_TOOL.md"
        manifest.write_text(
            "---\nname: Tool\nversion: 1.2.3\ndescription: A fixture tool. It checks things.\n"
            "platforms: [linux]\nuse_cases: [testing]\n---\n# Tool\n",
            encoding="utf-8",
        )
        page = tool_page(self.root, "tool")
        self.assertEqual(page.layout, ["store-head", "get-started", "Use it to.", "More tools."])
        self.assertEqual(page.header, ["status-pill", "h1", "facts", "standfirst", "actions"])
        self.assertEqual(
            list(page.facts.items()),
            [
                ("Category", "Test environments"),
                ("Platform", "Linux"),
                ("Publisher", "example.test"),
                ("Version", "v1.2.3"),
            ],
        )
        # Each term is read to a screen reader and only its value is drawn.
        facts = page.root.one("dl")
        self.assertEqual(facts.classes, ["facts"])
        self.assertEqual(
            [
                [(child.tag, child.classes) for child in fact.children if isinstance(child, Element)]
                for fact in facts.children
                if isinstance(fact, Element)
            ],
            [[("dt", ["visually-hidden"]), ("dd", [])]] * 4,
        )
        self.assertEqual(
            page.sections,
            {
                "Get started.": get_started("https://example.test/tool"),
                "Use it to.": "Use it to. It checks things. testing",
                "More tools.": "More tools. Neighbor A fixture tool. Get",
            },
        )
        self.assertEqual([other.slug for other in page.more], ["neighbor"])
        manifest.write_text(
            "---\nname: Tool\ndescription: A fixture tool. It checks things.\n"
            "platforms: [linux]\nuse_cases: []\n---\n# Tool\n",
            encoding="utf-8",
        )
        described = tool_page(self.root, "tool")
        self.assertEqual(described.layout, ["store-head", "get-started", "What it does.", "More tools."])
        self.assertEqual(described.sections["What it does."], "What it does. It checks things.")
        self.assertEqual(described.use_cases, [])
        self.assertNotIn("Version", described.facts)
        manifest.write_text(
            "---\nname: Tool\ndescription: A fixture tool.\nplatforms: [linux]\nuse_cases: []\n---\n# Tool\n",
            encoding="utf-8",
        )
        self.assertEqual(tool_page(self.root, "tool").layout, ["store-head", "get-started", "More tools."])

    def test_page_shell_credits_the_family_once_in_the_footer(self) -> None:
        renderer = load_renderer()
        shell = parse(renderer.document(SITE, "", ARGS)).one("body")
        self.assertEqual(
            [child.tag for child in shell.children if isinstance(child, Element)],
            ["a", "svg", "header", "main", "footer", "div"],
        )
        footer = shell.one("footer")
        credit = shell.one("p", "credit")
        self.assertEqual(
            footer.text, "Amplifier Smart Tools Catalog Blog Specification GitHub Developed by made at Microsoft"
        )
        self.assertIs(footer.one("div", "footer-grid").children[-1], credit)
        self.assertEqual(credit.text, "Developed by made at Microsoft")
        self.assertEqual([(child.tag, child.text) for child in credit.descendants()], [("strong", "made")])
        self.assertNotIn("a", [ancestor.tag for ancestor in credit.ancestors()])
        for words in ("made", "Microsoft"):
            with self.subTest(words=words):
                self.assertEqual(shell.text.count(words), 1)
        for class_name in ("attribution", "footer-attribution", "team"):
            with self.subTest(class_name=class_name):
                self.assertEqual([element for element in shell.descendants() if class_name in element.classes], [])
        for words in ("Office of the CTO", "Math", "Design", "Engineering"):
            with self.subTest(words=words):
                self.assertNotIn(words, shell.text)
        # A publisher is a fact about one tool; the shell names Microsoft only in its credit.
        entry = self.add_entry("published", None)
        repository = "https://github.com/microsoft/example.git"
        write_json(entry / "source.json", {"repository": repository})
        provenance = read_json(entry / "provenance.json", self.root)
        provenance["source"]["repository"] = repository
        write_json(entry / "provenance.json", provenance)
        page = tool_page(self.root, "published")
        self.assertEqual(page.facts["Publisher"], "Microsoft")
        self.assertEqual(page.root.one("main").text.count("Microsoft"), 1)
        self.assertEqual(page.text.count("Microsoft"), 2)
        self.assertEqual(tool_page(self.root, "tool").text.count("Microsoft"), 1)

    def test_page_shell_links_the_same_destinations_in_the_masthead_footer_and_menu(self) -> None:
        renderer = load_renderer()
        shell = parse(renderer.document(SITE, "", ARGS)).one("body")
        destinations = [
            ("Catalog", "https://microsoft.github.io/amplifier-smart-tools-catalog/"),
            ("Blog", "https://microsoft.github.io/amplifier-smart-tools/blog/"),
            ("Specification", renderer.SPEC),
            ("GitHub", "https://github.com/microsoft/amplifier-smart-tools-catalog"),
        ]
        regions = {
            "masthead": shell.one("header", "masthead").one("nav", "nav"),
            "footer": shell.one("footer").one("nav", "footer-links"),
            "menu": shell.one("div", identity="menu").one("ul", "menu-rows"),
        }
        for name, region in regions.items():
            with self.subTest(region=name):
                self.assertEqual(
                    [(anchor.text, anchor.attrs["href"]) for anchor in region.select("a")], destinations
                )
        # Only the masthead marks the page a reader is on.
        self.assertEqual(
            [
                (anchor.text, anchor.attrs["aria-current"], named(anchor.parent or shell))
                for anchor in shell.select("a")
                if "aria-current" in anchor.attrs
            ],
            [("Catalog", "page", "nav")],
        )
        self.assertNotIn("Build", shell.text)

    def test_rows_show_the_first_sentence_and_search_covers_the_manifest(self) -> None:
        cases = [f"case {number}" for number in range(1, 9)]
        (self.root / "tools" / "tool" / "SMART_TOOL.md").write_text(
            "---\nname: fixture-name\nversion: 1.2.3\n"
            'description: "Checks apps \\u2014 fast.\\n  Use after v1.2 builds. Then stop."\n'
            f"platforms: [linux, macos]\nuse_cases: {json.dumps(cases)}\n---\n# Tool\n",
            encoding="utf-8",
        )
        catalog = CatalogPage(rendered_catalog(self.root))
        row, card = catalog.rows[0], catalog.featured[0]
        self.assertEqual(row.tagline, "Checks apps - fast.")
        self.assertEqual(card.tagline, "Checks apps - fast.")
        self.assertEqual(
            " ".join(row.search.split()),
            "fixture-name tool checks apps - fast. use after v1.2 builds. then stop. "
            f"{' '.join(cases)} linux macos test environments",
        )
        page = tool_page(self.root, "tool")
        self.assertEqual(page.tagline, "Checks apps - fast.")
        self.assertEqual(
            page.facts,
            {
                "Category": "Test environments",
                "Platform": "Linux, macOS",
                "Publisher": "example.test",
                "Version": "v1.2.3",
            },
        )
        self.assertEqual(page.use_cases, cases[:6])
        self.assertEqual(
            page.sections["Use it to."],
            f"Use it to. Use after v1.2 builds. Then stop. {' '.join(cases[:6])}",
        )
        renderer = load_renderer()
        for text, sentence in (
            ("One. Two.", "One."),
            ("Ready? Go.", "Ready?"),
            ("Reads v1.2 files. More.", "Reads v1.2 files."),
            ("Spread\n  over lines. More.", "Spread over lines."),
            ("No terminator", "No terminator"),
        ):
            with self.subTest(text=text):
                self.assertEqual(renderer.first_sentence(text), sentence)

    def test_digital_twin_fixture_renders_category_without_ordinary_badge(self) -> None:
        pinned = self.root / "pinned"
        write_json(pinned / "categories.json", read_json(ROOT / "categories.json", ROOT))
        slug = "digital-twin-universe"
        source_entry = ROOT / "tools" / slug
        target_entry = pinned / "tools" / slug
        for filename in ("source.json", "listing.json", "provenance.json", "SMART_TOOL.md"):
            (target_entry / filename).parent.mkdir(parents=True, exist_ok=True)
            (target_entry / filename).write_bytes((source_entry / filename).read_bytes())
        # Isolate the ordinary/zero-recommendation case from the live selections.
        write_json(target_entry / "listing.json", {"category": "test-environments", "recommended": False})
        unclassified_slug = "a-unclassified"
        write_json(pinned / "tools" / unclassified_slug / "source.json", {"repository": IDENTITY["repository"]})
        catalog = CatalogPage(rendered_catalog(pinned))
        self.assertEqual([row.slug for row in catalog.rows], [unclassified_slug, slug])
        unclassified, dtu = catalog.rows
        self.assertEqual(dtu.category, "test-environments")
        self.assertEqual(dtu.marks, [])
        self.assertEqual(dtu.text, f"Digital Twin Universe {dtu.tagline} Get")
        self.assertTrue(dtu.search.endswith(" test environments"))
        self.assertEqual(unclassified.category, UNCLASSIFIED)
        self.assertEqual(unclassified.marks, [])
        self.assertEqual(unclassified.text, f"A Unclassified {NO_SNAPSHOT} Get")
        self.assertTrue(unclassified.search.endswith(" other"))
        # Registry categories without a tool get no chip.
        self.assertEqual(
            catalog.chips,
            [ALL_CHIP, ("test-environments", "Test environments", "false"), OTHER_CHIP],
        )
        self.assertEqual(catalog.count, "2 tools")
        self.assertEqual(catalog.featured, [])
        self.assertEqual(catalog.root.select("section", identity="featured"), [])
        self.assertEqual(catalog.root.select("span", "tag"), [])
        pages = rendered_tool_pages(pinned)
        dtu_page = ToolPage(pages[f"tools/{slug}/index.html"])
        self.assertEqual(dtu_page.pills, [])
        self.assertEqual(dtu_page.facts["Category"], "Test environments")
        unclassified_page = ToolPage(pages[f"tools/{unclassified_slug}/index.html"])
        self.assertEqual(unclassified_page.pills, [])
        self.assertEqual(unclassified_page.facts["Category"], "Other")

    def test_empty_catalog_retains_zero_recommendation_state(self) -> None:
        empty = self.root / "empty"
        write_json(empty / "categories.json", {"categories": [CATEGORY]})
        catalog = CatalogPage(rendered_catalog(empty))
        self.assertEqual(catalog.rows, [])
        self.assertEqual(catalog.featured, [])
        self.assertEqual(catalog.root.select("article"), [])
        self.assertEqual(catalog.root.select("section", identity="featured"), [])
        self.assertEqual(catalog.count, "0 tools")
        self.assertEqual(catalog.chips, [ALL_CHIP])
        self.assertIn("hidden", catalog.root.one("div", identity="empty-results").attrs)
        self.assertEqual(rendered_tool_pages(empty), {})

    def test_selected_sources_keep_preference_when_upstream_advances(self) -> None:
        advanced = self.root / "advanced"
        write_json(advanced / "categories.json", read_json(ROOT / "categories.json", ROOT))
        original_listings = {}
        for slug in CURRENT_SELECTIONS:
            entry = advanced / "tools" / slug
            entry.mkdir(parents=True)
            for name in ("source.json", "listing.json", "provenance.json", "SMART_TOOL.md"):
                (entry / name).write_bytes((ROOT / "tools" / slug / name).read_bytes())
            original_listings[slug] = (entry / "listing.json").read_bytes()
            provenance = read_json(entry / "provenance.json", advanced)
            provenance["source"]["commit"] = "b" * 40
            write_json(entry / "provenance.json", provenance)
        catalog = CatalogPage(rendered_catalog(advanced))
        pages = rendered_tool_pages(advanced)
        self.assertEqual(sorted(row.slug for row in catalog.rows), sorted(CURRENT_SELECTIONS))
        self.assertEqual(sorted(card.slug for card in catalog.featured), sorted(CURRENT_SELECTIONS))
        self.assertEqual(
            [tag.text for tag in catalog.root.select("span", "tag")],
            ["Recommended"] * len(CURRENT_SELECTIONS),
        )
        for row in catalog.rows:
            self.assertEqual(row.marks, MARKS["recommended"])
        for slug in CURRENT_SELECTIONS:
            with self.subTest(tool=slug):
                self.assertEqual((advanced / "tools" / slug / "listing.json").read_bytes(), original_listings[slug])
                page = ToolPage(pages[f"tools/{slug}/index.html"])
                source_url = CURRENT_SELECTIONS[slug]["repository"].removesuffix(".git")
                self.assertEqual(page.pills, ["Recommended"])
                self.assertEqual(page.actions["View on GitHub"], source_url)
                self.assertEqual(page.prompt, f"Go to {source_url} and install it.")
                self.assertEqual(page.sections["Get started."], get_started(source_url))
                # Neither the advanced commit nor the one recorded before it reaches the page.
                self.assert_omits_snapshot_source(
                    page, read_json(advanced / "tools" / slug / "provenance.json", advanced)
                )
                self.assert_omits_snapshot_source(
                    page, read_json(ROOT / "tools" / slug / "provenance.json", ROOT)
                )

    def test_real_catalog_renders_recorded_states_including_drift(self) -> None:
        # Refresh may advance live snapshots without renewing editorial review.
        # Derive expected markers and preference from the shared identity helper.
        categories, _ = load_catalog_metadata(ROOT)
        recorded = recorded_tools(ROOT)
        catalog = CatalogPage(rendered_catalog(ROOT))
        ordered = sorted(recorded, key=lambda slug: (recorded[slug].name.casefold(), slug))
        recommended = [slug for slug in ordered if recorded[slug].state == "recommended"]
        self.assertEqual([row.slug for row in catalog.rows], ordered)
        self.assertEqual([card.slug for card in catalog.featured], recommended)
        self.assertLessEqual(set(recommended), set(CURRENT_SELECTIONS))
        self.assertEqual(len(catalog.root.select("section", identity="featured")), 1 if recommended else 0)
        self.assertEqual(len(catalog.root.select("article")), len(ordered) + len(recommended))
        self.assertEqual(catalog.count, tool_count(len(recorded)))
        for shown in (*catalog.rows, *catalog.featured):
            tool = recorded[shown.slug]
            with self.subTest(tool=shown.slug):
                self.assertEqual(shown.name, tool.name)
                self.assertEqual(shown.tagline, tool.tagline)
                self.assertEqual(shown.links, [f"./tools/{shown.slug}/"] * 2)
                self.assertEqual(shown.get_label, f"Get {tool.name}")
        for row in catalog.rows:
            tool = recorded[row.slug]
            with self.subTest(row=row.slug):
                self.assertEqual(row.category, tool.category)
                self.assertEqual(row.marks, MARKS[tool.state])
                # The script lowercases the query, never the indexed text.
                self.assertEqual(row.search, row.search.lower())
                self.assertIn(tool.name.lower(), row.search)
                self.assertTrue(row.search.endswith(f" {tool.label.lower()}"))
        for card in catalog.featured:
            self.assertEqual(card.marks, [])
        populated = {
            tool.category: tool.label for tool in recorded.values() if tool.category != UNCLASSIFIED
        }
        chips = [ALL_CHIP] + [
            (identity, label, "false")
            for identity, label in sorted(populated.items(), key=lambda item: item[1].casefold())
        ]
        if any(tool.category == UNCLASSIFIED for tool in recorded.values()):
            chips.append(OTHER_CHIP)
        self.assertEqual(catalog.chips, chips)
        self.assertEqual(len(categories), 10)
        self.assertEqual(set(populated), set(categories))
        self.assertEqual(set(catalog.root.identities().values()), {1})

    def test_build_listings_writes_one_page_per_real_listing(self) -> None:
        recorded = recorded_tools(ROOT)
        pages = rendered_tool_pages(ROOT)
        self.assertEqual(
            set(pages), {f"tools/{slug}/index.{kind}" for slug in recorded for kind in ("html", "md")}
        )
        catalog = CatalogPage(rendered_catalog(ROOT))
        self.assertEqual(
            {link for shown in (*catalog.rows, *catalog.featured) for link in shown.links},
            {f"./{path.removesuffix('index.html')}" for path in pages if path.endswith(".html")},
        )
        for slug, tool in recorded.items():
            with self.subTest(tool=slug):
                page = ToolPage(pages[f"tools/{slug}/index.html"])
                self.assertEqual(page.title, f"{tool.name} | Amplifier Smart Tools catalog")
                self.assertEqual(
                    page.assets,
                    [
                        "../../assets/favicon.svg",
                        "./index.md",
                        f"{CATALOG_URL}llms.txt",
                        "../../assets/style.css",
                        "../../assets/site.js",
                    ],
                )
                self.assertEqual(
                    [(link.attrs["rel"], link.attrs.get("type")) for link in page.root.select("link")],
                    [
                        ("icon", "image/svg+xml"),
                        ("alternate", "text/markdown"),
                        ("describedby", "text/plain"),
                        ("stylesheet", None),
                    ],
                )
                self.assertEqual(page.name, tool.name)
                self.assertEqual(page.tagline, tool.tagline)
                self.assertEqual(page.pills, PILLS[tool.state])
                self.assertEqual(
                    page.header,
                    [*(["status-pill"] if page.pills else []), "h1", "facts", "standfirst", "actions"],
                )
                self.assertEqual(page.facts["Category"], tool.label)
                self.assertEqual(page.facts["Publisher"], tool.publisher)
                self.assertEqual(page.facts.get("Version"), tool.version)
                self.assertEqual(page.actions["Get"], "#get-started")
                self.assertEqual(page.actions["View on GitHub"], tool.source_url)
                self.assertEqual(page.prompt, f"Go to {tool.source_url} and install it.")
                self.assertEqual(page.sections["Get started."], get_started(tool.source_url))
                self.assertEqual(page.use_cases, tool.use_cases[:6])
                self.assertEqual("Use it to." in page.sections, bool(tool.use_cases))
                self.assertEqual(
                    page.layout,
                    ["store-head", "get-started"]
                    + [
                        heading
                        for heading in ("Use it to.", "What it does.", "More tools.")
                        if heading in page.sections
                    ],
                )
                self.assert_omits_snapshot_source(page, tool.provenance)
                for other in page.more:
                    self.assertIn(other.slug, recorded)
                    self.assertNotEqual(other.slug, slug)
                    self.assertEqual(other.links, [f"../{other.slug}/"] * 2)
                self.assertEqual(set(page.root.identities().values()), {1})
                copy_page = MarkdownPage(pages[f"tools/{slug}/index.md"])
                self.assertEqual(copy_page.name, tool.name)
                self.assertTrue(" ".join(copy_page.description.split()).startswith(tool.tagline))
                facts = {
                    "Status": "Recommended" if tool.state == "recommended" else None,
                    "Category": tool.label,
                    "Platforms": page.facts["Platform"] if page.facts["Platform"] != "Not declared" else None,
                    "Publisher": tool.publisher,
                    "Version": tool.version,
                    "Source": tool.source_url,
                }
                self.assertEqual(
                    list(copy_page.facts.items()),
                    [(term, value) for term, value in facts.items() if value],
                )
                self.assertEqual(copy_page.prompt, f"Go to {tool.source_url} and install it.")
                self.assertEqual([" ".join(case.split()) for case in copy_page.use_cases], tool.use_cases)
                self.assertEqual(
                    copy_page.layout,
                    [f"# {tool.name}", "## Get started", *(["## Use it to"] if tool.use_cases else [])],
                )

    def test_website_build_writes_llms_txt_that_lists_every_real_listing_by_category(self) -> None:
        renderer = load_renderer()
        out = self.root / "generated"
        with patch.object(sys, "argv", ["build.py", "--output", str(out)]), redirect_stdout(io.StringIO()):
            renderer.main()
        document = (out / "llms.txt").read_text(encoding="utf-8")
        self.assertEqual(document, renderer.catalog_llms(SITE, ARGS, ROOT))
        self.assertEqual(
            document.splitlines()[:5],
            [
                "# Amplifier Smart Tools catalog",
                "",
                f"> {SITE['description']}",
                "",
                f"To let an agent find and install these tools, give it this prompt: {renderer.FAMILY_PROMPT}",
            ],
        )
        recorded = recorded_tools(ROOT)
        ordered = sorted(recorded, key=lambda slug: (recorded[slug].name.casefold(), slug))
        recommended = [slug for slug in ordered if recorded[slug].state == "recommended"]
        labels = sorted(
            {tool.label for tool in recorded.values()}, key=lambda label: (label == "Other", label.casefold())
        )
        expected = {"Recommended": recommended} if recommended else {}
        expected.update({label: [slug for slug in ordered if recorded[slug].label == label] for label in labels})
        sections = llms_sections(document)
        self.assertEqual(list(sections), list(expected))
        for title, items in sections.items():
            with self.subTest(section=title):
                self.assertEqual(
                    [(name, url, " ".join(notes.split())) for name, url, notes in items],
                    [
                        (recorded[slug].name, f"{CATALOG_URL}tools/{slug}/index.md", recorded[slug].tagline)
                        for slug in expected[title]
                    ],
                )
                for _, url, _ in items:
                    self.assertTrue((out / url.removeprefix(CATALOG_URL)).is_file(), url)
        self.assertEqual(
            {path.relative_to(out).as_posix() for path in out.rglob("index.md")},
            {f"tools/{slug}/index.md" for slug in recorded},
        )
        index = parse((out / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(
            [(link.attrs["rel"], link.attrs["href"]) for link in index.select("link")],
            [
                ("icon", "./assets/favicon.svg"),
                ("describedby", f"{CATALOG_URL}llms.txt"),
                ("stylesheet", "./assets/style.css"),
            ],
        )


if __name__ == "__main__":
    unittest.main()