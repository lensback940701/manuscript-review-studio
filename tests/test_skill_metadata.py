from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillMetadataTests(unittest.TestCase):
    def test_skill_frontmatter_is_bounded_and_named(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        closing = content.find("\n---\n", 4)
        self.assertGreater(closing, 4)
        frontmatter = content[4:closing]
        self.assertRegex(frontmatter, r"(?m)^name: manuscript-revision-closure$")
        self.assertRegex(frontmatter, r"(?m)^description: >-$")
        self.assertNotIn("<", frontmatter)
        self.assertNotIn(">", frontmatter.replace(">-", ""))

    def test_interface_metadata_uses_canonical_invocation(self) -> None:
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Manuscript Revision Closure"', metadata)
        self.assertIn("$manuscript-revision-closure", metadata)
        self.assertRegex(metadata, r"(?m)^policy:\s*$")
        self.assertRegex(metadata, r"(?m)^  allow_implicit_invocation: true\s*$")

    def test_default_prompt_preserves_read_only_closure_scope(self) -> None:
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        prompt_match = re.search(r'(?m)^  default_prompt: "(.+)"$', metadata)
        self.assertIsNotNone(prompt_match)
        prompt = prompt_match.group(1)
        self.assertIn("complete academic manuscript", prompt)
        self.assertIn("stop general AI revision", prompt)
        self.assertIn("concise closure verdict", prompt)


if __name__ == "__main__":
    unittest.main()
