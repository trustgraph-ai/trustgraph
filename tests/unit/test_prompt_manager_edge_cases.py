"""
Edge case and error handling tests for PromptManager

These tests focus on boundary conditions, error scenarios, and 
unusual but valid use cases for the PromptManager.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock

from trustgraph.template.prompt_manager import PromptManager, PromptConfiguration, Prompt


@pytest.mark.unit
class TestPromptManagerEdgeCases:
    """Edge case tests for PromptManager"""

    @pytest.mark.asyncio
    async def test_very_large_json_response(self):
        """Test handling of very large JSON responses"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["large_json"]),
            "template.large_json": json.dumps({
                "prompt": "Generate large dataset",
                "response-type": "json"
            })
        }
        pm.load_config(config)
        
        # Create a large JSON structure
        large_data = {
            f"item_{i}": {
                "name": f"Item {i}",
                "data": list(range(100)),
                "nested": {
                    "level1": {
                        "level2": f"Deep value {i}"
                    }
                }
            }
            for i in range(100)
        }
        
        mock_llm = AsyncMock()
        mock_llm.return_value = json.dumps(large_data)
        
        result = await pm.invoke("large_json", {}, mock_llm)
        
        assert isinstance(result, dict)
        assert len(result) == 100
        assert "item_50" in result

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["unicode"]),
            "template.unicode": json.dumps({
                "prompt": "Process text: {{ text }}",
                "response-type": "text"
            })
        }
        pm.load_config(config)
        
        special_text = "Hello 世界! 🌍 Привет мир! مرحبا بالعالم"
        
        mock_llm = AsyncMock()
        mock_llm.return_value = f"Processed: {special_text}"
        
        result = await pm.invoke("unicode", {"text": special_text}, mock_llm)
        
        assert special_text in result
        assert "🌍" in result
        assert "世界" in result

    @pytest.mark.asyncio
    async def test_nested_json_in_text_response(self):
        """Test text response containing JSON-like structures"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["text_with_json"]),
            "template.text_with_json": json.dumps({
                "prompt": "Explain this data",
                "response-type": "text"  # Text response, not JSON
            })
        }
        pm.load_config(config)
        
        mock_llm = AsyncMock()
        mock_llm.return_value = """
        The data structure is:
        {
            "key": "value",
            "nested": {
                "array": [1, 2, 3]
            }
        }
        This represents a nested object.
        """
        
        result = await pm.invoke("text_with_json", {}, mock_llm)
        
        assert isinstance(result, str)  # Should remain as text
        assert '"key": "value"' in result

    @pytest.mark.asyncio
    async def test_multiple_json_blocks_in_response(self):
        """Test response with multiple JSON blocks"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["multi_json"]),
            "template.multi_json": json.dumps({
                "prompt": "Generate examples",
                "response-type": "json"
            })
        }
        pm.load_config(config)
        
        mock_llm = AsyncMock()
        mock_llm.return_value = """
        Here's the first example:
        ```json
        {"first": true, "value": 1}
        ```
        
        And here's another:
        ```json
        {"second": true, "value": 2}
        ```
        """
        
        # Should extract the first valid JSON block
        result = await pm.invoke("multi_json", {}, mock_llm)
        
        assert result == {"first": True, "value": 1}

    @pytest.mark.asyncio
    async def test_json_with_comments(self):
        """Test JSON response with comment-like content"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["json_comments"]),
            "template.json_comments": json.dumps({
                "prompt": "Generate config",
                "response-type": "json"
            })
        }
        pm.load_config(config)
        
        mock_llm = AsyncMock()
        # JSON with comment-like content that should be extracted
        mock_llm.return_value = """
        // This is a configuration file
        {
            "setting": "value",  // Important setting
            "number": 42
        }
        /* End of config */
        """
        
        # Standard JSON parser won't handle comments
        with pytest.raises(ValueError):
            await pm.invoke("json_comments", {}, mock_llm)

    def test_template_with_raw_blocks(self):
        """Test template with raw blocks that shouldn't be processed"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["raw_template"]),
            "template.raw_template": json.dumps({
                "prompt": """
                    Normal: {{ variable }}
                    {% raw %}
                    Raw block: {{ this_should_not_be_processed }}
                    {% endraw %}
                    Normal again: {{ another }}
                    """,
                "response-type": "text"
            })
        }
        pm.load_config(config)
        
        result = pm.render(
            "raw_template",
            {"variable": "processed", "another": "also processed"}
        )
        
        assert "processed" in result
        assert "{{ this_should_not_be_processed }}" in result  # Should remain as-is
        assert "also processed" in result

    @pytest.mark.asyncio
    async def test_empty_json_response_variations(self):
        """Test various empty JSON response formats"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["empty_json"]),
            "template.empty_json": json.dumps({
                "prompt": "Generate empty data",
                "response-type": "json"
            })
        }
        pm.load_config(config)
        
        empty_variations = [
            "{}",
            "[]",
            "null",
            '""',
            "0",
            "false"
        ]
        
        for empty_value in empty_variations:
            mock_llm = AsyncMock()
            mock_llm.return_value = empty_value
            
            result = await pm.invoke("empty_json", {}, mock_llm)
            assert result == json.loads(empty_value)

    @pytest.mark.asyncio
    async def test_malformed_json_recovery(self):
        """Test recovery from slightly malformed JSON"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["malformed"]),
            "template.malformed": json.dumps({
                "prompt": "Generate data",
                "response-type": "json"
            })
        }
        pm.load_config(config)
        
        # Missing closing brace - should fail
        mock_llm = AsyncMock()
        mock_llm.return_value = '{"key": "value"'
        
        with pytest.raises(RuntimeError) as exc_info:
            await pm.invoke("malformed", {}, mock_llm)
        
        assert "JSON parse fail" in str(exc_info.value)

    def test_template_infinite_loop_protection(self):
        """Test protection against infinite template loops"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["recursive"]),
            "template.recursive": json.dumps({
                "prompt": "{{ recursive_var }}",
                "response-type": "text"
            })
        }
        pm.load_config(config)
        pm.prompts["recursive"].terms = {"recursive_var": "This includes {{ recursive_var }}"}
        
        # This should not cause infinite recursion
        result = pm.render("recursive", {})
        
        # The exact behavior depends on the template engine
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_extremely_long_template(self):
        """Test handling of extremely long templates"""
        # Create a very long template
        long_template = "Start\n" + "\n".join([
            f"Line {i}: " + "{{ var_" + str(i) + " }}"
            for i in range(1000)
        ]) + "\nEnd"
        
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["long"]),
            "template.long": json.dumps({
                "prompt": long_template,
                "response-type": "text"
            })
        }
        pm.load_config(config)
        
        # Create corresponding variables
        variables = {f"var_{i}": f"value_{i}" for i in range(1000)}
        
        mock_llm = AsyncMock()
        mock_llm.return_value = "Processed long template"
        
        result = await pm.invoke("long", variables, mock_llm)
        
        assert result == "Processed long template"
        
        # Check that template was rendered correctly
        call_args = mock_llm.call_args[1]
        rendered = call_args["prompt"]
        assert "Line 500: value_500" in rendered

    @pytest.mark.asyncio
    async def test_json_schema_with_additional_properties(self):
        """Test JSON schema validation with additional properties"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["strict_schema"]),
            "template.strict_schema": json.dumps({
                "prompt": "Generate user",
                "response-type": "json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    },
                    "required": ["name"],
                    "additionalProperties": False
                }
            })
        }
        pm.load_config(config)
        
        mock_llm = AsyncMock()
        # Response with extra property
        mock_llm.return_value = '{"name": "John", "age": 30}'
        
        # Should fail validation due to additionalProperties: false
        with pytest.raises(RuntimeError) as exc_info:
            await pm.invoke("strict_schema", {}, mock_llm)
        
        assert "Schema validation fail" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_llm_timeout_handling(self):
        """Test handling of LLM timeouts"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["timeout_test"]),
            "template.timeout_test": json.dumps({
                "prompt": "Test prompt",
                "response-type": "text"
            })
        }
        pm.load_config(config)
        
        mock_llm = AsyncMock()
        mock_llm.side_effect = asyncio.TimeoutError("LLM request timed out")
        
        with pytest.raises(asyncio.TimeoutError):
            await pm.invoke("timeout_test", {}, mock_llm)

    def test_template_with_filters_and_tests(self):
        """Test template with Jinja2 filters and tests"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["filters"]),
            "template.filters": json.dumps({
                "prompt": """
                    {% if items %}
                    Items ({{ items|length }}):
                    {% for item in items|sort %}
                    - {{ item|upper }}
                    {% endfor %}
                    {% else %}
                    No items
                    {% endif %}
                    """,
                "response-type": "text"
            })
        }
        pm.load_config(config)
        
        # Test with items
        result = pm.render(
            "filters",
            {"items": ["banana", "apple", "cherry"]}
        )
        
        assert "Items (3)" in result
        assert "- APPLE" in result
        assert "- BANANA" in result
        assert "- CHERRY" in result
        
        # Test without items
        result = pm.render("filters", {"items": []})
        assert "No items" in result

    @pytest.mark.asyncio
    async def test_concurrent_template_modifications(self):
        """Test thread safety of template operations"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["concurrent"]),
            "template.concurrent": json.dumps({
                "prompt": "User: {{ user }}",
                "response-type": "text"
            })
        }
        pm.load_config(config)
        
        mock_llm = AsyncMock()
        mock_llm.side_effect = lambda **kwargs: f"Response for {kwargs['prompt'].split()[1]}"
        
        # Simulate concurrent invocations with different users
        import asyncio
        tasks = []
        for i in range(10):
            tasks.append(
                pm.invoke("concurrent", {"user": f"User{i}"}, mock_llm)
            )
        
        results = await asyncio.gather(*tasks)
        
        # Each result should correspond to its user
        for i, result in enumerate(results):
            assert f"User{i}" in result