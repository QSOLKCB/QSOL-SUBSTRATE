#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected exactly one replacement target, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_empirical_core() -> None:
    replace_once(
        "tools/mixed_register_empirical.py",
        '''DEFAULT_THRESHOLDS = {
    "primary_status_accuracy_min": 0.90,
    "register_accuracy_min": 0.90,
    "evidence_fidelity_min": 0.80,
    "unsupported_assertion_rate_max": 0.0,
    "per_status_accuracy_min": 0.80,
    "satire_register_accuracy_min": 0.80,
}
WORD_RE = re.compile''',
        '''DEFAULT_THRESHOLDS = {
    "primary_status_accuracy_min": 0.90,
    "register_accuracy_min": 0.90,
    "evidence_fidelity_min": 0.80,
    "unsupported_assertion_rate_max": 0.0,
    "per_status_accuracy_min": 0.80,
    "satire_register_accuracy_min": 0.80,
}
DEFAULT_NUM_PREDICT = 4096
DEFAULT_REQUEST_TIMEOUT_SECONDS = 600
WORD_RE = re.compile''',
    )

    replace_once(
        "tools/mixed_register_empirical.py",
        '''    if vector_cfg.get("top_k") != tool_cfg.get("top_k"):
        raise EmpiricalError("vector and tool-enabled canonical top_k must match")
    return value
''',
        '''    if vector_cfg.get("top_k") != tool_cfg.get("top_k"):
        raise EmpiricalError("vector and tool-enabled canonical top_k must match")
    runner = value.get("default_local_runner")
    if not isinstance(runner, dict):
        raise EmpiricalError("empirical protocol default_local_runner is missing")
    num_predict = runner.get("num_predict")
    timeout_seconds = runner.get("request_timeout_seconds")
    if not isinstance(num_predict, int) or isinstance(num_predict, bool) or num_predict < 1:
        raise EmpiricalError("default_local_runner.num_predict must be a positive integer")
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or timeout_seconds < 1:
        raise EmpiricalError("default_local_runner.request_timeout_seconds must be a positive integer")
    if num_predict > int(runner.get("num_ctx", 0)):
        raise EmpiricalError("default_local_runner.num_predict may not exceed num_ctx")
    return value
''',
    )

    replace_once(
        "tools/mixed_register_empirical.py",
        '''class OllamaClient:
    def __init__(self, base_url: str, model: str, num_ctx: int = 32768, seed: int = 18437):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.seed = seed
''',
        '''class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        num_ctx: int = 32768,
        seed: int = 18437,
        num_predict: int = DEFAULT_NUM_PREDICT,
        request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ):
        if num_ctx < 1:
            raise EmpiricalError("num_ctx must be positive")
        if num_predict < 1 or num_predict > num_ctx:
            raise EmpiricalError("num_predict must be positive and no greater than num_ctx")
        if request_timeout_seconds < 1:
            raise EmpiricalError("request_timeout_seconds must be positive")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.seed = seed
        self.num_predict = num_predict
        self.request_timeout_seconds = request_timeout_seconds
''',
    )

    replace_once(
        "tools/mixed_register_empirical.py",
        '''            with urllib.request.urlopen(request, timeout=1800) as response:
''',
        '''            with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
''',
    )

    replace_once(
        "tools/mixed_register_empirical.py",
        '''                "num_ctx": self.num_ctx,
            },
''',
        '''                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
            },
''',
    )

    replace_once(
        "tools/mixed_register_empirical.py",
        '''            "load_duration": response.get("load_duration"),
            "raw_response_sha256": _sha256(raw.encode("utf-8")),
''',
        '''            "load_duration": response.get("load_duration"),
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
            "request_timeout_seconds": self.request_timeout_seconds,
            "raw_response_sha256": _sha256(raw.encode("utf-8")),
''',
    )


