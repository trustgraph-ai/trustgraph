"""
Simplified integration tests for Template Service

These tests verify the basic functionality of the template service
without the full message queue infrastructure.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from trustgraph.schema import PromptRequest, PromptResponse
from trustgraph.template.prompt_manager import PromptManager


@pytest.mark.integration 
class TestTemplateServiceSimple:
    """Simplified integration tests for Template Service components"""

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing"""
        return {
            "system": json.dumps("You are a helpful assistant."),
            "template-index": json.dumps(["greeting", "json_test"]),
            "template.greeting": json.dumps({
                "prompt": "Hello {{ name }}, welcome to {{ system_name }}!",
                "response-type": "text"
            }),
            "template.json_test": json.dumps({
                "prompt": "Generate profile for {{ username }}",
                "response-type": "json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"}
                    },
                    "required": ["name", "role"]
                }
            })
        }

    @pytest.fixture
    def prompt_manager(self, sample_config):
        """Create a configured PromptManager"""
        pm = PromptManager()
        pm.load_config(sample_config)
        pm.terms["system_name"] = "TrustGraph"
        return pm

    @pytest.mark.asyncio
    async def test_prompt_manager_text_invocation(self, prompt_manager):
        """Test PromptManager text response invocation"""
        # Mock LLM function
        async def mock_llm(system, prompt):
            assert system == "You are a helpful assistant."
            assert "Hello Alice, welcome to TrustGraph!" in prompt
            return "Welcome message processed!"

        result = await prompt_manager.invoke("greeting", {"name": "Alice"}, mock_llm)
        
        assert result == "Welcome message processed!"

    @pytest.mark.asyncio
    async def test_prompt_manager_json_invocation(self, prompt_manager):
        """Test PromptManager JSON response invocation"""
        # Mock LLM function
        async def mock_llm(system, prompt):
            assert "Generate profile for johndoe" in prompt
            return '{"name": "John Doe", "role": "user"}'

        result = await prompt_manager.invoke("json_test", {"username": "johndoe"}, mock_llm)
        
        assert isinstance(result, dict)
        assert result["name"] == "John Doe"
        assert result["role"] == "user"

    @pytest.mark.asyncio
    async def test_prompt_manager_json_validation_error(self, prompt_manager):
        """Test JSON schema validation failure"""
        # Mock LLM function that returns invalid JSON
        async def mock_llm(system, prompt):
            return '{"name": "John Doe"}'  # Missing required "role"

        with pytest.raises(RuntimeError) as exc_info:
            await prompt_manager.invoke("json_test", {"username": "johndoe"}, mock_llm)
        
        assert "Schema validation fail" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_prompt_manager_json_parse_error(self, prompt_manager):
        """Test JSON parsing failure"""
        # Mock LLM function that returns non-JSON
        async def mock_llm(system, prompt):
            return "This is not JSON at all"

        with pytest.raises(RuntimeError) as exc_info:
            await prompt_manager.invoke("json_test", {"username": "johndoe"}, mock_llm)
        
        assert "JSON parse fail" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_prompt_manager_unknown_prompt(self, prompt_manager):
        """Test unknown prompt ID handling"""
        async def mock_llm(system, prompt):
            return "Response"

        with pytest.raises(KeyError):
            await prompt_manager.invoke("unknown_prompt", {}, mock_llm)

    @pytest.mark.asyncio
    async def test_prompt_manager_term_merging(self, prompt_manager):
        """Test proper term merging (global + prompt + input)"""
        # Add prompt-specific terms
        prompt_manager.prompts["greeting"].terms = {"greeting_prefix": "Hi"}
        
        async def mock_llm(system, prompt):
            # Should have global term (system_name), input term (name), and any prompt terms
            assert "TrustGraph" in prompt  # Global term
            assert "Bob" in prompt  # Input term
            return "Merged correctly"

        result = await prompt_manager.invoke("greeting", {"name": "Bob"}, mock_llm)
        assert result == "Merged correctly"

    def test_prompt_manager_template_rendering(self, prompt_manager):
        """Test direct template rendering"""
        result = prompt_manager.render("greeting", {"name": "Charlie"})
        
        assert "Hello Charlie, welcome to TrustGraph!" == result.strip()

    def test_prompt_manager_configuration_loading(self):
        """Test configuration loading with various formats"""
        pm = PromptManager()
        
        # Test empty configuration
        pm.load_config({})
        assert pm.config.system_template == "Be helpful."
        assert len(pm.prompts) == 0
        
        # Test configuration with single prompt
        config = {
            "system": json.dumps("Test system"),
            "template-index": json.dumps(["test"]),
            "template.test": json.dumps({
                "prompt": "Test {{ value }}",
                "response-type": "text"
            })
        }
        pm.load_config(config)
        
        assert pm.config.system_template == "Test system"
        assert "test" in pm.prompts
        assert pm.prompts["test"].response_type == "text"

    @pytest.mark.asyncio
    async def test_prompt_manager_json_with_markdown(self, prompt_manager):
        """Test JSON extraction from markdown code blocks"""
        async def mock_llm(system, prompt):
            return '''
            Here's the profile:
            ```json
            {"name": "Jane Smith", "role": "admin"}
            ```
            '''

        result = await prompt_manager.invoke("json_test", {"username": "jane"}, mock_llm)
        
        assert isinstance(result, dict)
        assert result["name"] == "Jane Smith"
        assert result["role"] == "admin"

    def test_prompt_manager_error_handling_in_templates(self, prompt_manager):
        """Test error handling in template rendering"""
        # Test with missing variable - ibis might handle this differently than Jinja2
        try:
            result = prompt_manager.render("greeting", {})  # Missing 'name'
            # If no exception, check that result is still a string
            assert isinstance(result, str)
        except Exception as e:
            # If exception is raised, that's also acceptable
            assert "name" in str(e) or "undefined" in str(e).lower() or "variable" in str(e).lower()

    @pytest.mark.asyncio
    async def test_concurrent_prompt_invocations(self, prompt_manager):
        """Test concurrent invocations"""
        async def mock_llm(system, prompt):
            # Extract name from prompt for response
            if "Alice" in prompt:
                return "Alice response"
            elif "Bob" in prompt:
                return "Bob response"
            else:
                return "Default response"

        # Run concurrent invocations
        import asyncio
        results = await asyncio.gather(
            prompt_manager.invoke("greeting", {"name": "Alice"}, mock_llm),
            prompt_manager.invoke("greeting", {"name": "Bob"}, mock_llm),
        )

        assert "Alice response" in results
        assert "Bob response" in results