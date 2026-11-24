"""
Joke Remote Action Service - An example remote action service.

This service demonstrates the remote action service integration by
accepting execution requests with typed parameters and returning
typed artifacts.

Params:
    topic: The topic for the joke (e.g., programming, animals, food)
    style: Joke style (pun, dad-joke, one-liner).  Optional.

Returns:
    TextBlobArtifact with the joke text.

Example remote-action config:
{
    "joke": "{
        \"request-topic\": \"request:tg:joke-action\",
        \"response-topic\": \"response:tg:joke-action\"
    }"
}
"""

import random
import logging

from ... base import RemoteActionService

logger = logging.getLogger(__name__)

default_ident = "joke-action-service"
default_topic = "joke-action"

JOKES = {
    "programming": {
        "pun": [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "Why do Java developers wear glasses? Because they can't C#!",
            "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
        ],
        "dad-joke": [
            "I told my computer I needed a break, and now it won't stop sending me Kit-Kat ads.",
            "I asked my computer for a joke about UDP. I'm not sure if it got it.",
        ],
        "one-liner": [
            "There are only 10 types of people: those who understand binary and those who don't.",
            "99 little bugs in the code, 99 little bugs. Take one down, patch it around, 127 little bugs in the code.",
        ],
    },
    "animals": {
        "pun": [
            "What do you call a fish without eyes? A fsh!",
            "What do you call a bear with no teeth? A gummy bear!",
        ],
        "dad-joke": [
            "What do you call a dog that does magic tricks? A Labracadabrador!",
            "Why do cows wear bells? Because their horns don't work!",
        ],
        "one-liner": [
            "A horse walks into a bar. The bartender asks 'Why the long face?'",
            "What's orange and sounds like a parrot? A carrot!",
        ],
    },
    "default": {
        "pun": [
            "Time flies like an arrow. Fruit flies like a banana!",
            "I used to be a banker, but I lost interest.",
        ],
        "dad-joke": [
            "I'm afraid for the calendar. Its days are numbered.",
            "I only know 25 letters of the alphabet. I don't know y.",
        ],
        "one-liner": [
            "I told my wife she was drawing her eyebrows too high. She looked surprised.",
            "Parallel lines have so much in common. It's a shame they'll never meet.",
        ],
    },
}


def categorise_topic(topic):
    topic = topic.lower()
    if any(w in topic for w in ("program", "code", "computer", "software")):
        return "programming"
    if any(w in topic for w in ("animal", "dog", "cat", "bird")):
        return "animals"
    return "default"


class Processor(RemoteActionService):

    def __init__(self, **params):
        super(Processor, self).__init__(**params)
        logger.info("Joke action service initialized")

    async def execute(self, inputs, user_context):

        topic = inputs.get("topic", {}).get("text", "")
        style = inputs.get("style", {}).get("text", "")

        if not style or style not in ("pun", "dad-joke", "one-liner"):
            style = random.choice(["pun", "dad-joke", "one-liner"])

        category = categorise_topic(topic) if topic else "default"

        jokes = JOKES.get(category, JOKES["default"]).get(
            style, JOKES["default"]["pun"],
        )

        joke = random.choice(jokes)

        logger.info(
            f"Generated joke: style={style}, topic={topic}, "
            f"user={user_context.user_id if user_context else 'anonymous'}"
        )

        return {"output": ("TextBlobArtifact", {"text": joke})}

    @staticmethod
    def add_args(parser):
        RemoteActionService.add_args(parser)
        for action in parser._actions:
            if '--topic' in action.option_strings:
                action.default = default_topic
                break


def run():
    Processor.launch(default_ident, __doc__)
