"""
Redact Remote Action Service - A test action service for text redaction.

This service takes a TextBlobArtifact as input and replaces specified
words with [REDACTED].

Inputs:
    text: TextBlobArtifact with text to redact.
    words: TextBlobArtifact with comma-separated list of words to redact.

Returns:
    TextBlobArtifact with redacted text.

Example remote-action config:
{
    "redact": "{
        \"request-topic\": \"request:tg:redact-action\",
        \"response-topic\": \"response:tg:redact-action\"
    }"
}
"""

import re
import logging

from ... base import RemoteActionService

logger = logging.getLogger(__name__)

default_ident = "redact-action-service"
default_topic = "redact-action"


def redact_text(text, words):
    for word in words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub("[REDACTED]", text)
    return text


class Processor(RemoteActionService):

    def __init__(self, **params):
        super(Processor, self).__init__(**params)
        logger.info("Redact action service initialized")

    async def execute(self, inputs, user_context):

        words_param = inputs.get("words", {}).get("text", "")
        words = [w.strip() for w in words_param.split(",") if w.strip()]

        if not words:
            raise ValueError("No words specified for redaction")

        text = inputs.get("text", {}).get("text", "")

        if not text:
            raise ValueError("No text input provided")

        redacted = redact_text(text, words)

        logger.info(
            f"Redacted {len(words)} word(s), "
            f"user={user_context.user_id if user_context else 'anonymous'}"
        )

        return {"output": ("TextBlobArtifact", {"text": redacted})}

    @staticmethod
    def add_args(parser):
        RemoteActionService.add_args(parser)
        for action in parser._actions:
            if '--topic' in action.option_strings:
                action.default = default_topic
                break


def run():
    Processor.launch(default_ident, __doc__)
