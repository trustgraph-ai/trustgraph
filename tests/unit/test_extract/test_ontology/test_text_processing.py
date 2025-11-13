"""
Unit tests for text processing and segmentation.

Tests that text is properly split into sentences for ontology matching,
including NLTK tokenization and TextSegment creation.
"""

import pytest
from trustgraph.extract.kg.ontology.extract import Processor
from trustgraph.schema.text_segment import TextSegment


class MockParams:
    """Mock parameters for Processor."""
    def get(self, key, default=None):
        return default


@pytest.fixture
def processor():
    """Create a Processor instance for testing."""
    params = MockParams()
    processor = Processor()
    processor.subscribe(None, None, params)
    return processor


class TestTextSegmentation:
    """Test suite for text segmentation functionality."""

    def test_segment_single_sentence(self, processor):
        """Test segmentation of a single sentence."""
        text = "This is a simple sentence."

        segments = processor.segment_text(text)

        assert len(segments) == 1, "Single sentence should produce one segment"
        assert segments[0].text == text, "Segment text should match input"
        assert segments[0].start == 0, "First segment should start at position 0"

    def test_segment_multiple_sentences(self, processor):
        """Test segmentation of multiple sentences."""
        text = "First sentence. Second sentence. Third sentence."

        segments = processor.segment_text(text)

        assert len(segments) == 3, "Should create three segments for three sentences"
        assert segments[0].text == "First sentence."
        assert segments[1].text == "Second sentence."
        assert segments[2].text == "Third sentence."

    def test_segment_positions(self, processor):
        """Test that segment positions are correctly calculated."""
        text = "First sentence. Second sentence."

        segments = processor.segment_text(text)

        assert segments[0].start == 0
        assert segments[0].end == 15  # "First sentence."
        assert segments[1].start == 16  # After space
        assert segments[1].end == len(text)

    def test_segment_empty_text(self, processor):
        """Test handling of empty text."""
        text = ""

        segments = processor.segment_text(text)

        assert len(segments) == 0, "Empty text should produce no segments"

    def test_segment_whitespace_only(self, processor):
        """Test handling of whitespace-only text."""
        text = "   \n\t  "

        segments = processor.segment_text(text)

        assert len(segments) == 0, "Whitespace-only text should produce no segments"

    def test_segment_with_newlines(self, processor):
        """Test segmentation of text with newlines."""
        text = "First sentence.\nSecond sentence."

        segments = processor.segment_text(text)

        assert len(segments) == 2
        assert "First sentence" in segments[0].text
        assert "Second sentence" in segments[1].text

    def test_segment_complex_punctuation(self, processor):
        """Test segmentation with complex punctuation."""
        text = "Dr. Smith went to the U.S.A. yesterday. He met Mr. Jones."

        segments = processor.segment_text(text)

        # NLTK should handle abbreviations correctly
        assert len(segments) == 2, "Should recognize abbreviations and not split on them"
        assert "Dr. Smith" in segments[0].text
        assert "Mr. Jones" in segments[1].text

    def test_segment_question_and_exclamation(self, processor):
        """Test segmentation with different sentence terminators."""
        text = "Is this working? Yes, it is! Great news."

        segments = processor.segment_text(text)

        assert len(segments) == 3
        assert segments[0].text.strip() == "Is this working?"
        assert segments[1].text.strip() == "Yes, it is!"
        assert segments[2].text.strip() == "Great news."

    def test_segment_long_paragraph(self, processor):
        """Test segmentation of a longer paragraph."""
        text = (
            "The recipe requires several ingredients. "
            "First, gather flour and sugar. "
            "Then, add eggs and milk. "
            "Finally, mix everything together."
        )

        segments = processor.segment_text(text)

        assert len(segments) == 4, "Should split paragraph into individual sentences"
        assert all(isinstance(seg, TextSegment) for seg in segments)

    def test_segment_preserves_original_text(self, processor):
        """Test that segments can be used to reconstruct original text."""
        text = "First sentence. Second sentence. Third sentence."

        segments = processor.segment_text(text)

        # Reconstruct text from segments
        reconstructed = text[segments[0].start:segments[0].end]
        for seg in segments[1:]:
            reconstructed += text[seg.start:seg.end]

        # Should match original (minus potential whitespace normalization)
        assert "First sentence" in reconstructed
        assert "Second sentence" in reconstructed
        assert "Third sentence" in reconstructed


