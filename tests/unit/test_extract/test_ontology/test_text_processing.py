"""
Unit tests for text processing and segmentation.

Tests that text is properly split into sentences for ontology matching,
including NLTK tokenization and TextSegment creation.
"""

import pytest
from trustgraph.extract.kg.ontology.text_processor import TextProcessor, TextSegment


@pytest.fixture
def text_processor():
    """Create a TextProcessor instance for testing."""
    return TextProcessor()


class TestTextSegmentation:
    """Test suite for text segmentation functionality."""

    def test_segment_single_sentence(self, text_processor):
        """Test segmentation of a single sentence."""
        text = "This is a simple sentence."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # Filter to only sentences
        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 1, "Single sentence should produce one sentence segment"
        assert text in sentences[0].text, "Segment text should contain input"

    def test_segment_multiple_sentences(self, text_processor):
        """Test segmentation of multiple sentences."""
        text = "First sentence. Second sentence. Third sentence."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # Filter to only sentences
        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 3, "Should create three sentence segments for three sentences"
        assert "First sentence" in sentences[0].text
        assert "Second sentence" in sentences[1].text
        assert "Third sentence" in sentences[2].text

    def test_segment_positions(self, text_processor):
        """Test that segment positions are tracked."""
        text = "First sentence. Second sentence."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # Filter to only sentences
        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 2
        assert sentences[0].position == 0
        assert sentences[1].position > 0

    def test_segment_empty_text(self, text_processor):
        """Test handling of empty text."""
        text = ""

        segments = text_processor.process_chunk(text, extract_phrases=False)

        assert len(segments) == 0, "Empty text should produce no segments"

    def test_segment_whitespace_only(self, text_processor):
        """Test handling of whitespace-only text."""
        text = "   \n\t  "

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # May produce empty segments or no segments depending on implementation
        assert len(segments) <= 1, "Whitespace-only text should produce minimal segments"

    def test_segment_with_newlines(self, text_processor):
        """Test segmentation of text with newlines."""
        text = "First sentence.\nSecond sentence."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # Filter to only sentences
        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 2
        assert "First sentence" in sentences[0].text
        assert "Second sentence" in sentences[1].text

    def test_segment_complex_punctuation(self, text_processor):
        """Test segmentation with complex punctuation."""
        text = "Dr. Smith went to the U.S.A. yesterday. He met Mr. Jones."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # Filter to only sentences
        sentences = [s for s in segments if s.type == 'sentence']
        # NLTK should handle abbreviations correctly
        assert len(sentences) == 2, "Should recognize abbreviations and not split on them"
        assert "Dr. Smith" in sentences[0].text
        assert "Mr. Jones" in sentences[1].text

    def test_segment_question_and_exclamation(self, text_processor):
        """Test segmentation with different sentence terminators."""
        text = "Is this working? Yes, it is! Great news."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # Filter to only sentences
        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 3
        assert "Is this working?" in sentences[0].text
        assert "Yes, it is!" in sentences[1].text
        assert "Great news" in sentences[2].text

    def test_segment_long_paragraph(self, text_processor):
        """Test segmentation of a longer paragraph."""
        text = (
            "The recipe requires several ingredients. "
            "First, gather flour and sugar. "
            "Then, add eggs and milk. "
            "Finally, mix everything together."
        )

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # Filter to only sentences
        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 4, "Should split paragraph into individual sentences"
        assert all(isinstance(seg, TextSegment) for seg in sentences)

    def test_extract_phrases_option(self, text_processor):
        """Test that phrase extraction can be enabled."""
        text = "The recipe requires several ingredients."

        # With phrases
        segments_with_phrases = text_processor.process_chunk(text, extract_phrases=True)
        # Without phrases
        segments_without_phrases = text_processor.process_chunk(text, extract_phrases=False)

        # With phrases should have more segments (sentences + phrases)
        assert len(segments_with_phrases) >= len(segments_without_phrases)


