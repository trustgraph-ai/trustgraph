"""
Text processing components for OntoRAG system.
Splits text into sentences and extracts phrases for granular matching.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import nltk
from nltk.corpus import stopwords

logger = logging.getLogger(__name__)

# Ensure required NLTK data is downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


@dataclass
class TextSegment:
    """Represents a segment of text (sentence or phrase)."""
    text: str
    type: str  # 'sentence', 'phrase', 'noun_phrase', 'verb_phrase'
    position: int
    parent_sentence: Optional[str] = None
    metadata: Dict[str, Any] = None


class SentenceSplitter:
    """Splits text into sentences using NLTK."""

    def __init__(self):
        """Initialize sentence splitter."""
        self.sent_detector = nltk.data.load('tokenizers/punkt/english.pickle')
        logger.info("Using NLTK sentence tokenizer")

    def split(self, text: str) -> List[str]:
        """Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        sentences = self.sent_detector.tokenize(text)
        return sentences


class PhraseExtractor:
    """Extracts meaningful phrases from sentences using NLTK."""

    def __init__(self):
        """Initialize phrase extractor."""
        logger.info("Using NLTK phrase extraction")

    def extract(self, sentence: str) -> List[Dict[str, str]]:
        """Extract phrases from a sentence.

        Args:
            sentence: Sentence to extract phrases from

        Returns:
            List of phrases with their types
        """
        phrases = []

        # Tokenize and POS tag
        tokens = nltk.word_tokenize(sentence)
        pos_tags = nltk.pos_tag(tokens)

        # Extract noun phrases (simple pattern)
        noun_phrase = []
        for word, pos in pos_tags:
            if pos.startswith('NN') or pos.startswith('JJ'):
                noun_phrase.append(word)
            elif noun_phrase:
                if len(noun_phrase) > 1:
                    phrases.append({
                        'text': ' '.join(noun_phrase),
                        'type': 'noun_phrase'
                    })
                noun_phrase = []

        # Add last noun phrase if exists
        if noun_phrase and len(noun_phrase) > 1:
            phrases.append({
                'text': ' '.join(noun_phrase),
                'type': 'noun_phrase'
            })

        # Extract verb phrases (simple pattern)
        verb_phrase = []
        for word, pos in pos_tags:
            if pos.startswith('VB') or pos.startswith('RB'):
                verb_phrase.append(word)
            elif verb_phrase:
                if len(verb_phrase) > 1:
                    phrases.append({
                        'text': ' '.join(verb_phrase),
                        'type': 'verb_phrase'
                    })
                verb_phrase = []

        # Add last verb phrase if exists
        if verb_phrase and len(verb_phrase) > 1:
            phrases.append({
                'text': ' '.join(verb_phrase),
                'type': 'verb_phrase'
            })

        return phrases


class TextProcessor:
    """Main text processing class that coordinates sentence splitting and phrase extraction."""

    def __init__(self):
        """Initialize text processor."""
        self.sentence_splitter = SentenceSplitter()
        self.phrase_extractor = PhraseExtractor()

    def process_chunk(self, chunk_text: str, extract_phrases: bool = True) -> List[TextSegment]:
        """Process a text chunk into segments.

        Args:
            chunk_text: Text chunk to process
            extract_phrases: Whether to extract phrases from sentences

        Returns:
            List of TextSegment objects
        """
        segments = []
        position = 0

        # Split into sentences
        sentences = self.sentence_splitter.split(chunk_text)

        for sentence in sentences:
            # Add sentence segment
            segments.append(TextSegment(
                text=sentence,
                type='sentence',
                position=position
            ))
            position += 1

            # Extract phrases if requested
            if extract_phrases:
                phrases = self.phrase_extractor.extract(sentence)
                for phrase_data in phrases:
                    segments.append(TextSegment(
                        text=phrase_data['text'],
                        type=phrase_data['type'],
                        position=position,
                        parent_sentence=sentence
                    ))
                    position += 1

        logger.debug(f"Processed chunk into {len(segments)} segments")
        return segments

    def extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for matching.

        Args:
            text: Text to extract terms from

        Returns:
            List of key terms
        """
        terms = []

        # Split on word boundaries
        words = re.findall(r'\b\w+\b', text.lower())

        # Use NLTK stopwords
        stop_words = set(stopwords.words('english'))

        # Filter stopwords and short words
        terms = [w for w in words if w not in stop_words and len(w) > 2]

        # Also extract multi-word terms (bigrams)
        for i in range(len(words) - 1):
            if words[i] not in stop_words and words[i+1] not in stop_words:
                bigram = f"{words[i]} {words[i+1]}"
                terms.append(bigram)

        return terms

    def normalize_text(self, text: str) -> str:
        """Normalize text for consistent processing.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        return text
