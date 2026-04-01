"""
Unit tests for text document gateway translation compatibility.
"""

import base64

from trustgraph.messaging.translators.document_loading import TextDocumentTranslator


class TestTextDocumentTranslator:
    def test_decode_decodes_base64_text(self):
        translator = TextDocumentTranslator()
        payload = "Cancer survival: 2.74× higher hazard ratio"

        msg = translator.decode(
            {
                "id": "doc-1",
                "user": "alice",
                "collection": "research",
                "charset": "utf-8",
                "text": base64.b64encode(payload.encode("utf-8")).decode("ascii"),
            }
        )

        assert msg.metadata.id == "doc-1"
        assert msg.metadata.user == "alice"
        assert msg.metadata.collection == "research"
        assert msg.text == payload.encode("utf-8")

    def test_decode_accepts_raw_utf8_text(self):
        translator = TextDocumentTranslator()
        payload = "Cancer survival: 2.74× higher hazard ratio"

        msg = translator.decode(
            {
                "charset": "utf-8",
                "text": payload,
            }
        )

        assert msg.text == payload.encode("utf-8")

    def test_decode_falls_back_to_raw_non_base64_ascii(self):
        translator = TextDocumentTranslator()
        payload = "plain-text payload"

        msg = translator.decode(
            {
                "charset": "utf-8",
                "text": payload,
            }
        )

        assert msg.text == payload.encode("utf-8")