class TestTextSegmentCreation:
    """Test suite for TextSegment object creation."""

    def test_text_segment_attributes(self, text_processor):
        """Test that TextSegment objects have correct attributes."""
        text = "This is a test sentence."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        assert len(segments) >= 1
        segment = segments[0]

        assert hasattr(segment, 'text'), "Segment should have text attribute"
        assert hasattr(segment, 'type'), "Segment should have type attribute"
        assert hasattr(segment, 'position'), "Segment should have position attribute"
        assert segment.type in ['sentence', 'phrase', 'noun_phrase', 'verb_phrase']

    def test_text_segment_types(self, text_processor):
        """Test that different segment types are created correctly."""
        text = "The recipe requires several ingredients."

        # Without phrases
        segments = text_processor.process_chunk(text, extract_phrases=False)
        types = set(s.type for s in segments)
        assert 'sentence' in types, "Should create sentence segments"

        # With phrases
        segments = text_processor.process_chunk(text, extract_phrases=True)
        types = set(s.type for s in segments)
        assert 'sentence' in types, "Should create sentence segments"
        # May also have phrase types

    def test_text_segment_sentence_tracking(self, text_processor):
        """Test that segments track their parent sentence."""
        text = "This is a test sentence."

        segments = text_processor.process_chunk(text, extract_phrases=True)

        # Phrases should reference their parent sentence
        phrases = [s for s in segments if s.type != 'sentence']
        if phrases:
            for phrase in phrases:
                # parent_sentence may be set for phrases
                assert hasattr(phrase, 'parent_sentence')


class TestNLTKCompatibility:
    """Test suite for NLTK version compatibility."""

    def test_nltk_punkt_availability(self, text_processor):
        """Test that NLTK punkt tokenizer is available."""
        # This test verifies the text_processor can use NLTK
        # If punkt/punkt_tab is not available, this will fail during setup
        import nltk

        # Try to use sentence tokenizer
        text = "Test sentence. Another sentence."

        try:
            from nltk.tokenize import sent_tokenize
            result = sent_tokenize(text)
            assert len(result) > 0, "NLTK sentence tokenizer should work"
        except LookupError:
            pytest.fail("NLTK punkt tokenizer not available")

    def test_text_processor_uses_nltk(self, text_processor):
        """Test that TextProcessor successfully uses NLTK for segmentation."""
        # This verifies the integration works
        text = "First sentence. Second sentence."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # Should successfully segment using NLTK
        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) >= 1, "Should successfully segment text using NLTK"


class TestEdgeCases:
    """Test suite for edge cases in text processing."""

    def test_sentence_with_only_punctuation(self, text_processor):
        """Test handling of unusual punctuation patterns."""
        text = "...!?!"

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # Should handle gracefully (NLTK may split this oddly, that's ok)
        assert len(segments) <= 3, "Should handle punctuation-only text gracefully"

    def test_very_long_sentence(self, text_processor):
        """Test handling of very long sentences."""
        # Create a long sentence with many clauses
        text = (
            "This is a very long sentence with many clauses, "
            "including subordinate clauses, coordinate clauses, "
            "and various other grammatical structures that make it "
            "quite lengthy but still technically a single sentence."
        )

        segments = text_processor.process_chunk(text, extract_phrases=False)

        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 1, "Long sentence should still be one sentence segment"
        assert len(sentences[0].text) > 100

    def test_unicode_text(self, text_processor):
        """Test handling of unicode characters."""
        text = "Café serves crêpes. The recipe is français."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 2
        assert "Café" in sentences[0].text
        assert "français" in sentences[1].text

    def test_numbers_and_dates(self, text_processor):
        """Test handling of numbers and dates in text."""
        text = "The recipe was created on Jan. 1, 2024. It serves 4-6 people."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 2
        assert "2024" in sentences[0].text
        assert "4-6" in sentences[1].text

    def test_ellipsis_handling(self, text_processor):
        """Test handling of ellipsis in text."""
        text = "First sentence... Second sentence."

        segments = text_processor.process_chunk(text, extract_phrases=False)

        # NLTK may handle ellipsis differently
        assert len(segments) >= 1, "Should produce at least one segment"
        # The exact behavior depends on NLTK version

    def test_quoted_text(self, text_processor):
        """Test handling of quoted text."""
        text = 'He said "Hello world." Then he left.'

        segments = text_processor.process_chunk(text, extract_phrases=False)

        sentences = [s for s in segments if s.type == 'sentence']
        assert len(sentences) == 2
        assert '"Hello world."' in sentences[0].text or "Hello world" in sentences[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
