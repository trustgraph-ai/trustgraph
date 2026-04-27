from trustgraph.i18n import get_language_pack, get_translator, normalize_language


def test_normalize_language_handles_regions_and_accept_language():
    assert normalize_language(None) == "en"
    assert normalize_language("") == "en"

    assert normalize_language("es-ES") == "es"
    assert normalize_language("pt-BR") == "pt"
    assert normalize_language("zh") == "zh-cn"

    assert normalize_language("es-ES,es;q=0.9,en;q=0.8") == "es"
    assert normalize_language("unknown") == "en"


def test_language_pack_loads_from_resources():
    pack = get_language_pack("en")
    assert isinstance(pack, dict)

    # Key should exist and map to a non-empty string.
    title = pack.get("cli.verify_system_status.title")
    assert isinstance(title, str)
    assert title.strip() != ""


def test_translator_formats_placeholders():
    tr = get_translator("en")
    out = tr.t(
        "cli.verify_system_status.checking_attempt",
        name="Pulsar",
        attempt=2,
    )

    assert "Pulsar" in out
    assert "2" in out


def test_translator_falls_back_to_key_for_unknown_keys():
    tr = get_translator("en")
    assert tr.t("missing.key") == "missing.key"
