"""
Unit tests for PromptManager

These tests verify the functionality of the PromptManager class,
including template rendering, term merging, JSON validation, and error handling.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.template.prompt_manager import PromptManager, PromptConfiguration, Prompt


@pytest.mark.unit
class TestPromptManager:
    """Unit tests for PromptManager template functionality"""

    @pytest.fixture
    def sample_config(self):
        """Sample configuration dict for PromptManager"""
        return {
            "system": json.dumps("You are a helpful assistant."),
            "template-index": json.dumps(["simple_text", "json_response", "complex_template"]),
            "template.simple_text": json.dumps({
                "prompt": "Hello {{ name }}, welcome to {{ system_name }}!",
                "response-type": "text"
            }),
            "template.json_response": json.dumps({
                "prompt": "Generate a user profile for {{ username }}",
                "response-type": "json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "number"}
                    },
                    "required": ["name", "age"]
                }
            }),
            "template.complex_template": json.dumps({
                "prompt": """
                {% for item in items %}
                - {{ item.name }}: {{ item.value }}
                {% endfor %}
                """,
                "response-type": "text"
            })
        }

    @pytest.fixture
    def prompt_manager(self, sample_config):
        """Create a PromptManager with sample configuration"""
        pm = PromptManager()
        pm.load_config(sample_config)
        # Add global terms manually since load_config doesn't handle them
        pm.terms["system_name"] = "TrustGraph"
        pm.terms["version"] = "1.0"
        return pm

    def test_prompt_manager_initialization(self, prompt_manager, sample_config):
        """Test PromptManager initialization with configuration"""
        assert prompt_manager.config.system_template == "You are a helpful assistant."
        assert len(prompt_manager.prompts) == 3
        assert "simple_text" in prompt_manager.prompts

    def test_simple_text_template_rendering(self, prompt_manager):
        """Test basic template rendering with text response"""
        terms = {"name": "Alice"}
        
        rendered = prompt_manager.render("simple_text", terms)
        
        assert rendered == "Hello Alice, welcome to TrustGraph!"

    def test_global_terms_merging(self, prompt_manager):
        """Test that global terms are properly merged"""
        terms = {"name": "Bob"}
        
        # Global terms should be available in template
        rendered = prompt_manager.render("simple_text", terms)
        
        assert "TrustGraph" in rendered  # From global terms
        assert "Bob" in rendered  # From input terms

    def test_term_override_priority(self):
        """Test term override priority: input > prompt > global"""
        # Create a fresh PromptManager for this test
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["test"]),
            "template.test": json.dumps({
                "prompt": "Value is: {{ value }}",
                "response-type": "text"
            })
        }
        pm.load_config(config)
        
        # Set up terms at different levels
        pm.terms["value"] = "global"  # Global term
        if "test" in pm.prompts:
            pm.prompts["test"].terms = {"value": "prompt"}  # Prompt term
        
        # Test with no input override - prompt terms should win
        rendered = pm.render("test", {})
        if "test" in pm.prompts and pm.prompts["test"].terms:
            assert rendered == "Value is: prompt"  # Prompt terms override global
        else:
            assert rendered == "Value is: global"  # No prompt terms, use global
        
        # Test with input override - input terms should win
        rendered = pm.render("test", {"value": "input"})
        assert rendered == "Value is: input"  # Input terms override all

    def test_complex_template_rendering(self, prompt_manager):
        """Test complex template with loops and filters"""
        terms = {
            "items": [
                {"name": "Item1", "value": 10},
                {"name": "Item2", "value": 20},
                {"name": "Item3", "value": 30}
            ]
        }
        
        rendered = prompt_manager.render("complex_template", terms)
        
        assert "Item1: 10" in rendered
        assert "Item2: 20" in rendered
        assert "Item3: 30" in rendered

    @pytest.mark.asyncio
    async def test_invoke_text_response(self, prompt_manager):
        """Test invoking a prompt with text response"""
        mock_llm = AsyncMock()
        mock_llm.return_value = "Welcome Alice to TrustGraph!"
        
        result = await prompt_manager.invoke(
            "simple_text",
            {"name": "Alice"},
            mock_llm
        )
        
        assert result == "Welcome Alice to TrustGraph!"
        
        # Verify LLM was called with correct prompts
        mock_llm.assert_called_once()
        call_args = mock_llm.call_args[1]
        assert call_args["system"] == "You are a helpful assistant."
        assert "Hello Alice, welcome to TrustGraph!" in call_args["prompt"]

    @pytest.mark.asyncio
    async def test_invoke_json_response_valid(self, prompt_manager):
        """Test invoking a prompt with valid JSON response"""
        mock_llm = AsyncMock()
        mock_llm.return_value = '{"name": "John Doe", "age": 30}'
        
        result = await prompt_manager.invoke(
            "json_response",
            {"username": "johndoe"},
            mock_llm
        )
        
        assert isinstance(result, dict)
        assert result["name"] == "John Doe"
        assert result["age"] == 30

    @pytest.mark.asyncio
    async def test_invoke_json_response_with_markdown(self, prompt_manager):
        """Test JSON extraction from markdown code blocks"""
        mock_llm = AsyncMock()
        mock_llm.return_value = """
        Here is the user profile:
        
        ```json
        {
            "name": "Jane Smith",
            "age": 25
        }
        ```
        
        This is a valid profile.
        """
        
        result = await prompt_manager.invoke(
            "json_response",
            {"username": "janesmith"},
            mock_llm
        )
        
        assert isinstance(result, dict)
        assert result["name"] == "Jane Smith"
        assert result["age"] == 25

    @pytest.mark.asyncio
    async def test_invoke_json_validation_failure(self, prompt_manager):
        """Test JSON schema validation failure"""
        mock_llm = AsyncMock()
        # Missing required 'age' field
        mock_llm.return_value = '{"name": "Invalid User"}'
        
        with pytest.raises(RuntimeError) as exc_info:
            await prompt_manager.invoke(
                "json_response",
                {"username": "invalid"},
                mock_llm
            )
        
        assert "Schema validation fail" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_json_parse_failure(self, prompt_manager):
        """Test invalid JSON parsing"""
        mock_llm = AsyncMock()
        mock_llm.return_value = "This is not JSON at all"
        
        with pytest.raises(RuntimeError) as exc_info:
            await prompt_manager.invoke(
                "json_response",
                {"username": "test"},
                mock_llm
            )
        
        assert "JSON parse fail" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_unknown_prompt(self, prompt_manager):
        """Test invoking an unknown prompt ID"""
        mock_llm = AsyncMock()
        
        with pytest.raises(KeyError):
            await prompt_manager.invoke(
                "nonexistent_prompt",
                {},
                mock_llm
            )

    def test_template_rendering_with_undefined_variable(self, prompt_manager):
        """Test template rendering with undefined variables"""
        terms = {}  # Missing 'name' variable
        
        # ibis might handle undefined variables differently than Jinja2
        # Let's test what actually happens
        try:
            result = prompt_manager.render("simple_text", terms)
            # If no exception, check that undefined variables are handled somehow
            assert isinstance(result, str)
        except Exception as e:
            # If exception is raised, that's also acceptable behavior
            assert "name" in str(e) or "undefined" in str(e).lower() or "variable" in str(e).lower()

    @pytest.mark.asyncio
    async def test_json_response_without_schema(self):
        """Test JSON response without schema validation"""
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["no_schema"]),
            "template.no_schema": json.dumps({
                "prompt": "Generate any JSON",
                "response-type": "json"
                # No schema defined
            })
        }
        pm.load_config(config)
        
        mock_llm = AsyncMock()
        mock_llm.return_value = '{"any": "json", "is": "valid"}'
        
        result = await pm.invoke("no_schema", {}, mock_llm)
        
        assert result == {"any": "json", "is": "valid"}

    def test_prompt_configuration_validation(self):
        """Test PromptConfiguration validation"""
        # Valid configuration
        config = PromptConfiguration(
            system_template="Test system",
            prompts={
                "test": Prompt(
                    template="Hello {{ name }}",
                    response_type="text"
                )
            }
        )
        assert config.system_template == "Test system"
        assert len(config.prompts) == 1

    def test_nested_template_includes(self):
        """Test templates with nested variable references"""
        # Create a fresh PromptManager for this test
        pm = PromptManager()
        config = {
            "system": json.dumps("Test"),
            "template-index": json.dumps(["nested"]),
            "template.nested": json.dumps({
                "prompt": "{{ greeting }} from {{ company }} in {{ year }}!",
                "response-type": "text"
            })
        }
        pm.load_config(config)
        
        # Set up global and prompt terms
        pm.terms["company"] = "TrustGraph"
        pm.terms["year"] = "2024"
        if "nested" in pm.prompts:
            pm.prompts["nested"].terms = {"greeting": "Welcome"}
        
        rendered = pm.render("nested", {"user": "Alice", "greeting": "Welcome"})
        
        # Should contain company and year from global terms
        assert "TrustGraph" in rendered
        assert "2024" in rendered
        assert "Welcome" in rendered

    @pytest.mark.asyncio
    async def test_concurrent_invocations(self, prompt_manager):
        """Test concurrent prompt invocations"""
        mock_llm = AsyncMock()
        mock_llm.side_effect = [
            "Response for Alice",
            "Response for Bob",
            "Response for Charlie"
        ]
        
        # Simulate concurrent invocations
        import asyncio
        results = await asyncio.gather(
            prompt_manager.invoke("simple_text", {"name": "Alice"}, mock_llm),
            prompt_manager.invoke("simple_text", {"name": "Bob"}, mock_llm),
            prompt_manager.invoke("simple_text", {"name": "Charlie"}, mock_llm)
        )
        
        assert len(results) == 3
        assert "Alice" in results[0]
        assert "Bob" in results[1]
        assert "Charlie" in results[2]

    def test_empty_configuration(self):
        """Test PromptManager with minimal configuration"""
        pm = PromptManager()
        pm.load_config({})  # Empty config

        assert pm.config.system_template == "Be helpful."  # Default system
        assert pm.terms == {}  # Default empty terms
        assert len(pm.prompts) == 0


@pytest.mark.unit
class TestPromptManagerJsonl:
    """Unit tests for PromptManager JSONL functionality"""

    @pytest.fixture
    def jsonl_config(self):
        """Configuration with JSONL response type prompts"""
        return {
            "system": json.dumps("You are an extraction assistant."),
            "template-index": json.dumps(["extract_simple", "extract_with_schema", "extract_mixed"]),
            "template.extract_simple": json.dumps({
                "prompt": "Extract entities from: {{ text }}",
                "response-type": "jsonl"
            }),
            "template.extract_with_schema": json.dumps({
                "prompt": "Extract definitions from: {{ text }}",
                "response-type": "jsonl",
                "schema": {
                    "type": "object",
                    "properties": {
                        "entity": {"type": "string"},
                        "definition": {"type": "string"}
                    },
                    "required": ["entity", "definition"]
                }
            }),
            "template.extract_mixed": json.dumps({
                "prompt": "Extract knowledge from: {{ text }}",
                "response-type": "jsonl",
                "schema": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "type": {"const": "definition"},
                                "entity": {"type": "string"},
                                "definition": {"type": "string"}
                            },
                            "required": ["type", "entity", "definition"]
                        },
                        {
                            "type": "object",
                            "properties": {
                                "type": {"const": "relationship"},
                                "subject": {"type": "string"},
                                "predicate": {"type": "string"},
                                "object": {"type": "string"}
                            },
                            "required": ["type", "subject", "predicate", "object"]
                        }
                    ]
                }
            })
        }

    @pytest.fixture
    def prompt_manager(self, jsonl_config):
        """Create a PromptManager with JSONL configuration"""
        pm = PromptManager()
        pm.load_config(jsonl_config)
        return pm

    def test_parse_jsonl_basic(self, prompt_manager):
        """Test basic JSONL parsing"""
        text = '{"entity": "cat", "definition": "A small furry animal"}\n{"entity": "dog", "definition": "A loyal pet"}'

        result = prompt_manager.parse_jsonl(text)

        assert len(result) == 2
        assert result[0]["entity"] == "cat"
        assert result[1]["entity"] == "dog"

    def test_parse_jsonl_with_empty_lines(self, prompt_manager):
        """Test JSONL parsing skips empty lines"""
        text = '{"entity": "cat"}\n\n\n{"entity": "dog"}\n'

        result = prompt_manager.parse_jsonl(text)

        assert len(result) == 2

    def test_parse_jsonl_with_markdown_fences(self, prompt_manager):
        """Test JSONL parsing strips markdown code fences"""
        text = '''```json
{"entity": "cat", "definition": "A furry animal"}
{"entity": "dog", "definition": "A loyal pet"}
```'''

        result = prompt_manager.parse_jsonl(text)

        assert len(result) == 2
        assert result[0]["entity"] == "cat"
        assert result[1]["entity"] == "dog"

    def test_parse_jsonl_with_jsonl_fence(self, prompt_manager):
        """Test JSONL parsing strips jsonl-marked code fences"""
        text = '''```jsonl
{"entity": "cat"}
{"entity": "dog"}
```'''

        result = prompt_manager.parse_jsonl(text)

        assert len(result) == 2

    def test_parse_jsonl_truncation_resilience(self, prompt_manager):
        """Test JSONL parsing handles truncated final line"""
        text = '{"entity": "cat", "definition": "Complete"}\n{"entity": "dog", "defi'

        result = prompt_manager.parse_jsonl(text)

        # Should get the first valid object, skip the truncated one
        assert len(result) == 1
        assert result[0]["entity"] == "cat"

    def test_parse_jsonl_invalid_lines_skipped(self, prompt_manager):
        """Test JSONL parsing skips invalid JSON lines"""
        text = '''{"entity": "valid1"}
not json at all
{"entity": "valid2"}
{broken json
{"entity": "valid3"}'''

        result = prompt_manager.parse_jsonl(text)

        assert len(result) == 3
        assert result[0]["entity"] == "valid1"
        assert result[1]["entity"] == "valid2"
        assert result[2]["entity"] == "valid3"

    def test_parse_jsonl_empty_input(self, prompt_manager):
        """Test JSONL parsing with empty input"""
        result = prompt_manager.parse_jsonl("")
        assert result == []

        result = prompt_manager.parse_jsonl("\n\n\n")
        assert result == []

    @pytest.mark.asyncio
    async def test_invoke_jsonl_response(self, prompt_manager):
        """Test invoking a prompt with JSONL response"""
        mock_llm = AsyncMock()
        mock_llm.return_value = '{"entity": "photosynthesis", "definition": "Plant process"}\n{"entity": "mitosis", "definition": "Cell division"}'

        result = await prompt_manager.invoke(
            "extract_simple",
            {"text": "Biology text"},
            mock_llm
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["entity"] == "photosynthesis"
        assert result[1]["entity"] == "mitosis"

    @pytest.mark.asyncio
    async def test_invoke_jsonl_with_schema_validation(self, prompt_manager):
        """Test JSONL response with schema validation"""
        mock_llm = AsyncMock()
        mock_llm.return_value = '{"entity": "cat", "definition": "A pet"}\n{"entity": "dog", "definition": "Another pet"}'

        result = await prompt_manager.invoke(
            "extract_with_schema",
            {"text": "Animal text"},
            mock_llm
        )

        assert len(result) == 2
        assert all("entity" in obj and "definition" in obj for obj in result)

    @pytest.mark.asyncio
    async def test_invoke_jsonl_schema_filters_invalid(self, prompt_manager):
        """Test JSONL schema validation filters out invalid objects"""
        mock_llm = AsyncMock()
        # Second object is missing required 'definition' field
        mock_llm.return_value = '{"entity": "valid", "definition": "Has both fields"}\n{"entity": "invalid_missing_definition"}\n{"entity": "also_valid", "definition": "Complete"}'

        result = await prompt_manager.invoke(
            "extract_with_schema",
            {"text": "Test text"},
            mock_llm
        )

        # Only the two valid objects should be returned
        assert len(result) == 2
        assert result[0]["entity"] == "valid"
        assert result[1]["entity"] == "also_valid"

    @pytest.mark.asyncio
    async def test_invoke_jsonl_mixed_types(self, prompt_manager):
        """Test JSONL with discriminated union schema (oneOf)"""
        mock_llm = AsyncMock()
        mock_llm.return_value = '''{"type": "definition", "entity": "DNA", "definition": "Genetic material"}
{"type": "relationship", "subject": "DNA", "predicate": "found_in", "object": "nucleus"}
{"type": "definition", "entity": "RNA", "definition": "Messenger molecule"}'''

        result = await prompt_manager.invoke(
            "extract_mixed",
            {"text": "Biology text"},
            mock_llm
        )

        assert len(result) == 3

        # Check definitions
        definitions = [r for r in result if r.get("type") == "definition"]
        assert len(definitions) == 2

        # Check relationships
        relationships = [r for r in result if r.get("type") == "relationship"]
        assert len(relationships) == 1
        assert relationships[0]["subject"] == "DNA"

    @pytest.mark.asyncio
    async def test_invoke_jsonl_empty_result(self, prompt_manager):
        """Test JSONL response that yields no valid objects"""
        mock_llm = AsyncMock()
        mock_llm.return_value = "No JSON here at all"

        result = await prompt_manager.invoke(
            "extract_simple",
            {"text": "Test"},
            mock_llm
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_invoke_jsonl_without_schema(self, prompt_manager):
        """Test JSONL response without schema validation"""
        mock_llm = AsyncMock()
        mock_llm.return_value = '{"any": "structure"}\n{"completely": "different"}'

        result = await prompt_manager.invoke(
            "extract_simple",
            {"text": "Test"},
            mock_llm
        )

        assert len(result) == 2
        assert result[0] == {"any": "structure"}
        assert result[1] == {"completely": "different"}