def patch_runner() -> None:
    replace_once(
        "tools/run_mixed_register_empirical.py",
        '''    parser.add_argument("--num-ctx", type=int, default=int(runner_defaults["num_ctx"]))
    parser.add_argument("--seed", type=int, default=int(runner_defaults["seed"]))
''',
        '''    parser.add_argument("--num-ctx", type=int, default=int(runner_defaults["num_ctx"]))
    parser.add_argument("--num-predict", type=int, default=int(runner_defaults["num_predict"]))
    parser.add_argument(
        "--request-timeout-seconds",
        type=int,
        default=int(runner_defaults["request_timeout_seconds"]),
    )
    parser.add_argument("--seed", type=int, default=int(runner_defaults["seed"]))
''',
    )

    replace_once(
        "tools/run_mixed_register_empirical.py",
        '''        client = OllamaClient(args.ollama_url, args.model, num_ctx=args.num_ctx, seed=args.seed)
''',
        '''        client = OllamaClient(
            args.ollama_url,
            args.model,
            num_ctx=args.num_ctx,
            seed=args.seed,
            num_predict=args.num_predict,
            request_timeout_seconds=args.request_timeout_seconds,
        )
''',
    )

    replace_once(
        "tools/run_mixed_register_empirical.py",
        '''                (output_dir / "carriers" / f"{stem}.txt").write_text(carrier, encoding="utf-8")

                raw_payload, provider_meta, raw_text = client.generate(prompt)
''',
        '''                (output_dir / "carriers" / f"{stem}.txt").write_text(carrier, encoding="utf-8")

                print(
                    f"{condition}/{variant}: starting prompt_chars={len(prompt)} "
                    f"num_ctx={args.num_ctx} num_predict={args.num_predict} "
                    f"timeout_seconds={args.request_timeout_seconds}",
                    flush=True,
                )
                raw_payload, provider_meta, raw_text = client.generate(prompt)
''',
    )

    replace_once(
        "tools/run_mixed_register_empirical.py",
        '''        summary["num_ctx"] = args.num_ctx
        summary["top_k"] = args.top_k
''',
        '''        summary["num_ctx"] = args.num_ctx
        summary["num_predict"] = args.num_predict
        summary["request_timeout_seconds"] = args.request_timeout_seconds
        summary["top_k"] = args.top_k
''',
    )


def patch_protocol_and_schema() -> None:
    path = ROOT / "empirical/mixed-register/experiment.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    runner = value["default_local_runner"]
    runner["num_predict"] = 4096
    runner["request_timeout_seconds"] = 600
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    replace_once(
        "schema/mixed-register-empirical-experiment.schema.json",
        '''"required": ["provider","model","temperature","seed","num_ctx","immutable_revision"]''',
        '''"required": ["provider","model","temperature","seed","num_ctx","num_predict","request_timeout_seconds","immutable_revision"]''',
    )
    replace_once(
        "schema/mixed-register-empirical-experiment.schema.json",
        '''        "num_ctx": {"type": "integer", "minimum": 1},
        "immutable_revision": {"type": "string", "minLength": 1}
''',
        '''        "num_ctx": {"type": "integer", "minimum": 1},
        "num_predict": {"type": "integer", "minimum": 1, "maximum": 32768},
        "request_timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 1800},
        "immutable_revision": {"type": "string", "minLength": 1}
''',
    )


def patch_workflow() -> None:
    replace_once(
        ".github/workflows/phase9-empirical-consumer.yml",
        '''      num_ctx:
        description: Ollama context length
        required: false
        default: '32768'
''',
        '''      num_ctx:
        description: Ollama context length
        required: false
        default: '32768'
      num_predict:
        description: Maximum generated tokens per model pass
        required: false
        default: '4096'
      request_timeout_seconds:
        description: Maximum wall-clock seconds per Ollama request
        required: false
        default: '600'
''',
    )
    replace_once(
        ".github/workflows/phase9-empirical-consumer.yml",
        '''      NUM_CTX: ${{ inputs.num_ctx || '32768' }}
      PYTHONUNBUFFERED: '1'
''',
        '''      NUM_CTX: ${{ inputs.num_ctx || '32768' }}
      NUM_PREDICT: ${{ inputs.num_predict || '4096' }}
      REQUEST_TIMEOUT_SECONDS: ${{ inputs.request_timeout_seconds || '600' }}
      PYTHONUNBUFFERED: '1'
''',
    )
    replace_once(
        ".github/workflows/phase9-empirical-consumer.yml",
        '''            --num-ctx "$NUM_CTX" \\
            --source-commit "$(git rev-parse HEAD)" \\
''',
        '''            --num-ctx "$NUM_CTX" \\
            --num-predict "$NUM_PREDICT" \\
            --request-timeout-seconds "$REQUEST_TIMEOUT_SECONDS" \\
            --source-commit "$(git rev-parse HEAD)" \\
''',
    )


