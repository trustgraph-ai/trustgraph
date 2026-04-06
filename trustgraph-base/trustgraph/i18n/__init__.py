"""Minimal i18n support for TrustGraph.

This module intentionally stays lightweight:
- No runtime translation calls
- Translations are pre-generated and shipped as language packs

Consumers (CLI/API/Workbench) select a language code (e.g. "es") and
use `Translator.t(key, **kwargs)` to format localized strings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Mapping, Optional

import importlib.resources as importlib_resources


SUPPORTED_LANGUAGES: Mapping[str, str] = {
    "en": "English",
    "es": "Spanish",
    "sw": "Swahili",
    "pt": "Portuguese",
    "tr": "Turkish",
    "hi": "Hindi",
    "he": "Hebrew",
    "ar": "Arabic",
    "zh-cn": "Chinese (simplified)",
    "ru": "Russian",
}

_LANGUAGE_ALIASES: Mapping[str, str] = {
    "zh": "zh-cn",
    "zh-hans": "zh-cn",
    "zh-hans-cn": "zh-cn",
    "zh-cn": "zh-cn",
    "zh_cn": "zh-cn",
}


def normalize_language(value: Optional[str]) -> str:
    """Normalize language inputs to our supported codes.

    Accepts:
    - Simple codes: "es"
    - Region tags: "es-ES", "en-US"
    - Accept-Language style: "es-ES,es;q=0.9,en;q=0.8"

    Falls back to "en" when unknown.
    """

    if not value:
        return "en"

    # Accept-Language: take first entry
    token = value.split(",", 1)[0].strip()
    if not token:
        return "en"

    token = token.replace("_", "-").lower()

    # Exact alias mapping
    if token in _LANGUAGE_ALIASES:
        token = _LANGUAGE_ALIASES[token]

    # Collapse common regional tags
    if token.startswith("en-"):
        token = "en"
    elif token.startswith("es-"):
        token = "es"
    elif token.startswith("pt-"):
        token = "pt"
    elif token.startswith("tr-"):
        token = "tr"
    elif token.startswith("hi-"):
        token = "hi"
    elif token.startswith("he-"):
        token = "he"
    elif token.startswith("ar-"):
        token = "ar"
    elif token.startswith("sw-"):
        token = "sw"
    elif token.startswith("ru-"):
        token = "ru"
    elif token.startswith("zh-"):
        token = "zh-cn"

    # Otherwise use primary subtag
    primary = token.split("-", 1)[0]
    if primary in SUPPORTED_LANGUAGES:
        return primary

    if token in SUPPORTED_LANGUAGES:
        return token

    return "en"


@lru_cache(maxsize=32)
def get_language_pack(language: str) -> Dict[str, str]:
    """Load the language pack for `language` from package resources."""

    lang = normalize_language(language)

    try:
        with importlib_resources.open_text(
            "trustgraph.i18n.packs", f"{lang}.json", encoding="utf-8"
        ) as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    if not isinstance(data, dict):
        return {}

    # Ensure values are strings
    out: Dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


@dataclass(frozen=True)
class Translator:
    language: str

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate `key` using the current language pack.

        Falls back to English pack, then the key itself.
        Supports `.format(**kwargs)` placeholder substitution.
        """

        lang = normalize_language(self.language)
        pack = get_language_pack(lang)
        fallback = get_language_pack("en")

        template = pack.get(key) or fallback.get(key) or key
        if not kwargs:
            return template

        try:
            return template.format(**kwargs)
        except Exception:
            # If formatting fails, return the untranslated template
            return template


def get_translator(language: Optional[str]) -> Translator:
    return Translator(language=normalize_language(language))
