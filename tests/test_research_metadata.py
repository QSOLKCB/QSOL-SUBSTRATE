from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "1.0.0"
RELEASE_COMMIT = "4483582173abf62f61bcc18076b22c1db10b26ca"
SUBSTRATE_SHA = "fb6e7a694ff1279af67d4aaf776e232e31025d9737011f6768fdc79c0f63eb25"
ORCID = "0009-0002-4515-9237"
RELEASE_URL = "https://github.com/QSOLKCB/QSOL-SUBSTRATE/releases/tag/v1.0.0"


class ResearchMetadataTests(unittest.TestCase):
    def test_zenodo_metadata_is_json_and_targets_exact_release(self):
        metadata = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["upload_type"], "software")
        self.assertEqual(metadata["version"], RELEASE_VERSION)
        self.assertEqual(metadata["license"], "Apache-2.0")
        self.assertEqual(metadata["access_right"], "open")
        self.assertEqual(metadata["creators"][0]["orcid"], ORCID)
        identifiers = {item["identifier"]: item["relation"] for item in metadata["related_identifiers"]}
        self.assertEqual(identifiers[RELEASE_URL], "isIdenticalTo")
        self.assertIn(RELEASE_COMMIT, metadata["notes"])
        self.assertIn(SUBSTRATE_SHA, metadata["notes"])

    def test_zenodo_metadata_contains_ai_discovery_terms(self):
        metadata = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
        keywords = {item.casefold() for item in metadata["keywords"]}
        for term in (
            "large language models",
            "ai context substrate",
            "epistemic provenance",
            "open-world semantics",
            "retrieval-augmented generation",
            "yEAH-NAH/1".casefold(),
            "qsol-substrate",
        ):
            self.assertIn(term.casefold(), keywords)

    def test_citation_cff_binds_release_identity_without_fake_doi(self):
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn("cff-version: 1.2.0", citation)
        self.assertIn(f"version: {RELEASE_VERSION}", citation)
        self.assertIn(f"commit: {RELEASE_COMMIT}", citation)
        self.assertIn(ORCID, citation)
        self.assertIn(RELEASE_URL, citation)
        self.assertNotIn("10.5281/zenodo.", citation)

    def test_codemeta_uses_current_pinned_context_and_exact_release(self):
        metadata = json.loads((ROOT / "codemeta.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["@context"], "https://w3id.org/codemeta/3.1")
        self.assertEqual(metadata["@type"], "SoftwareSourceCode")
        self.assertEqual(metadata["version"], RELEASE_VERSION)
        self.assertEqual(metadata["identifier"], RELEASE_URL)
        self.assertEqual(metadata["author"]["@id"], f"https://orcid.org/{ORCID}")
        self.assertEqual(metadata["codeRepository"], "https://github.com/QSOLKCB/QSOL-SUBSTRATE")

    def test_formalization_is_anchored_and_preserves_core_invariants(self):
        formalization = (ROOT / "FORMALIZATION.md").read_text(encoding="utf-8")
        self.assertIn(RELEASE_COMMIT, formalization)
        self.assertIn(SUBSTRATE_SHA, formalization)
        for invariant in (
            "UNKNOWN != FALSE",
            "CANONICAL_TRUTH != DERIVED_PROJECTION",
            "NEAREST_NEIGHBOR != EVIDENCE",
            "SCORING_ORACLE != EMPIRICAL_MODEL_RESULT",
            "RELEASE_VERSION != SNAPSHOT_IDENTITY",
            "ARCHIVE_DOI != CANONICAL_FACT_AUTHORITY",
        ):
            self.assertIn(invariant, formalization)

    def test_deposition_guide_refuses_retagging_v1(self):
        guide = (ROOT / "ZENODO_DEPOSITION.md").read_text(encoding="utf-8")
        self.assertIn("Do **not** move or recreate the `v1.0.0` tag", guide)
        self.assertIn(RELEASE_COMMIT, guide)
        self.assertIn(SUBSTRATE_SHA, guide)

    def test_followup_release_updates_metadata_before_tagging(self):
        guide = (ROOT / "ZENODO_DEPOSITION.md").read_text(encoding="utf-8")
        self.assertIn("**before creating the tag or GitHub release**", guide)
        self.assertIn("update `.zenodo.json`, `CITATION.cff`, and `codemeta.json`", guide)
        self.assertIn("remove any stale `v1.0.0` exact-commit binding", guide)
        self.assertIn("create the new tag and GitHub release **on that exact metadata commit**", guide)
        self.assertIn("after the release commit SHA is known", guide)
        self.assertIn("A metadata file cannot deterministically embed the SHA of the same Git commit", guide)
        self.assertIn("Never cut a follow-up release while those files still advertise `1.0.0`", guide)


if __name__ == "__main__":
    unittest.main()