def patch_tests() -> None:
    replace_once(
        "tests/test_phase9_empirical.py",
        '''        self._models = models or []
        self._response_text = response_text
''',
        '''        self._models = models or []
        self._response_text = response_text
        self.last_generate_body = None
''',
    )
    replace_once(
        "tests/test_phase9_empirical.py",
        '''        if path == "/api/generate":
            return {
''',
        '''        if path == "/api/generate":
            self.last_generate_body = body
            return {
''',
    )
    replace_once(
        "tests/test_phase9_empirical.py",
        '''        self.assertEqual(exact, raw)
        self.assertEqual(
            metadata["raw_response_sha256"],
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        )
''',
        '''        self.assertEqual(exact, raw)
        self.assertEqual(client.last_generate_body["options"]["num_predict"], 4096)
        self.assertEqual(metadata["num_predict"], 4096)
        self.assertEqual(metadata["request_timeout_seconds"], 600)
        self.assertEqual(
            metadata["raw_response_sha256"],
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        )
''',
    )
    replace_once(
        "tests/test_phase9_empirical.py",
        '''        self.assertTrue(protocol["consumer_contract"]["evidence_reference_violations_fail_gate"])
''',
        '''        self.assertTrue(protocol["consumer_contract"]["evidence_reference_violations_fail_gate"])
        runner = protocol["default_local_runner"]
        self.assertGreater(runner["num_predict"], 0)
        self.assertLessEqual(runner["num_predict"], runner["num_ctx"])
        self.assertGreater(runner["request_timeout_seconds"], 0)
''',
    )
    replace_once(
        "tests/test_phase9_empirical.py",
        '''        self.assertIn("inputs.model || '" + model + "'", workflow)
''',
        '''        self.assertIn("inputs.model || '" + model + "'", workflow)
        self.assertIn("inputs.num_predict || '4096'", workflow)
        self.assertIn("inputs.request_timeout_seconds || '600'", workflow)
        self.assertIn("python -u tools/run_mixed_register_empirical.py", workflow)
''',
    )


def patch_docs_and_changelog() -> None:
    replace_once(
        "docs/MIXED_REGISTER_EMPIRICAL.md",
        '''The runner builds fresh tool-less, vector, and `MIXED-REGISTER/1` bundles from the checked-out commit, resolves the immutable Ollama model digest, performs the ten paired runs, normalises only explicitly visible evidence references, scores each audit with the canonical Phase 9 scorer, and writes `summary.json`.
''',
        '''The runner builds fresh tool-less, vector, and `MIXED-REGISTER/1` bundles from the checked-out commit, resolves the immutable Ollama model digest, performs the ten paired runs, normalises only explicitly visible evidence references, scores each audit with the canonical Phase 9 scorer, and writes `summary.json`.

The canonical local-run defaults cap each response at 4,096 generated tokens and each Ollama request at 600 seconds. Reaching either bound is retained as a consumer/protocol failure for that exact condition; it is not silently retried, extended, or converted into a passing result. These limits prevent one malformed JSON generation from monopolising the complete matrix.
''',
    )
    replace_once(
        "CHANGELOG.md",
        '''- Phase 9 empirical closure adds paired guarded/ablated mixed-register measurement, mechanically derived adjacency traps, false-support/spurious-evidence metrics, and a cold open-weight consumer workflow that remains `derived_evaluation` rather than canonical truth; closure now rejects mixed-run evidence by binding every audit/report to the summary, immutable model/substrate identity, condition/variant, and prompt/carrier/raw hashes.
''',
        '''- Phase 9 empirical closure adds paired guarded/ablated mixed-register measurement, mechanically derived adjacency traps, false-support/spurious-evidence metrics, and a cold open-weight consumer workflow that remains `derived_evaluation` rather than canonical truth; closure rejects mixed-run evidence by binding every audit/report to the summary, immutable model/substrate identity, condition/variant, and prompt/carrier/raw hashes, while canonical runtime limits bound each model pass to 4,096 generated tokens and 600 seconds.
''',
    )


def main() -> None:
    patch_empirical_core()
    patch_runner()
    patch_protocol_and_schema()
    patch_workflow()
    patch_tests()
    patch_docs_and_changelog()
    print("Applied bounded empirical runtime contract.")


if __name__ == "__main__":
    main()
