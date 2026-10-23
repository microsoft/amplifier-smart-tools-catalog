"""Regression checks for preview retention and trusted-main publication gates."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml


WORKFLOW = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "website.yml").read_text()
UPLOAD_PAGES_ARTIFACT = "actions/upload-pages-artifact@"


def condition(job: str, **overrides: object) -> bool:
    """Evaluate the workflow's own boolean condition, not a duplicated policy."""
    match = re.search(rf"(?m)^  {job}:\n    if: >-\n((?:      .*\n)+)", WORKFLOW)
    assert match, f"Missing folded {job} condition"
    expression = " ".join(line.strip() for line in match[1].splitlines())
    expression = expression.replace("&&", " and ").replace("||", " or ")
    values = {
        "event_name": "push",
        "ref": "refs/heads/main",
        "publish": False,
    }
    values.update(overrides)
    github = SimpleNamespace(event_name=values["event_name"], ref=values["ref"])
    return bool(eval(expression, {"__builtins__": {}}, {
        "github": github,
        "inputs": SimpleNamespace(publish=values["publish"]),
    }))


class WebsiteWorkflowTests(unittest.TestCase):
    def test_main_push_deploys_built_revision(self) -> None:
        self.assertTrue(condition("deploy", event_name="push"))
        self.assertFalse(condition("deploy", event_name="push", ref="refs/heads/feature"))
        self.assertIn("needs: build", WORKFLOW)
        self.assertNotIn("actions/download-artifact", WORKFLOW)
        self.assertNotIn("workflow_run", WORKFLOW)
        self.assertNotIn("pull_request_target", WORKFLOW)

    def test_prs_and_manual_branch_previews_never_deploy(self) -> None:
        self.assertFalse(condition("deploy", event_name="pull_request", ref="refs/pull/1/merge", publish=True))
        self.assertFalse(condition("deploy", event_name="workflow_dispatch", ref="refs/heads/feature", publish=True))
        self.assertFalse(condition("deploy", event_name="workflow_dispatch", publish=False))
        self.assertTrue(condition("deploy", event_name="workflow_dispatch", publish=True))

    def test_metadata_scripts_tests_and_review_artifacts_are_included(self) -> None:
        for path in ("'categories.json'", "'scripts/**'", "'tests/**'", "'tools/**'", "'site/**'"):
            self.assertEqual(WORKFLOW.count(path), 2, path)
        self.assertIn(UPLOAD_PAGES_ARTIFACT, WORKFLOW)
        self.assertIn("retention-days: 7", WORKFLOW)
        self.assertIn("persist-credentials: false", WORKFLOW)

    def test_actions_are_pinned_to_commit_shas(self) -> None:
        for action in re.findall(r"uses: (\S+)", WORKFLOW):
            with self.subTest(action=action):
                self.assertRegex(action, r"@[0-9a-f]{40}$")

    def test_workflow_yaml_parses_with_category_triggers_and_preview_retention(self) -> None:
        # BaseLoader keeps the GitHub Actions "on" key rather than treating it
        # as a YAML 1.1 boolean. Existing condition tests exercise trust gates.
        workflow = yaml.load(WORKFLOW, Loader=yaml.BaseLoader)
        for event in ("push", "pull_request"):
            self.assertIn("categories.json", workflow["on"][event]["paths"])
        steps = workflow["jobs"]["build"]["steps"]
        upload = next(step for step in steps if step.get("uses", "").startswith(UPLOAD_PAGES_ARTIFACT))
        self.assertEqual(upload["with"]["retention-days"], "7")
        self.assertEqual(upload["with"]["path"], "_site")
        self.assertEqual(workflow["jobs"]["deploy"]["needs"], "build")


if __name__ == "__main__":
    unittest.main()
