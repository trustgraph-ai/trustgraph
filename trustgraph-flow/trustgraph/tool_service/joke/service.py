"""
Joke Tool Service - An example dynamic tool service.

This service demonstrates the tool service integration by:
- Using config params (style) to customize joke style
- Using arguments (topic) to generate topic-specific jokes

Example tool-service config:
{
    "id": "joke-service",
    "topic": "joke",
    "config-params": [
        {"name": "style", "required": false}
    ]
}

Example tool config:
{
    "type": "tool-service",
    "name": "tell-joke",
    "description": "Tell a joke on a given topic",
    "service": "joke-service",
    "style": "pun",
    "arguments": [
        {
            "name": "topic",
            "type": "string",
            "description": "The topic for the joke (e.g., programming, animals, food)"
        }
    ]
}
"""

import random
import logging

from ... base import DynamicToolService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "joke-service"
default_topic = "joke"

# Joke database organized by topic and style
JOKES = {
    "programming": {
        "pun": [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "Why do Java developers wear glasses? Because they can't C#!",
            "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
            "Why was the JavaScript developer sad? Because he didn't Node how to Express himself!",
        ],
        "dad-joke": [
            "I told my computer I needed a break, and now it won't stop sending me Kit-Kat ads.",
            "My son asked me to explain what a linked list is. I said 'I'll tell you, and then I'll tell you again, and again...'",
            "I asked my computer for a joke about UDP. I'm not sure if it got it.",
        ],
        "one-liner": [
            "There are only 10 types of people: those who understand binary and those who don't.",
            "A programmer's wife tells him: 'Go to the store and get a loaf of bread. If they have eggs, get a dozen.' He returns with 12 loaves.",
            "99 little bugs in the code, 99 little bugs. Take one down, patch it around, 127 little bugs in the code.",
        ],
    },
    "llama": {
        "pun": [
            "Why did the llama get a ticket? Because he was caught spitting in a no-spitting zone!",
            "What do you call a llama who's a great musician? A llama del Rey!",
            "Why did the llama cross the road? To prove he wasn't a chicken!",
        ],
        "dad-joke": [
            "What did the llama say when he got kicked out of the zoo? 'Alpaca my bags!'",
            "Why don't llamas ever get lost? Because they always know the way to the Andes!",
            "What do you call a llama with no legs? A woolly rug!",
        ],
        "one-liner": [
            "Llamas are great at meditation. They're always saying 'Dalai Llama.'",
            "I asked a llama for directions. He said 'No probllama!'",
            "Never trust a llama. They're always up to something woolly.",
        ],
    },
    "animals": {
        "pun": [
            "What do you call a fish without eyes? A fsh!",
            "Why don't scientists trust atoms? Because they make up everything... just like that cat who blamed the dog!",
            "What do you call a bear with no teeth? A gummy bear!",
        ],
        "dad-joke": [
            "I tried to catch some fog earlier. I mist. My dog wasn't impressed either.",
            "What do you call a dog that does magic tricks? A Labracadabrador!",
            "Why do cows wear bells? Because their horns don't work!",
        ],
        "one-liner": [
            "I'm reading a book about anti-gravity. It's impossible to put down, unlike my cat.",
            "A horse walks into a bar. The bartender asks 'Why the long face?'",
            "What's orange and sounds like a parrot? A carrot!",
        ],
    },
    "food": {
        "pun": [
            "I'm on a seafood diet. I see food and I eat it!",
            "Why did the tomato turn red? Because it saw the salad dressing!",
            "What do you call cheese that isn't yours? Nacho cheese!",
        ],
        "dad-joke": [
            "I used to hate facial hair, but then it grew on me. Speaking of growing, have you tried my garden salad?",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "I told my wife she was drawing her eyebrows too high. She looked surprised, then made me a sandwich.",
        ],
        "one-liner": [
            "I'm reading a book about submarines and sandwiches. It's a sub-genre.",
            "Broken puppets for sale. No strings attached. Also, free spaghetti!",
            "I ordered a chicken and an egg online. I'll let you know which comes first.",
        ],
    },
    "default": {
        "pun": [
            "Time flies like an arrow. Fruit flies like a banana!",
            "I used to be a banker, but I lost interest.",
            "I'm reading a book on the history of glue. I can't put it down!",
        ],
        "dad-joke": [
            "I'm afraid for the calendar. Its days are numbered.",
            "I only know 25 letters of the alphabet. I don't know y.",
            "Did you hear about the claustrophobic astronaut? He just needed a little space.",
        ],
        "one-liner": [
            "I told my wife she was drawing her eyebrows too high. She looked surprised.",
            "I'm not lazy, I'm on energy-saving mode.",
            "Parallel lines have so much in common. It's a shame they'll never meet.",
        ],
    },
}


class Processor(DynamicToolService):
    """
    Joke tool service that demonstrates the tool service integration.
    """

    def __init__(self, **params):
        super(Processor, self).__init__(**params)
        logger.info("Joke service initialized")

    async def invoke(self, config, arguments):
        """
        Generate a joke based on the topic and style.

        Args:
            config: Config values including 'style' (pun, dad-joke, one-liner)
            arguments: Arguments including 'topic' (programming, animals, food)

        Returns:
            A joke string
        """
        # Get style from config (default: random)
        style = config.get("style", random.choice(["pun", "dad-joke", "one-liner"]))

        # Get topic from arguments (default: random)
        topic = arguments.get("topic", "").lower()

        # Map topic to our categories
        if "program" in topic or "code" in topic or "computer" in topic or "software" in topic:
            category = "programming"
        elif "llama" in topic:
            category = "llama"
        elif "animal" in topic or "dog" in topic or "cat" in topic or "bird" in topic:
            category = "animals"
        elif "food" in topic or "eat" in topic or "cook" in topic or "drink" in topic:
            category = "food"
        else:
            category = "default"

        # Normalize style
        if style not in ["pun", "dad-joke", "one-liner"]:
            style = random.choice(["pun", "dad-joke", "one-liner"])

        # Get jokes for this category and style
        jokes = JOKES.get(category, JOKES["default"]).get(style, JOKES["default"]["pun"])

        # Pick a random joke
        joke = random.choice(jokes)

        response = f"Here's a {style} for you:\n\n{joke}"

        logger.debug(f"Generated joke: style={style}, topic={topic}")

        return response

    @staticmethod
    def add_args(parser):
        DynamicToolService.add_args(parser)
        # Override the topic default for this service
        for action in parser._actions:
            if '--topic' in action.option_strings:
                action.default = default_topic
                break


def run():
    Processor.launch(default_ident, __doc__)