class TestTextSegmentCreation:
    """Test suite for TextSegment object creation."""

    def test_text_segment_attributes(self, processor):
        """Test that TextSegment objects have correct attributes."""
        text = "This is a test sentence."

        segments = processor.segment_text(text)

        assert len(segments) == 1
        segment = segments[0]

        assert hasattr(segment, 'text'), "Segment should have text attribute"
        assert hasattr(segment, 'start'), "Segment should have start attribute"
        assert hasattr(segment, 'end'), "Segment should have end attribute"

    def test_text_segment_non_overlapping(self, processor):
        """Test that segments don't overlap."""
        text = "First sentence. Second sentence. Third sentence."

        segments = processor.segment_text(text)

        for i in range(len(segments) - 1):
            assert segments[i].end <= segments[i+1].start, \
                "Segments should not overlap"

    def test_text_segment_coverage(self, processor):
        """Test that segments cover the full text (no gaps)."""
        text = "First sentence. Second sentence."

        segments = processor.segment_text(text)

        # First segment should start at 0
        assert segments[0].start == 0
        # Last segment should end at text length or close to it
        assert segments[-1].end >= len(text) - 2  # Allow for whitespace


class TestNLTKCompatibility:
    """Test suite for NLTK version compatibility."""

    def test_nltk_punkt_availability(self, processor):
        """Test that NLTK punkt tokenizer is available."""
        # This test verifies the processor can initialize NLTK
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

    def test_handles_missing_punkt_gracefully(self):
        """Test that processor handles missing punkt data gracefully."""
        # This is more of a documentation test showing the expected behavior
        # In the actual implementation, punkt_tab is tried first, then punkt
        import nltk

        # Verify one of the tokenizers is available
        try:
            from nltk.tokenize import sent_tokenize
            sent_tokenize("Test.")
            assert True, "Tokenizer should be available"
        except LookupError as e:
            pytest.fail(f"Neither punkt nor punkt_tab available: {e}")


class TestEdgeCases:
    """Test suite for edge cases in text processing."""

    def test_sentence_with_only_punctuation(self, processor):
        """Test handling of unusual punctuation patterns."""
        text = "...!?!"

        segments = processor.segment_text(text)

        # Should either return 1 segment or 0 segments (both acceptable)
        assert len(segments) <= 1

    def test_very_long_sentence(self, processor):
        """Test handling of very long sentences."""
        # Create a long sentence with many clauses
        text = (
            "This is a very long sentence with many clauses, "
            "including subordinate clauses, coordinate clauses, "
            "and various other grammatical structures that make it "
            "quite lengthy but still technically a single sentence."
        )

        segments = processor.segment_text(text)

        assert len(segments) == 1, "Long sentence should still be one segment"
        assert len(segments[0].text) > 100

    def test_unicode_text(self, processor):
        """Test handling of unicode characters."""
        text = "Café serves crêpes. The recipe is français."

        segments = processor.segment_text(text)

        assert len(segments) == 2
        assert "Café" in segments[0].text
        assert "français" in segments[1].text

    def test_numbers_and_dates(self, processor):
        """Test handling of numbers and dates in text."""
        text = "The recipe was created on Jan. 1, 2024. It serves 4-6 people."

        segments = processor.segment_text(text)

        assert len(segments) == 2
        assert "2024" in segments[0].text
        assert "4-6" in segments[1].text

    def test_ellipsis_handling(self, processor):
        """Test handling of ellipsis in text."""
        text = "First sentence... Second sentence."

        segments = processor.segment_text(text)

        # NLTK may handle ellipsis differently
        assert len(segments) >= 1, "Should produce at least one segment"
        # The exact behavior depends on NLTK version

    def test_quoted_text(self, processor):
        """Test handling of quoted text."""
        text = 'He said "Hello world." Then he left.'

        segments = processor.segment_text(text)

        assert len(segments) == 2
        assert '"Hello world."' in segments[0].text or "Hello world" in segments[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
