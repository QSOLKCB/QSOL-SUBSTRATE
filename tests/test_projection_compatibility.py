import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from projection_core import compatibility_fingerprint, compatibility_mismatches  # noqa: E402


def identity(**updates):
    value = {
        "type": "qsol-model-projection-compatibility",
        "schema_version": "1.0.0",
        "projection_kind": "kv_cache",
        "model_id": "example/model",
        "model_revision": "revision-1",
        "architecture": "ExampleForCausalLM",
        "tokenizer_id": "example/tokenizer",
        "tokenizer_sha256": "d" * 64,
        "context_length": 32768,
        "hidden_size": 4096,
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "kv_layout_version": "v1",
        "tensor_dtype": "float16",
        "kv_cache_dtype": "float16",
        "quantization_id": "none",
    }
    value.update(updates)
    return value


class ProjectionCompatibilityTests(unittest.TestCase):
    def test_projection_kind_change_invalidates(self):
        expected = identity()
        actual = identity(projection_kind="lora")
        self.assertIn("projection_kind", compatibility_mismatches(expected, actual))
        self.assertNotEqual(compatibility_fingerprint(expected), compatibility_fingerprint(actual))

    def test_model_revision_change_invalidates(self):
        self.assertIn("model_revision", compatibility_mismatches(identity(), identity(model_revision="revision-2")))

    def test_kv_layout_change_invalidates(self):
        self.assertIn("kv_layout_version", compatibility_mismatches(identity(), identity(kv_layout_version="v2")))

    def test_tensor_dtype_change_invalidates(self):
        self.assertIn("tensor_dtype", compatibility_mismatches(identity(), identity(tensor_dtype="bfloat16")))

    def test_kv_cache_dtype_change_invalidates(self):
        self.assertIn("kv_cache_dtype", compatibility_mismatches(identity(), identity(kv_cache_dtype="bfloat16")))

    def test_quantization_change_invalidates(self):
        expected = identity()
        actual = identity(quantization_id="q4_k_m")
        self.assertIn("quantization_id", compatibility_mismatches(expected, actual))
        self.assertNotEqual(compatibility_fingerprint(expected), compatibility_fingerprint(actual))


if __name__ == "__main__":
    unittest.main()
