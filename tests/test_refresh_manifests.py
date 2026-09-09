"""Unit tests for scripts/refresh_manifests.py; they do not contact upstreams."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "refresh_manifests.py"
SPEC = importlib.util.spec_from_file_location("refresh_manifests", SCRIPT)
assert SPEC and SPEC.loader
refresh_manifests = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = refresh_manifests
SPEC.loader.exec_module(refresh_manifests)


class RefreshManifestsTests(unittest.TestCase):
    def test_catalog_branding_uses_the_published_repository_and_skill_name(self) -> None:
        catalog_root = SCRIPT.parents[1]
        skill_name = "amplifier-smart-tools-catalog"
        intermediate_skill_name = "amplifier-smart" + "-tools"
        old_repository_name = "amplifier-tools" + "-smart-catalog"
        skill_file = catalog_root / "skills" / skill_name / "SKILL.md"

        self.assertEqual(list((catalog_root / "skills").glob("*/SKILL.md")), [skill_file])
        skill_text = skill_file.read_text()
        self.assertIn(f"name: {skill_name}", skill_text)
        self.assertIn("# Amplifier Smart Tools Catalog", skill_text)
        self.assertIn(
            "https://github.com/robotdad/amplifier-smart-tools-catalog", skill_text
        )

        readme = (catalog_root / "README.md").read_text()
        self.assertIn(f"robotdad/amplifier-smart-tools-catalog", readme)
        self.assertIn(f"--skill {skill_name}", readme)
        self.assertIn(f"skills/{skill_name}/", readme)
        self.assertIn(f"npx skills update {skill_name}", readme)
        self.assertNotIn(old_repository_name, readme)

        discovery_contract = (catalog_root / "contracts" / "discovery.v1.md").read_text()
        self.assertIn(f"skills/{skill_name}/SKILL.md", discovery_contract)
        self.assertIn(f"`{skill_name}`", discovery_contract)
        self.assertNotIn(old_repository_name, discovery_contract)
        self.assertNotRegex(
            "\n".join((readme, discovery_contract, skill_text)),
            rf"(?:name: |--skill |skills/){intermediate_skill_name}(?!-catalog)(?=[\s/`]|$)",
        )

    def test_brian_tool_sources_use_root_main_distributions(self) -> None:
        catalog_root = SCRIPT.parents[1]
        expected_repositories = {
            "home-assistant": "https://github.com/bkrabach/amplifier-smart-tool-home-assistant.git",
            "music-deck": "https://github.com/bkrabach/amplifier-smart-tool-music-deck.git",
        }

        for slug, repository in expected_repositories.items():
            source_file = catalog_root / "tools" / slug / "source.json"
            self.assertEqual(json.loads(source_file.read_text()), {"repository": repository})
            self.assertEqual(
                refresh_manifests.parse_source(source_file),
                refresh_manifests.Source(repository, "main", "."),
            )

    def test_parse_source_defaults_and_rejects_credential_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            source_file = Path(temporary_name) / "source.json"
            source_file.write_text('{"repository": "https://example.test/tool.git"}')
            self.assertEqual(
                refresh_manifests.parse_source(source_file),
                refresh_manifests.Source("https://example.test/tool.git", "main", "."),
            )

            source_file.write_text(
                '{"repository": "https://token@example.test/tool.git", "path": "../tool"}'
            )
            with self.assertRaises(refresh_manifests.RefreshError):
                refresh_manifests.parse_source(source_file)

    def test_prepare_snapshot_preserves_manifest_bytes_and_records_provenance(self) -> None:
        cache = Mock()
        cache.resolve.return_value = (Path("/temporary/source.git"), "a" * 40)
        cache.environment = {}
        cache.timeout = 1
        descriptor = b'{"manifest": "docs/SMART_TOOL.md"}\n'
        manifest = b"# Tool\r\n\nExact bytes.\x00\n"

        with (
            patch.object(refresh_manifests, "object_type", return_value="tree"),
            patch.object(
                refresh_manifests,
                "read_repository_file",
                side_effect=[descriptor, manifest],
            ),
        ):
            prepared = refresh_manifests.prepare_snapshot(
                refresh_manifests.Source("https://example.test/tool.git", "main", "tool"),
                cache,
            )

        self.assertEqual(prepared.manifest, manifest)
        provenance = json.loads(prepared.provenance)
        self.assertEqual(
            provenance["source"],
            {
                "repository": "https://example.test/tool.git",
                "ref": "main",
                "path": "tool",
                "commit": "a" * 40,
            },
        )
        self.assertEqual(provenance["original_manifest_path"], "tool/docs/SMART_TOOL.md")
        self.assertTrue(provenance["last_success"].endswith("Z"))

    def test_prepare_snapshot_rejects_invalid_manifest_location_or_content(self) -> None:
        cache = Mock()
        cache.resolve.return_value = (Path("/temporary/source.git"), "a" * 40)

        with (
            patch.object(refresh_manifests, "object_type", return_value="tree"),
            patch.object(
                refresh_manifests,
                "read_repository_file",
                return_value=b'{"manifest": "notes.md"}',
            ),
        ):
            with self.assertRaisesRegex(refresh_manifests.RefreshError, "SMART_TOOL.md"):
                refresh_manifests.prepare_snapshot(
                    refresh_manifests.Source("https://example.test/tool.git", "main", "tool"),
                    cache,
                )

        with (
            patch.object(refresh_manifests, "object_type", return_value="tree"),
            patch.object(
                refresh_manifests,
                "read_repository_file",
                side_effect=[b'{"manifest": "SMART_TOOL.md"}', b""],
            ),
        ):
            with self.assertRaisesRegex(refresh_manifests.RefreshError, "nonempty"):
                refresh_manifests.prepare_snapshot(
                    refresh_manifests.Source("https://example.test/tool.git", "main", "tool"),
                    cache,
                )

    def test_refresh_keeps_existing_pair_when_preparation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            entry = root / "tools" / "tool"
            entry.mkdir(parents=True)
            (entry / "source.json").write_text('{"repository": "https://example.test/tool.git"}')
            (entry / "SMART_TOOL.md").write_bytes(b"old manifest")
            (entry / "provenance.json").write_bytes(b'{"old": true}\n')
            errors = io.StringIO()

            with (
                patch.object(
                    refresh_manifests,
                    "prepare_snapshot",
                    side_effect=refresh_manifests.RefreshError("requested ref fetch failed"),
                ),
                redirect_stderr(errors),
            ):
                status = refresh_manifests.refresh(root, 1)

            self.assertEqual(status, 1)
            self.assertEqual((entry / "SMART_TOOL.md").read_bytes(), b"old manifest")
            self.assertEqual((entry / "provenance.json").read_bytes(), b'{"old": true}\n')
            self.assertIn("ERROR tool: requested ref fetch failed", errors.getvalue())

    def test_refresh_returns_fatal_code_for_snapshot_output_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            entry = root / "tools" / "tool"
            entry.mkdir(parents=True)
            (entry / "source.json").write_text('{"repository": "https://example.test/tool.git"}')
            errors = io.StringIO()

            with (
                patch.object(
                    refresh_manifests,
                    "prepare_snapshot",
                    return_value=refresh_manifests.PreparedSnapshot(b"manifest", b"provenance"),
                ),
                patch.object(
                    refresh_manifests,
                    "replace_pair",
                    side_effect=refresh_manifests.OutputError("snapshot output failed"),
                ),
                redirect_stderr(errors),
            ):
                status = refresh_manifests.refresh(root, 1)

            self.assertEqual(status, 2)
            self.assertIn("FATAL tool: snapshot output failed", errors.getvalue())

    def test_cache_fetches_a_repository_ref_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            source = refresh_manifests.Source("https://example.test/tool.git", "main", ".")
            commit = b"b" * 40 + b"\n"
            with patch.object(
                refresh_manifests,
                "run_git",
                side_effect=[b"", b"", b"", commit],
            ) as run_git:
                cache = refresh_manifests.RepositoryCache(Path(temporary_name), 1)
                first = cache.resolve(source)
                second = cache.resolve(source)

            self.assertEqual(first, second)
            fetches = [
                call
                for call in run_git.call_args_list
                if call.args[0][:2] == ["fetch", "--no-tags"]
            ]
            self.assertEqual(len(fetches), 1)


if __name__ == "__main__":
    unittest.main()