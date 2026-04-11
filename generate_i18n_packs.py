#!/usr/bin/env python3

"""Generate TrustGraph pre-built language packs using the local Ollama translate model.

This script translates a curated set of UI/CLI strings (keys) from English into
all supported languages and writes JSON packs under:
  trustgraph-base/trustgraph/i18n/packs/

Design goal: no runtime translation. Packs are generated ahead of time and
loaded via `trustgraph.i18n`.

Requires:
- Ollama running locally (default: http://localhost:11434)
- Model available (default: translategemma:12b)

Usage:
  python generate_i18n_packs.py

You can override:
  OLLAMA_URL, OLLAMA_MODEL
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Reuse the hardened translation engine we already use for docs.
import translate_docs


DEFAULT_OUTPUT_DIR = Path("trustgraph-base/trustgraph/i18n/packs")

# 10 languages (including English)
LANGS: Dict[str, Tuple[str, str]] = {
    "en": ("English", "en"),
    "es": ("Spanish", "es"),
    "sw": ("Swahili", "sw"),
    "pt": ("Portuguese", "pt"),
    "tr": ("Turkish", "tr"),
    "hi": ("Hindi", "hi"),
    "he": ("Hebrew", "he"),
    "ar": ("Arabic", "ar"),
    "zh-cn": ("Chinese (simplified)", "zh-cn"),
    "ru": ("Russian", "ru"),
}


# Curated strings currently used by tg-verify-system-status.
# Keep keys stable.
EN_STRINGS: Dict[str, str] = {
    "cli.verify_system_status.title": "TrustGraph System Status Verification",
    "cli.verify_system_status.phase_1": "Phase 1: Infrastructure",
    "cli.verify_system_status.phase_2": "Phase 2: Core Services",
    "cli.verify_system_status.phase_3": "Phase 3: Data Services",
    "cli.verify_system_status.phase_4": "Phase 4: User Interface",
    "cli.verify_system_status.summary": "Summary",
    "cli.verify_system_status.checking": "Checking {name}...",
    "cli.verify_system_status.checking_attempt": "Checking {name}... (attempt {attempt})",
    "cli.verify_system_status.failed_timeout": "{name}: Failed (timeout after {attempt} attempts)",
    "cli.verify_system_status.pulsar_not_responding": "Pulsar is not responding - other checks may fail",
    "cli.verify_system_status.checks_passed": "Checks passed: {passed}/{total}",
    "cli.verify_system_status.checks_failed": "Checks failed: {failed}/{total}",
    "cli.verify_system_status.total_time": "Total time: {elapsed}",
    "cli.verify_system_status.system_healthy": "System is healthy!",
    "cli.verify_system_status.system_failing": "System has {failed} failing check(s)",

    "cli.verify_system_status.check_name.pulsar": "Pulsar",
    "cli.verify_system_status.check_name.api_gateway": "API Gateway",
    "cli.verify_system_status.check_name.processors": "Processors",
    "cli.verify_system_status.check_name.flow_blueprints": "Flow Blueprints",
    "cli.verify_system_status.check_name.flows": "Flows",
    "cli.verify_system_status.check_name.prompts": "Prompts",
    "cli.verify_system_status.check_name.library": "Library",
    "cli.verify_system_status.check_name.workbench_ui": "Workbench UI",

    "cli.verify_system_status.pulsar.healthy": "Pulsar healthy ({clusters} cluster(s))",
    "cli.verify_system_status.pulsar.status": "Pulsar returned status {status_code}",
    "cli.verify_system_status.pulsar.timeout": "Pulsar connection timeout",
    "cli.verify_system_status.pulsar.cannot_connect": "Cannot connect to Pulsar",
    "cli.verify_system_status.pulsar.error": "Pulsar error: {error}",

    "cli.verify_system_status.api_gateway.responding": "API Gateway is responding",
    "cli.verify_system_status.api_gateway.status": "API Gateway returned status {status_code}",
    "cli.verify_system_status.api_gateway.timeout": "API Gateway connection timeout",
    "cli.verify_system_status.api_gateway.cannot_connect": "Cannot connect to API Gateway",
    "cli.verify_system_status.api_gateway.error": "API Gateway error: {error}",

    "cli.verify_system_status.processors.found": "Found {count} processors (≥ {min})",
    "cli.verify_system_status.processors.only": "Only {count} processors running (need {min})",
    "cli.verify_system_status.processors.metrics_status": "Metrics returned status {status_code}",
    "cli.verify_system_status.processors.error": "Processor check error: {error}",

    "cli.verify_system_status.flow_blueprints.found": "Found {count} flow blueprint(s)",
    "cli.verify_system_status.flow_blueprints.none": "No flow blueprints found",
    "cli.verify_system_status.flow_blueprints.error": "Flow blueprints check error: {error}",

    "cli.verify_system_status.flows.responding": "Flow manager responding ({count} flow(s))",
    "cli.verify_system_status.flows.error": "Flow manager check error: {error}",

    "cli.verify_system_status.prompts.found": "Found {count} prompt(s)",
    "cli.verify_system_status.prompts.none": "No prompts found",
    "cli.verify_system_status.prompts.error": "Prompts check error: {error}",

    "cli.verify_system_status.library.responding": "Library responding ({count} document(s))",
    "cli.verify_system_status.library.error": "Library check error: {error}",

    "cli.verify_system_status.ui.responding": "Workbench UI is responding",
    "cli.verify_system_status.ui.status": "UI returned status {status_code}",
    "cli.verify_system_status.ui.timeout": "UI connection timeout",
    "cli.verify_system_status.ui.cannot_connect": "Cannot connect to UI",
    "cli.verify_system_status.ui.error": "UI error: {error}",
}


_FMT_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")


def _protect_format_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    """Replace `{name}` placeholders with CODE-like placeholders that the doc translator preserves."""

    mapping: Dict[str, str] = {}

    def repl(m: re.Match[str]) -> str:
        idx = len(mapping)
        token = f"⟦CODE_{idx}⟧"
        mapping[token] = m.group(0)
        return token

    protected = _FMT_RE.sub(repl, text)
    return protected, mapping


def _restore_format_placeholders(text: str, mapping: Dict[str, str]) -> str:
    out = text
    for token, original in mapping.items():
        out = out.replace(token, original)
    return out


def _validate_placeholders(restored: str, originals: List[str]) -> bool:
    return all(ph in restored for ph in originals)


def translate_pack(client: translate_docs.OllamaClient, *, lang_name: str, lang_code: str) -> Dict[str, str]:
    keys = list(EN_STRINGS.keys())

    protected_lines: List[str] = []
    placeholder_maps: List[Dict[str, str]] = []
    placeholder_originals: List[List[str]] = []

    for k in keys:
        text = EN_STRINGS[k]
        protected, mapping = _protect_format_placeholders(text)
        protected_lines.append(protected + "\n")
        placeholder_maps.append(mapping)
        placeholder_originals.append(list(mapping.values()))

    translated = translate_docs.translate_lines_resilient(
        client,
        lines=protected_lines,
        target_language_name=lang_name,
        target_language_code=lang_code,
        retries=2,
    )

    if translated is None:
        raise RuntimeError(f"Translation failed for {lang_code}")

    out_lines = translated.splitlines()
    if len(out_lines) != len(keys):
        raise RuntimeError(f"Unexpected line count for {lang_code}: {len(out_lines)} != {len(keys)}")

    pack: Dict[str, str] = {}
    for i, k in enumerate(keys):
        restored = _restore_format_placeholders(out_lines[i], placeholder_maps[i])

        # Ensure python-format placeholders survived
        if not _validate_placeholders(restored, placeholder_originals[i]):
            raise RuntimeError(f"Placeholder lost for key {k} in {lang_code}")

        pack[k] = restored

    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory for packs (default: {DEFAULT_OUTPUT_DIR})",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = translate_docs.OllamaClient(
        url=os.getenv("OLLAMA_URL", translate_docs.DEFAULT_OLLAMA_URL),
        model=os.getenv("OLLAMA_MODEL", translate_docs.DEFAULT_OLLAMA_MODEL),
        num_ctx=translate_docs.DEFAULT_NUM_CTX,
        num_predict=translate_docs.DEFAULT_NUM_PREDICT,
        temperature=translate_docs.DEFAULT_TEMPERATURE,
        top_p=translate_docs.DEFAULT_TOP_P,
        repeat_penalty=translate_docs.DEFAULT_REPEAT_PENALTY,
        keep_alive=translate_docs.DEFAULT_KEEP_ALIVE,
    )

    # Always write English as the source pack
    (output_dir / "en.json").write_text(json.dumps(EN_STRINGS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for lang, (name, code) in LANGS.items():
        if lang == "en":
            continue

        print(f"\n=== Generating pack: {lang} ({name}) ===")
        pack = translate_pack(client, lang_name=name, lang_code=code)
        (output_dir / f"{lang}.json").write_text(
            json.dumps(pack, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
