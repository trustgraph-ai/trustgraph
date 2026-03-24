"""
Integration tests for MiniMax text completion provider.
Tests actual API calls to MiniMax when MINIMAX_API_KEY is available.
"""

import os
import pytest
from openai import OpenAI

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_BASE_URL = "https://api.minimax.io/v1"


@pytest.mark.skipif(
    not MINIMAX_API_KEY,
    reason="MINIMAX_API_KEY not set"
)
class TestMiniMaxIntegration:
    """Integration tests that call the real MiniMax API"""

    def get_client(self):
        return OpenAI(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)

    def test_basic_chat_completion(self):
        """Test basic chat completion with MiniMax-M2.7"""
        client = self.get_client()

        resp = client.chat.completions.create(
            model="MiniMax-M2.7",
            messages=[{
                "role": "user",
                "content": 'Say "test passed" and nothing else.'
            }],
            temperature=1.0,
            max_tokens=64,
        )

        assert resp.choices[0].message.content is not None
        assert len(resp.choices[0].message.content) > 0
        assert resp.usage.prompt_tokens > 0
        assert resp.usage.completion_tokens > 0

    def test_highspeed_model(self):
        """Test chat completion with MiniMax-M2.7-highspeed"""
        client = self.get_client()

        resp = client.chat.completions.create(
            model="MiniMax-M2.7-highspeed",
            messages=[{
                "role": "user",
                "content": 'Say "highspeed test passed" and nothing else.'
            }],
            temperature=1.0,
            max_tokens=64,
        )

        assert resp.choices[0].message.content is not None
        assert len(resp.choices[0].message.content) > 0

    def test_streaming_completion(self):
        """Test streaming chat completion"""
        client = self.get_client()

        response = client.chat.completions.create(
            model="MiniMax-M2.7",
            messages=[{
                "role": "user",
                "content": 'Say "stream test passed" and nothing else.'
            }],
            temperature=1.0,
            max_tokens=64,
            stream=True,
            stream_options={"include_usage": True}
        )

        chunks = list(response)
        assert len(chunks) > 0

        # Collect text from chunks
        texts = []
        for chunk in chunks:
            if chunk.choices and chunk.choices[0].delta.content:
                texts.append(chunk.choices[0].delta.content)

        full_text = "".join(texts)
        assert len(full_text) > 0
